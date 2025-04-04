import random
import subprocess
import shutil
import sys
import os
import argparse
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep

FILE_WIDTH = 50
INTERMEDIATE_EXTENSION = '.e'
BINARY_EXTENSION = '.b'
BIN_DIR = 'temp_bin/'
TXT_DIR = 'temp_txt/'


def confirm_vivado():
    print('Looking for Vivado...')

    vivado_cmd = shutil.which('vivado')
    if not vivado_cmd:
        print('Vivado is not installed or not in the system PATH.')
        clean_up(exit_code=0)

    try:
        result = subprocess.run([vivado_cmd, '-version'], capture_output=True, text=True, check=True)
        print(f'Found {result.stdout.splitlines()[0]}')
    except subprocess.CalledProcessError as e:
        print(f'Error executing Vivado: {e}')
        clean_up(exit_code=1)


def create_directory(directory_name):
    try:
        os.makedirs(directory_name, exist_ok=False)
        print(f"Directory '{directory_name}' created successfully.")
    except FileExistsError:
        print(f"Error: Directory '{directory_name}' already exists.")
        clean_up(exit_code=1)
    except PermissionError:
        print(f"Error: Permission denied. Cannot create directory '{directory_name}'.")
        clean_up(exit_code=1)
    except OSError as e:
        print(f"Error: Failed to create directory '{directory_name}': {e}")
        clean_up(exit_code=1)


def delete_directory(directory_name):
    try:
        # Get the full path of the directory in the current working directory
        dir_path = os.path.join(os.getcwd(), directory_name)

        # Check if it's a directory
        if os.path.isdir(dir_path):
            # Remove directory and all its contents
            shutil.rmtree(dir_path)
            print(f"Directory '{directory_name}' has been deleted.")
        else:
            # It exists but is not a directory
            print(f"'{directory_name}' exists but is not a directory.")
    except FileNotFoundError:
        # Directory doesn't exist - silently ignore
        print(f"Directory '{directory_name}' doesn't exist. Nothing to delete.")
    except PermissionError:
        print(f"Permission denied when trying to delete '{directory_name}'.")
    except OSError as e:
        print(f"Error deleting directory '{directory_name}': {e}")


def get_files_to_process():
    # Create a custom help formatter to customize the help output
    class CustomHelpFormatter(argparse.HelpFormatter):
        def _format_usage(self, usage, actions, groups, prefix):
            return """Usage: python script.py [OPTIONS]

    A utility for processing and simulating files with Vivado.

    File Selection Options:
      -a, --all            Process all files with appropriate extension in current directory
                           (default if no selection method is specified)
      -d DIR, --dir DIR    Process all files with appropriate extension in specified directory
      -f FILE [FILE ...], --file FILE [FILE ...]
                           Process specific file(s)

    Processing Options:
      -s, --sequential     Run simulations sequentially instead of in parallel
      -p N, --parallel N   Run up to N simulations in parallel (cannot be used with -s)
      -b, --binary         Process binary (.b) files directly instead of intermediate (.e) files

    General Options:
      -h, --help           Show this help message and exit

    Description:
      This script automates the process of converting intermediate files to binary format
      and running simulations with Vivado. It checks for Vivado installation, creates
      temporary directories, processes the selected files, and displays simulation results
      in a tabular format.

      When using intermediate files (.e), the script first converts them to binary format
      before simulation. When using binary files (.b), it runs simulations directly.

      Results are displayed with PASS/FAIL status for each processed file.

    Examples:
      python script.py                    # Process all .e files in current directory
      python script.py -a                 # Same as above
      python script.py -d tests/          # Process all .e files in tests/ directory
      python script.py -f test1.e test2.e # Process only specified files
      python script.py -b                 # Process all .b files in current directory
      python script.py -s -f test1.e      # Process test1.e sequentially
      python script.py -p 2 -f test1.e test2.e test3.e # Process files with max 2 parallel simulations
    """

    # Use the custom formatter when creating the parser
    parser = argparse.ArgumentParser(
        description="Process files based on command line arguments",
        formatter_class=CustomHelpFormatter,
        add_help=True
    )

    group = parser.add_argument_group('file selection')
    group.add_argument('-a', '--all', action='store_true', help='Process all files in current directory')
    group.add_argument('-d', '--dir', type=str, help='Process all files in specified directory')
    group.add_argument('-f', '--file', nargs='+', help='Process specific file(s)')

    # Add parallel option and make it mutually exclusive with sequential
    execution_group = parser.add_mutually_exclusive_group()
    execution_group.add_argument('-s', '--sequential', action='store_true', help="Run simulations sequentially")
    execution_group.add_argument('-p', '--parallel', type=int, metavar='N', help="Run up to N simulations in parallel")

    parser.add_argument('-b', '--binary', action='store_true',
                        help="Process binary files instead of intermediate files")

    args = parser.parse_args()

    extension = BINARY_EXTENSION if args.binary else INTERMEDIATE_EXTENSION

    if extension and not extension.startswith('.'):
        extension = '.' + extension

    if not (args.all or args.dir or args.file):
        args.all = True

    selected_options = sum([bool(args.all), bool(args.dir), bool(args.file)])
    if selected_options > 1:
        print("Error: Please use only one file selection method (-a, -d, or -f)")
        clean_up(exit_code=0)

    # Check if parallel value is valid
    if args.parallel is not None and args.parallel < 1:
        print("Error: Number of parallel simulations must be at least 1")
        clean_up(exit_code=0)

    files_to_process = []

    def has_correct_extension(path):
        return path.endswith(extension)

    if args.all:
        files = glob.glob(f'*{extension}')
        files_to_process.extend(os.path.abspath(f) for f in files if os.path.isfile(f))

    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"Error: Directory '{args.dir}' does not exist")
            clean_up(exit_code=0)
        files = glob.glob(os.path.join(args.dir, f'*{extension}'))
        files_to_process.extend(os.path.abspath(f) for f in files if os.path.isfile(f))

    elif args.file:
        for file_path in args.file:
            if not os.path.isfile(file_path):
                print(f"Warning: File '{file_path}' does not exist")
                continue
            if has_correct_extension(file_path):
                files_to_process.append(os.path.abspath(file_path))
            else:
                print(f"Warning: File '{file_path}' does not have the required '{extension}' extension")

    return files_to_process, args.sequential, args.parallel, args.binary, extension


