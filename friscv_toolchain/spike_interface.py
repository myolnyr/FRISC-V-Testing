import os
import queue
import shutil
import subprocess
import re
import threading


class SpikeInterface:
    """
    Interface to run Spike in debug mode and parse commit-level state.
    """
    COMMIT_RE = re.compile(r"core\s+(?P<core>\d+):\s+(?P<pc>0x[0-9a-fA-F]+)\s+\((?P<inst>0x[0-9a-fA-F]+)\)\s+(?P<disasm>.+)")
    REG_RE    = re.compile(r"\s*x(?P<reg>\d+)\s+=\s+(?P<val>0x[0-9a-fA-F]+)")
    MEM_RE    = re.compile(r"store:\s+addr=(?P<addr>0x[0-9a-fA-F]+)\s+data=(?P<data>0x[0-9a-fA-F]+)")


    def __init__(self, spike_path, isa, base_opts, start_pc, elf_path):
        self.spike_path = spike_path
        self.isa = isa
        self.base_opts = base_opts
        self.start_pc = start_pc
        self.elf_path = elf_path
        self.proc = None
        self._queue = queue.Queue()
        self._thread = None


    def start(self):
        cmd = [
            self.spike_path,
            '-d',
            f'--isa={self.isa}',
            *self.base_opts.split(),
            f'--pc={self.start_pc}',
            '--log-commits',
            self.elf_path
        ]
        self.proc = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self._thread = threading.Thread(target=self._enqueue_output, daemon=True)
        self._thread.start()


    def _enqueue_output(self):
        if not self.proc or not self.proc.stderr:
            return

        for line in self.proc.stderr:
            self._queue.put(line.strip())

    def next_commit(self, timeout=None):
        state = {'regs': {}, 'stores': []}
        while True:
            try:
                line = self._queue.get(timeout=timeout)
            except queue.Empty:
                return None
            m = self.COMMIT_RE.match(line)
            if m:
                state['core'] = int(m.group('core'))
                state['pc']   = m.group('pc')
                state['inst'] = m.group('inst')
                state['disasm'] = m.group('disasm')
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
                state['regs'][reg] = val
                continue
            mm = self.MEM_RE.search(line)
            if mm:
                addr = mm.group('addr')
                data = mm.group('data')
                state['stores'].append((addr, data))
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
