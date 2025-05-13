# Check for required dependencies --
# Parse command-line arguments
# Load configuration
# Initialize components
# Run tests
# Generate reports

import shutil
import subprocess
import json
import argparse
import os
from pathlib import Path


def read_json(path: str) -> dict:
    """
    Read and parse a JSON configuration file.

    Args:
        path: Path to the JSON file

    Returns:
        Parsed JSON data as a dictionary
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file {path} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Configuration file {path} is not valid JSON.")
        return {}


def get_vivado_version(custom_path: str | None = None) -> str | None:
    """
    Get the Vivado version if installed.

    Args:
        custom_path: Optional custom path to Vivado installation

    Returns:
        Version string or None if Vivado is not found
    """
    if custom_path:
        # Check if the provided custom path is valid
        possible_cmd_path = os.path.join(custom_path, 'bin', 'vivado')
        if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
            vivado_cmd = possible_cmd_path
        else:
            print(f"Warning: Custom Vivado path {custom_path} is invalid.")
            return None
    else:
        # Try to find Vivado in the system PATH
        vivado_cmd = shutil.which('vivado')

    if not vivado_cmd:
        return None

    try:
        result = subprocess.run([vivado_cmd, '-version'], capture_output=True, text=True, check=True)
        return result.stdout.splitlines()[0]
    except subprocess.CalledProcessError as e:
        print(f'Error executing Vivado: {e}')
        return None


def get_spike_installed(custom_path: str | None = None) -> bool:
    """
    Check if Spike is installed and accessible.

    Args:
        custom_path: Optional custom path to Spike installation

    Returns:
        True if Spike is installed and working, False otherwise
    """
    if custom_path:
        # Check if the provided custom path is valid
        possible_cmd_path = os.path.join(custom_path, 'spike')
        if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
            spike_cmd = possible_cmd_path
        else:
            # Try the bin subdirectory
            possible_cmd_path = os.path.join(custom_path, 'bin', 'spike')
            if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
                spike_cmd = possible_cmd_path
            else:
                print(f"Warning: Custom Spike path {custom_path} is invalid.")
                return False
    else:
        # Try to find Spike in the system PATH
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
        print(f'Error: Spike executable not found at {spike_cmd}')
        return False


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

    # Core arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--test', dest='test_path', metavar='TEST_PATH',
                             help='Path to a single test file (C or assembly) to verify')
    input_group.add_argument('--test-dir', dest='test_dir', metavar='TEST_DIR',
                             help='Directory containing test files to run (will run all compatible files)')

    parser.add_argument('--mode', choices=['single', 'batch'], default='single',
                        help='Run in single test mode or batch mode')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase output verbosity (can be used multiple times)')
    parser.add_argument('--log-level', choices=['debug', 'info', 'warning', 'error'],
                        default='info', help='Set logging level')
    parser.add_argument('--output', dest='output_dir', metavar='OUTPUT_DIR',
                        default='./output', help='Directory to store results')
    parser.add_argument('--config', dest='config_file', metavar='CONFIG_FILE',
                        default='./config/toolchain_config.json',
                        help='Path to custom configuration file')

    # Tool path arguments
    tools_group = parser.add_argument_group('Tool Paths')
    tools_group.add_argument('--vivado-path', metavar='VIVADO_PATH',
                             help='Custom path to Vivado installation')
    tools_group.add_argument('--spike-path', metavar='SPIKE_PATH',
                             help='Custom path to Spike simulator')
    tools_group.add_argument('--riscv-tools-path', metavar='RISCV_PATH',
                             help='Custom path to RISC-V toolchain')

    # Simulation control arguments
    sim_group = parser.add_argument_group('Simulation Control')
    sim_group.add_argument('--stop-on-error', action='store_true',
                           help='Stop verification when first error is encountered')
    sim_group.add_argument('--timeout', type=int, default=300,
                           help='Set timeout for test execution in seconds')
    sim_group.add_argument('--max-cycles', type=int, default=10000,
                           help='Maximum number of cycles to simulate')
    sim_group.add_argument('--start-pc', type=lambda x: int(x, 0),  # Allows 0x prefixed hex values
                           help='Starting program counter value (default: from ELF entry point)')
    sim_group.add_argument('--incremental', action='store_true',
                           help='Continue from previous state for batch testing')

    # Comparison arguments
    compare_group = parser.add_argument_group('Comparison Options')
    compare_group.add_argument('--compare', choices=['all', 'regs', 'pc', 'mem'],
                               default='all', help='Elements to compare between simulations')
    compare_group.add_argument('--ignore-regs', metavar='LIST',
                               help='Comma-separated list of registers to exclude from comparison')
    compare_group.add_argument('--mem-regions', metavar='LIST',
                               help='Memory regions to compare (format: "start1-end1,start2-end2")')
    compare_group.add_argument('--tolerance', type=int, default=0,
                               help='Allow specified number of cycles difference')

    # Output arguments
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

    # Post-processing and validation of arguments
    if args.test_path:
        args.test_path = Path(args.test_path).resolve()
        if not args.test_path.exists():
            parser.error(f"Test file not found: {args.test_path}")

        # Check if file is a valid C or assembly file
        valid_extensions = ['.c', '.s', '.S', '.asm']
        if not any(args.test_path.suffix == ext for ext in valid_extensions):
            parser.error(
                f"Invalid test file extension: {args.test_path}. Must be one of: {', '.join(valid_extensions)}")

    if args.test_dir:
        args.test_dir = Path(args.test_dir).resolve()
        if not args.test_dir.exists() or not args.test_dir.is_dir():
            parser.error(f"Test directory not found: {args.test_dir}")

    # Create the output directory if it doesn't exist
    args.output_dir = Path(args.output_dir).resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Process ignore-regs to a list if provided
    if args.ignore_regs:
        args.ignore_regs = [reg.strip() for reg in args.ignore_regs.split(',')]
    else:
        args.ignore_regs = []

    # Process memory regions to a list of tuples if provided
    if args.mem_regions:
        try:
            regions = []
            for region in args.mem_regions.split(','):
                start, end = region.split('-')
                regions.append((int(start, 0), int(end, 0)))  # Allow hex input with 0x prefix
            args.mem_regions = regions
        except ValueError:
            parser.error("Invalid memory region format. Expected format: 'start1-end1,start2-end2'")
    else:
        args.mem_regions = []

    # Set up the log level based on verbosity
    verbosity_map = {
        0: 'warning',
        1: 'info',
        2: 'debug'
    }
    # Override log_level if the verbose flag is used
    if args.verbose > 0:
        args.log_level = verbosity_map.get(min(args.verbose, 2), 'debug')

    return args


def main():
    """
    Main function to run the verification toolchain.
    """
    args = parse_args()

    # Read configuration files
    try:
        vivado_config = read_json(args.config_file)
        if not vivado_config:
            vivado_config = read_json('./config/vivado_config.json')
            if not vivado_config:
                print("Error: Could not load Vivado configuration.")
                return
    except Exception as e:
        print(f"Error reading configuration: {e}")
        return

    # Check if Vivado is installed and in system PATH or custom path
    print('Looking for Vivado...')
    vivado_version = get_vivado_version(args.vivado_path)

    if vivado_version is None:
        print('Vivado is not correctly installed or not found in the specified location.')
        print('Please make sure Vivado is installed and in the system PATH, or provide a valid path using --vivado-path.')
        return
    else:
        print(f'Vivado found: {vivado_version}')

    # Check if the Vivado version is supported
    supported_versions = vivado_config.get('supported_versions', [])
    if not supported_versions:
        print("Warning: No supported Vivado versions specified in configuration.")
    else:
        for version in supported_versions:
            if version in vivado_version:
                print(f'Vivado version {version} is supported.')
                break
        else:
            print(f'Warning: Vivado version {vivado_version} is not in the list of supported versions.')
            print(f'Supported Vivado versions:')
            for version in supported_versions:
                print(f'  - {version}')
            if not args.force:
                print("Use --force to continue anyway.")
                return

    # Check if Spike is installed and in system PATH or custom path
    print('Looking for Spike...')
    if get_spike_installed(args.spike_path):
        spike_path = args.spike_path if args.spike_path else "system PATH"
        print(f'Spike is installed and accessible from {spike_path}.')
    else:
        print('Spike is not installed or not accessible from the specified location.')
        print('Please install Spike or provide a valid path using --spike-path.')
        print('You can use the provided script scripts/install_spike.sh to install Spike.')
        return

    print('\nAll dependencies are satisfied.\n')

    # Continue with the main verification workflow
    # ...


if __name__ == "__main__":
    main()
