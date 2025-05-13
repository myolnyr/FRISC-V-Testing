#!/bin/bash
# build-tests.sh - Script to compile the RV32I tests

# Exit on error
set -e

# Script's directory to find co-located files
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Input arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <test_source_directory> <output_base_directory>"
    exit 1
fi
TEST_SRC_DIR=$1
OUTPUT_BASE_DIR=$2

# Configuration
RISCV_PATH=${RISCV:-$HOME/riscv32}
CC="$RISCV_PATH/bin/riscv32-unknown-elf-gcc"
OBJCOPY="$RISCV_PATH/bin/riscv32-unknown-elf-objcopy"
OBJDUMP="$RISCV_PATH/bin/riscv32-unknown-elf-objdump"

# Ensure the tools exist
if [ ! -x "$CC" ]; then
    echo "Error: $CC not found or not executable"
    echo "Make sure RISCV_PATH is set correctly (currently $RISCV_PATH)"
    exit 1
fi

# Linker script and startup file paths (assumed to be with the script)
LINKER_SCRIPT="$SCRIPT_DIR/linker.ld"
STARTUP_S_FILE="$SCRIPT_DIR/startup.S"

if [ ! -f "$LINKER_SCRIPT" ]; then
    echo "Error: Linker script $LINKER_SCRIPT not found. It should be in the same directory as build-tests.sh."
    exit 1
fi
if [ ! -f "$STARTUP_S_FILE" ]; then
    echo "Error: Startup file $STARTUP_S_FILE not found. It should be in the same directory as build-tests.sh."
    exit 1
fi

# Flags for RV32I bare-metal compilation
CFLAGS="-march=rv32i -mabi=ilp32 -nostdlib -nostartfiles -static -ffreestanding -O2"
LDFLAGS="-T$LINKER_SCRIPT"

# Create output directories within the specified output base directory
BIN_DIR="$OUTPUT_BASE_DIR/bin"
HEX_DIR="$OUTPUT_BASE_DIR/hex"
DISASM_DIR="$OUTPUT_BASE_DIR/disasm"

mkdir -p "$BIN_DIR" "$HEX_DIR" "$DISASM_DIR"

# Compile startup code
echo "Compiling startup code ($STARTUP_S_FILE)..."
$CC "$CFLAGS" -c "$STARTUP_S_FILE" -o "$BIN_DIR/startup.o"

# Compile and link each test
compile_test() {
    local test_full_path=$1
    local test_file_name=$(basename "$test_full_path")
    local output_base=$(basename "$test_file_name" .c) # Assumes .c extension for tests

    echo "Compiling $test_full_path..."

    # Compile C file
    $CC "$CFLAGS" -c "$test_full_path" -o "$BIN_DIR/${output_base}".o

    # Link with startup code
    $CC "$CFLAGS" "$LDFLAGS" -o "$BIN_DIR/${output_base}".elf "$BIN_DIR/startup.o" "$BIN_DIR/${output_base}".o

    # Generate HEX file for memory initialization
    $OBJCOPY -O verilog "$BIN_DIR/${output_base}".elf "$HEX_DIR/${output_base}".hex

    # Generate binary file
    $OBJCOPY -O binary "$BIN_DIR/${output_base}".elf "$BIN_DIR/${output_base}".bin

    # Generate disassembly for analysis
    $OBJDUMP -d "$BIN_DIR/${output_base}".elf > "$DISASM_DIR/${output_base}".lst

    echo "Built $output_base (ELF: $BIN_DIR/${output_base}.elf)"
}

# Compile all test files from the specified source directory
if [ ! -d "$TEST_SRC_DIR" ]; then
    echo "Error: Test source directory $TEST_SRC_DIR not found."
    exit 1
fi

echo "Compiling tests from $TEST_SRC_DIR matching test*.c, outputting to $OUTPUT_BASE_DIR..."
found_tests=0
# Use find to robustly handle cases with no matches or special filenames
# -maxdepth 1 ensures we only look in the immediate TEST_SRC_DIR, not subdirectories
find "$TEST_SRC_DIR" -maxdepth 1 -name 'test*.c' -type f -print0 | while IFS= read -r -d $'\0' test_file_path; do
    compile_test "$test_file_path"
    found_tests=$((found_tests + 1))
done

if [ "$found_tests" -gt 0 ]; then
    echo "All $found_tests found C test(s) compiled successfully!"
    echo "- ELF binaries are in $BIN_DIR/"
    echo "- HEX files for memory initialization are in $HEX_DIR/"
    echo "- Disassemblies are in $DISASM_DIR/"
else
    echo "Warning: No .c test files found matching 'test*.c' in $TEST_SRC_DIR."
    # Depending on requirements, you might want to 'exit 1' here if no tests is an error.
fi

echo "Build process finished."