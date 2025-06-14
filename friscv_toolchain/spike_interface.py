import os
import queue
import shutil
import subprocess
import re
import threading
import time

from .state import State


class SpikeInterface:
    """
    Interface to run Spike in debug mode and parse commit-level state.
    """
    COMMIT_RE = re.compile(r"core\s+(?P<core>\d+):\s+(?P<pc>0x[0-9a-fA-F]+)\s+\((?P<inst>0x[0-9a-fA-F]+)\)\s+(?P<disasm>.+)")
    REG_RE    = re.compile(r"\s*x(?P<reg>\d+)\s+=\s+(?P<val>0x[0-9a-fA-F]+)")
    MEM_RE    = re.compile(r"store:\s+addr=(?P<addr>0x[0-9a-fA-F]+)\s+data=(?P<data>0x[0-9a-fA-F]+)")


    def __init__(self, spike_path: str, isa: str, base_opts: str, start_pc: str, elf_path: str) -> None:
        self.spike_path = spike_path
        self.isa = isa
        self.base_opts = base_opts
        self.start_pc = start_pc
        self.elf_path = elf_path
        self.proc = None
        self._queue = queue.Queue()
        self._thread_stdout = None
        self._thread_stderr = None


    def start(self) -> None:
        cmd = [
            self.spike_path,
            '-d',
            f'--isa={self.isa}',
            *self.base_opts.split(),
            f'--pc={self.start_pc}',
            '--log-commits',
            self.elf_path
        ]

        print(f'Starting Spike with command {" ".join(cmd)}')

        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        self._thread_stdout = threading.Thread(target=self._enqueue_stdout, daemon=True)
        self._thread_stderr = threading.Thread(target=self._enqueue_stderr, daemon=True)
        self._thread_stdout.start()
        self._thread_stderr.start()

        time.sleep(0.1)
        self._send_command('run 1')


    def _send_command(self, cmd: str) -> None:
        """Send a command to the Spike process"""
        if self.proc and self.proc.stdin:
            print(f"Sending command: {cmd}")
            self.proc.stdin.write(f"{cmd}\n")
            self.proc.stdin.flush()


    def _enqueue_stdout(self) -> None:
        """Capture stdout output"""
        if not self.proc or not self.proc.stdout:
            return
        
        for line in self.proc.stdout:
            line = line.strip()
            if line:
                print(f"STDOUT: {line}")
                self._queue.put(('stdout', line))


    def _enqueue_stderr(self) -> None:
        """Capture stderr output"""
        if not self.proc or not self.proc.stderr:
            return
        
        for line in self.proc.stderr:
            line = line.strip()
            if line:
                print(f"STDERR: {line}")
                self._queue.put(('stderr', line))


    def next_commit(self, timeout=None) -> State | None:
        state = State()

        if self.proc and self.proc.stdin:
            self.proc.stdin.write('run 1\n')
            self.proc.stdin.flush()

        while True:
            try:
                line = self._queue.get(timeout=timeout)
            except queue.Empty:
                return None
            
            m = self.COMMIT_RE.match(line)
            if m:
                state.core   = int(m.group('core'))
                state.pc     = m.group('pc')
                state.inst   = m.group('inst')
                state.disasm = m.group('disasm')
                break

        while True:
            try:
                line = self._queue.get_nowait()
            except queue.Empty:
                break

            mr = self.REG_RE.match(line)
            if mr:
                reg = int(mr.group('reg'))
                val = mr.group('val')
                state.regs[reg] = val
                continue

            mm = self.MEM_RE.search(line)
            if mm:
                addr = mm.group('addr')
                data = mm.group('data')
                state.stores.append((addr, data))

        return state


    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait()
            self.proc = None


def get_spike_installed(custom_path: str | None = None) -> bool:
    """
    Check if Spike is installed and accessible.

    Args:
        custom_path: Optional custom path to Spike installation

    Returns:
        True if Spike is installed and working, False otherwise
    """
    if custom_path:
        possible_cmd_path = os.path.join(custom_path, 'spike')
        if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
            spike_cmd = possible_cmd_path
        else:
            possible_cmd_path = os.path.join(custom_path, 'bin', 'spike')
            if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
                spike_cmd = possible_cmd_path
            else:
                print(f"Warning: Custom Spike path {custom_path} is invalid.")
                return False
    else:
        spike_cmd = shutil.which('spike')

    if not spike_cmd:
        return False

    try:
        _ = subprocess.run([spike_cmd, '--help'], capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'Error executing Spike: {e}')
        return False
    except FileNotFoundError:
        print(f'Error: Spike executable not found at {spike_cmd if spike_cmd else 'PATH'}')
        return False