def run_test(binary_file):
    expected_state = get_expected_state(binary_file)
    simulated_state = run_vivado_simulation(binary_file)
    errors = compare_states(expected_state, simulated_state)
    return False if errors else True


def truncate_filename(filename, max_length=40):
    if len(filename) <= max_length:
        return filename

    parts = filename.split("/")
    left, right = [], []
    length = 5

    for part in parts:
        if length + len(part) + 1 < max_length // 2:
            left.append(part)
            length += len(part) + 1
        else:
            break

    for part in reversed(parts):
        if length + len(part) + 1 < max_length:
            right.insert(0, part)
            length += len(part) + 1
        else:
            break

    return "/".join(left) + "/.../" + "/".join(right)


def print_table(files, results, statuses, initial=False):
    table_header = (
        f"\nResults Summary:\n"
        f"{'=' * (FILE_WIDTH + 20)}\n"
        f"{'File':<{FILE_WIDTH}} {'Status':<10} {'Result':<10}\n"
        f"{'=' * (FILE_WIDTH + 20)}"
    )

    if not initial:
        lines_to_move_up = len(files) + 6
        print(f"\033[{lines_to_move_up}F", end='', flush=True)

    print(table_header)

    for file in files:
        status = statuses[file]
        result_text = results.get(file, "N/A")
        color = "\033[92m" if result_text == "PASS" else "\033[91m" if result_text == "FAIL" else "\033[93m"
        truncated_name = truncate_filename(file, FILE_WIDTH)
        print(f"{truncated_name:<{FILE_WIDTH}} {status:<10} {color}{result_text}\033[0m\033[K")

    print("=" * (FILE_WIDTH + 20))


