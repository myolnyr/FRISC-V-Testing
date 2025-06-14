import argparse
import os
from pathlib import Path

from friscv_toolchain import (
    read_json,
    get_vivado_version,
    get_spike_installed,
    compile_riscv_tests,
    SpikeInterface
)


def parse_args() -> argparse.Namespace | None:
    """
    Parse command-line arguments for the RISC-V verification toolchain.

    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description='FRISC-V Verification Toolchain',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--test', dest='test_path', metavar='TEST_PATH',
                             help='Path to a single test file (C or assembly) to verify')
    input_group.add_argument('--test-dir', dest='test_dir', metavar='TEST_DIR',
                             help='Directory containing test files to run (will run all compatible files)')

    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase output verbosity (can be used multiple times)')
    parser.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error'],
                        default='info', help='Set logging level')
    parser.add_argument('--output', dest='output_dir', metavar='OUTPUT_DIR',
                        default='./output', help='Directory to store results')
    parser.add_argument('--config', dest='config_file', metavar='CONFIG_FILE',
                        default='./config/toolchain_config.json',
                        help='Path to custom configuration file')
    parser.add_argument('--force', action='store_true', help='Force continuation even with unsupported Vivado version')

    tools_group = parser.add_argument_group('Tool Paths')
    tools_group.add_argument('--vivado-path', metavar='VIVADO_PATH',
                             help='Custom path to Vivado installation')
    tools_group.add_argument('--spike-path', metavar='SPIKE_PATH',
                             help='Custom path to Spike simulator')
    tools_group.add_argument('--riscv-tools-path', metavar='RISCV_PATH',
                             help='Custom path to RISC-V toolchain')

    sim_group = parser.add_argument_group('Simulation Control')
    sim_group.add_argument('--stop-on-error', action='store_true',
                           help='Stop verification when first error is encountered')
    sim_group.add_argument('--timeout', type=int, default=300,
                           help='Set timeout for test execution in seconds')
    sim_group.add_argument('--max-cycles', type=int, default=10000,
                           help='Maximum number of cycles to simulate')
    sim_group.add_argument('--start-pc', type=lambda x: int(x, 0),
                           help='Starting program counter value (default: from ELF entry point)')
    sim_group.add_argument('--incremental', action='store_true',
                           help='Continue from previous state for batch testing')

    compare_group = parser.add_argument_group('Comparison Options')
    compare_group.add_argument('--compare', choices=['all', 'regs', 'pc', 'mem'],
                               default='all', help='Elements to compare between simulations')
    compare_group.add_argument('--ignore-regs', metavar='LIST',
                               help='Comma-separated list of registers to exclude from comparison')
    compare_group.add_argument('--mem-regions', metavar='LIST',
                               help='Memory regions to compare (format: "start1-end1,start2-end2")')
    compare_group.add_argument('--tolerance', type=int, default=0,
                               help='Allow specified number of cycles difference')

    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--report-format', choices=['text', 'html', 'json'],
                              default='text', help='Format for verification report')
    output_group.add_argument('--dump-state', action='store_true',
                              help='Generate dump files of simulator state at each step')
    output_group.add_argument('--dump-waveform', action='store_true',
                              help='Generate waveform dumps from Vivado simulation')
    output_group.add_argument('--waveform-format', choices=['vcd', 'wlf'],
                              default='vcd', help='Format for waveform dumps')

    args = parser.parse_args()

    if args.test_path:
        args.test_path = Path(args.test_path).resolve()
        if not args.test_path.exists():
            parser.error(f"Test file not found: {args.test_path}")

        valid_extensions = ['.c', '.s', '.S', '.asm']
        if not any(args.test_path.suffix == ext for ext in valid_extensions):
            parser.error(
                f"Invalid test file extension: {args.test_path}. Must be one of: {', '.join(valid_extensions)}")

    if args.test_dir:
        args.test_dir = Path(args.test_dir).resolve()
        if not args.test_dir.exists() or not args.test_dir.is_dir():
            parser.error(f"Test directory not found: {args.test_dir}")

    args.output_dir = Path(args.output_dir).resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.ignore_regs:
        args.ignore_regs = [reg.strip() for reg in args.ignore_regs.split(',')]
    else:
        args.ignore_regs = []

    if args.mem_regions:
        try:
            regions = []
            for region in args.mem_regions.split(','):
                start, end = region.split('-')
                regions.append((int(start, 0), int(end, 0)))
            args.mem_regions = regions
        except ValueError:
            parser.error("Invalid memory region format. Expected format: 'start1-end1,start2-end2'")
    else:
        args.mem_regions = []

    verbosity_map = {
        0: 'warning',
        1: 'info',
        2: 'debug'
    }
    if args.verbose > 0:
        args.log_level = verbosity_map.get(min(args.verbose, 2), 'debug')

    return args


def main() -> None:
    args = parse_args()
    if not args:
        return

    try:
        toolchain_config_data = read_json(args.config_file)
        if not toolchain_config_data:
            default_config_path = Path(__file__).parent / 'config' / 'toolchain_config.json'
            print(f'Trying default config: {default_config_path}')
            toolchain_config_data = read_json(str(default_config_path))
            if not toolchain_config_data:
                default_config_path = Path('.') / 'config' / 'toolchain_config.json'
                print(f'Trying project root config: {default_config_path.resolve()}')
                toolchain_config_data = read_json(str(default_config_path.resolve()))
                if not toolchain_config_data:
                    print('Warning: Could not load toolchain configuration. Proceeding with defaults/CLI args.')
                    toolchain_config_data = {}
    except Exception as e:
        print(f'Error reading toolchain configuration: {e}')
        toolchain_config_data = {}

    print('Looking for Vivado...')
    vivado_version = get_vivado_version(args.vivado_path)
    if vivado_version is None:
        print('Vivado is not correctly installed or not found.')
        return
    else:
        print(f'Vivado found: {vivado_version}')
        supported_versions = toolchain_config_data.get('vivado', {}).get('supported_versions', [])
        if not any(version in vivado_version for version in supported_versions):
            print(f'Warning: Vivado version {vivado_version} is not in the list of supported versions: {supported_versions}')
            if not args.force:
                print('Use --force to continue anyway. Exiting.')
                return
        else:
            print('Vivado version is supported.')

    print('Looking for Spike...')
    if get_spike_installed(args.spike_path):
        spike_loc = args.spike_path if args.spike_path else "system PATH"
        print(f'Spike is installed and accessible from {spike_loc}.')
    else:
        print('Spike is not installed or not accessible.')
        return

    print('\nAll dependencies are satisfied.\n')

    compiled_elf_dir: Path | None = None
    if args.test_dir:
        print(f'Mode: Batch processing tests from directory: {args.test_dir}')
        python_script_dir = Path(__file__).parent.resolve()
        build_script_path = python_script_dir / 'build_scripts' / 'build-tests.sh'

        if not build_script_path.is_file():
            print(f'Error: Build script \'build-tests.sh\' not found at {build_script_path}')
            print('Please ensure \'build-tests.sh\' is correctly located or configure its path.')
            return

        compilation_successful = compile_riscv_tests(
            bash_script_path=build_script_path,
            test_src_dir=args.test_dir,
            output_base_dir=args.output_dir,
            riscv_tools_path=args.riscv_tools_path
        )

        if not compilation_successful:
            print('Test compilation failed. Exiting.')
            return
        else:
            print('Compilation script finished. Check script output for details.')
            compiled_elf_dir = args.output_dir / 'bin'

    elif args.test_path:
        print(f'Mode: Single test file: {args.test_path}')
        if args.test_path.suffix.lower() == '.elf':
            print(f'Using pre-compiled ELF: {args.test_path}')
        else:
            print('For single C/asm files, direct compilation via this script is not yet implemented.')
            print('Please use --test-dir to compile multiple tests, or provide a pre-compiled .elf file.')
            return

    print('\nTool dependencies checked. Compilation (if applicable) handled.')
    print(f'Main output directory for this run: {args.output_dir.resolve()}')
    if compiled_elf_dir:
        print(f'Compiled ELF files should be in: {compiled_elf_dir.resolve()}')

    print('\nStarting Spike simulation...\n')

    if compiled_elf_dir is None:
        print('No compiled ELF directory provided. Exiting.')
        return
    
    spike_sims = []

    for filename in os.listdir(compiled_elf_dir):
        if filename.endswith('.elf'):
            elf_path = compiled_elf_dir / filename
            print(f'Found ELF file: {elf_path}')
            spike_sims.append(
                SpikeInterface(
                    spike_path='spike' if args.spike_path is None else args.spike_path,
                    isa='rv32i',
                    base_opts='-m0x80000000:0x10000,0x20000000:0x1000',
                    start_pc='0x80000000',
                    elf_path=str(elf_path),
                )
            )

    print()

    for spike in sorted(spike_sims, key=lambda x: x.elf_path):
        print(f'Start test {spike.elf_path}? (y/n) ', end='')
        if input().strip().lower() != 'y':
            print('Skipping test.')
            continue

        print(f'Starting Spike simulation for {spike.elf_path}...')
        try:
            spike.start()            
            for i in range(10):
                print(f'Waiting for commit {i + 1}...')
                state = spike.next_commit(timeout=5)
                if state is None:
                    print('No more commits or timeout reached.')
                    break

                print(f'Commit {i + 1}: PC={state.pc}, Instruction={state.inst}, Disasm={state.disasm}')

                for reg, val in state.regs.items():
                    print(f'  x{reg} = {val:#x}')

                for addr, data in state.stores:
                    print(f'  Store: {addr:#x} -> {data:#x}')
        
        except Exception as e:
            print(f'Error during simulation: {e}')
        finally:
            spike.stop()
            print(f'Simulation for {spike.elf_path} completed.\n')


if __name__ == "__main__":
    main()
