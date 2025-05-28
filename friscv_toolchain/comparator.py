

from friscv_toolchain.vivado_interface import VivadoInterface
from friscv_toolchain.spike_interface import SpikeInterface


def compare_run():
    spike = SpikeInterface(
        spike_path='spike',
        isa='rv32i',
        base_opts='-m0x80000000:0x10000,0x20000000:0x1000',
        start_pc='0x80000000',
        elf_path='./output/bin/test1_alu.elf'
    )

    vivado = VivadoInterface(
        sim_cmd='vsim -c -do run.do'
    )

    spike.start()

    try:
        while True:
            spike_state = spike.next_commit(timeout=1)
            if spike_state is None:
                break
            vivado_state = vivado.step_cycle()
            if spike_state['regs'] != vivado_state.get('regs') or spike_state['stores'] != vivado_state.get('stores'):
                print(f'Mismatch detected at PC {spike_state['pc']}')
                print(f'Spike state: {spike_state}')
                print(f'Vivado state: {vivado_state}')
                break
    finally:
        spike.stop()
        vivado.stop()