def run_simulations(files, sequential, parallel_count=None):
    statuses = {file: "Waiting" for file in files}
    results = {}

    print_table(files, results, statuses, initial=True)

    if sequential:
        for file in files:
            statuses[file] = "Running"
            print_table(files, results, statuses)
            test_passed = run_test(file)
            results[file] = "PASS" if test_passed else "FAIL"
            statuses[file] = "Done"
            print_table(files, results, statuses)

    else:
        # If parallel_count is specified, limit the number of workers
        max_workers = parallel_count if parallel_count is not None else None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_test, file): file for file in files}

            # Initialize running futures set
            running_futures = set()

            # Set initial running status for files that start immediately
            # Calculate how many workers are actually available
            worker_count = min(len(files),
                               executor._max_workers if hasattr(executor, '_max_workers') else len(files))

            # Mark the first batch of files as running
            for i, (future, file) in enumerate(list(futures.items())[:worker_count]):
                statuses[file] = "Running"
                running_futures.add(future)

            # Update the table with initial running statuses
            print_table(files, results, statuses)

            for future in as_completed(futures):
                file = futures[future]
                try:
                    test_passed = future.result()
                    results[file] = "PASS" if test_passed else "FAIL"
                    statuses[file] = "Done"
                except Exception as _:
                    results[file] = "ERROR"
                    statuses[file] = "Error"

                # Update the status of pending files
                running_futures.discard(future)

                # Find next waiting file to mark as running
                for f, f_file in futures.items():
                    if f not in running_futures and statuses[f_file] == "Waiting" and not f.done():
                        statuses[f_file] = "Running"
                        running_futures.add(f)
                        break

                print_table(files, results, statuses)

    passed_count = sum(1 for r in results.values() if r == "PASS")
    failed_count = sum(1 for r in results.values() if r == "FAIL")
    print(f"\nTotal: {len(files)} | \033[92mPassed: {passed_count}\033[0m | \033[91mFailed: {failed_count}\033[0m")


def convert_to_binary(filepath):
    filename = os.path.basename(filepath)
    base_name = os.path.splitext(filename)[0]

    if not filename.endswith(INTERMEDIATE_EXTENSION):
        return

    with open(filepath, "r", encoding="utf-8") as zad:
        read_lines = zad.readlines()

    word = [0, 0, 0, 0]
    flag = 0
    program = []
    new_version = True

    for line in read_lines:
        line_split = line.split()
        if len(line_split) > 3 and line_split[0][0] == "<" and line_split[1][0] != ";":
            if line_split[3] == ";":
                new_version = False
                break

    if new_version:
        program_to_write = "logic [31:0] debug_memory [];\ninitial begin\ndebug_memory = new[];\n"
        bytes_location = {0: "7:0", 1: "15:8", 2: "23:16", 3: "31:24"}
        address = 0
        for line in read_lines:
            line_split = line.split()
            try:
                if len(line_split) < 2:
                    continue

                if line_split[0][0] == "<" and line_split[1][0] != ";":
                    if line_split[1][-1] == "!":
                        line_split[1] = line_split[1][:-1]

                    try:
                        address = int(line_split[1], 16) // 4
                        offset = int(line_split[1], 16) % 4
                    except ValueError as ve:
                        print(f"Invalid address value: {line_split[1]} - {ve}")
                        continue

                    for string in line_split[2:6]:
                        if string[0] == ";":
                            break
                        if offset in bytes_location:
                            program_to_write += (
                                f"debug_memory[{address}][{bytes_location[offset]}] = 8'h{string};\n"
                            )
                            offset += 1
                        else:
                            print(f"Invalid offset: {offset}")
                elif line_split[0] == "|":
                    address += 1
                    if address > 1023:
                        raise ValueError(f"Address exceeds 1023: {address} in file {filepath}")
                    offset = 0
                    for string in line_split[1:]:
                        if offset in bytes_location:
                            program_to_write += (
                                f"debug_memory[{address}][{bytes_location[offset]}] = 8'h{string};\n"
                            )
                            offset += 1
                        else:
                            print(f"Invalid offset: {offset}")
            except Exception as e:
                print(f"Error processing line '{line}': {e}")
                continue

        program_to_write += "end"
        program_to_write = program_to_write.replace("new[]", f"new[{address + 1}]")

        txt_file_path = os.path.join(TXT_DIR, f"{base_name}.txt")
        with open(txt_file_path, "w", encoding="utf-8") as program_file_destination:
            program_file_destination.write(program_to_write)

    else:
        address = 0
        offset = 0
        bytes_location = {0: "7:0", 1: "15:8", 2: "23:16", 3: "31:24"}
        program_to_write = "logic [31:0] debug_memory [];\ninitial begin\ndebug_memory = new[];\n"
        for line in read_lines:
            line_split = line.split()

            if len(line_split) > 0 and line_split[0][0] == "|":
                program_to_write += f"debug_memory[{address}][{bytes_location[offset]}] = 8'h{line_split[1]};\n"
                offset += 1

            elif len(line_split) > 1 and line_split[0][0] == "<" and line_split[1][0] != ";":
                address = int(line_split[1], 16) // 4
                offset = int(line_split[1], 16) % 4
                program_to_write += f"debug_memory[{address}][{bytes_location[offset]}] = 8'h{line_split[2]};\n"
                offset += 1

        txt_file_path = os.path.join(TXT_DIR, f"{base_name}.txt")
        with open(txt_file_path, "w", encoding="utf-8") as program_file_destination:
            program_to_write += "end"
            program_file_destination.write(program_to_write)

    # Process .b files
    if new_version:
        for line in read_lines:
            line_split = line.split()
            try:
                if len(line_split) < 2:
                    continue
                if line_split[0][0] == "<" and line_split[1][0] != ";":
                    word[0] = str(line_split[5])
                    word[1] = str(line_split[4])
                    word[2] = str(line_split[3])
                    word[3] = str(line_split[2])
                    program.append("".join(word))
            except Exception as _:
                print(f"File {filepath} parsed.")
    else:
        for line in read_lines:
            line_split = line.split()
            try:
                if len(line_split) < 2:
                    continue
                if flag > 0:
                    flag = flag - 1
                    word[0 + flag] = str(line_split[1])
                    if flag == 0:
                        program.append("".join(word))

                elif line_split[0][0] == "<" and line_split[1][0] != ";":
                    word[3] = str(line_split[2])
                    flag = 3
            except Exception as _:
                print(f"File {filepath} parsed.")

    binary_file_path = os.path.join(BIN_DIR, f"{base_name}{BINARY_EXTENSION}")
    with open(binary_file_path, "wb") as binary_file_destination:
        counter = 0
        for line in program:
            binary_file_destination.write(int(line, 16).to_bytes(4, byteorder='little'))
            counter += 1


def run_reference_model(binary_file):
    # Uses Spike to get the expected output for given binary
    return dict()


def parse_simulation_output(simulation_output_file):
    return dict()


def get_expected_state(binary_file):
    # { 'x1': 0x1, 'x2': 0x2, ... , 'mem[0x100]': 0xdeadbeef }
    expected_state = run_reference_model(binary_file)
    return expected_state


def run_vivado_simulation(binary_file):
    # subprocess.run(['vivado', '-mode', 'batch', '-source', 'run_sim.tcl'])
    sleep(random.uniform(1, 3))
    sim_state = parse_simulation_output('sim_output.txt')
    return sim_state


def compare_states(expected, simulated):
    errors = []
    for key in expected:
        if key not in simulated or expected[key] != simulated[key]:
            errors.append((key, expected.get(key), simulated.get(key)))
    return errors


def clean_up(exit_code=None):
    print('Cleaning up...')
    delete_directory(BIN_DIR)
    delete_directory(TXT_DIR)
    if exit_code is not None:
        sys.exit(exit_code)


def main():
    files, sequential, parallel_count, use_binary, extension = get_files_to_process()

    confirm_vivado()
    print()

    print('Creating directories...')
    create_directory(BIN_DIR)
    create_directory(TXT_DIR)
    print()

    print(f'Using {"binary" if use_binary else "intermediate"} file extension: {extension}')

    if not files:
        print('No files to process')
        clean_up(exit_code=0)
    print()

    print(f'Found {len(files)} {"file" if len(files) == 1 else "files"} to process:')
    for file in files:
        print(f' - {file}')

    # If processing intermediate files, convert them to binary first
    if not use_binary:
        print('\nConverting files to binary format...')
        for file in files:
            print(f' - {file} ', end='')
            convert_to_binary(file)
            print(f'DONE')
        # Update files list to point to the generated binary files
        binary_files = []
        for file in files:
            filename = os.path.basename(file)
            base_name = os.path.splitext(filename)[0]
            binary_file_path = os.path.join(BIN_DIR, f"{base_name}{BINARY_EXTENSION}")
            binary_files.append(binary_file_path)
        files = binary_files
        print('Converted all files to binary')

    # Show the execution mode
    if sequential:
        print('\nRunning simulations sequentially')
    elif parallel_count:
        print(f'\nRunning simulations with maximum {parallel_count} parallel tasks')
    else:
        print('\nRunning all simulations in parallel')

    run_simulations(files, sequential, parallel_count)
    print()

    clean_up(exit_code=None)
    print('\033[92mDONE\033[0m')


if __name__ == '__main__':
    main()
