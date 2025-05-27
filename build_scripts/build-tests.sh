#!/bin/bash
# build-tests.sh - Script to compile the RV32I tests

# Exit on error
set -e

# Color definitions and symbols
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Unicode symbols
CHECK_MARK="✓"
CROSS_MARK="✗"
WARNING="⚠"
INFO="ℹ"
GEAR="⚙"

# Function to print colored messages
print_success() {
    echo -e "${GREEN}${CHECK_MARK}${NC} $1"
}

print_error() {
    echo -e "${RED}${CROSS_MARK}${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}${WARNING}${NC} $1"
}

print_info() {
    echo -e "${BLUE}${INFO}${NC} $1"
}

print_processing() {
    echo -e "${CYAN}${GEAR}${NC} $1"
}

print_header() {
    echo -e "${PURPLE}=== $1 ===${NC}"
}

# Script's directory to find co-located files
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Input arguments
if [ "$#" -ne 2 ]; then
    print_error "Usage: $0 <test_source_directory> <output_base_directory>"
    exit 1
fi
TEST_SRC_DIR=$1
OUTPUT_BASE_DIR=$2

print_header "RV32I Test Compilation Script"

# Configuration
RISCV_PATH=${RISCV:-$HOME/riscv32}
CC="$RISCV_PATH/bin/riscv32-unknown-elf-gcc"
OBJCOPY="$RISCV_PATH/bin/riscv32-unknown-elf-objcopy"
OBJDUMP="$RISCV_PATH/bin/riscv32-unknown-elf-objdump"

# Ensure the tools exist
if [ ! -x "$CC" ]; then
    print_error "Compiler $CC not found or not executable"
    print_error "Make sure RISCV_PATH is set correctly (currently $RISCV_PATH)"
    exit 1
fi

print_success "Found RISC-V toolchain at $RISCV_PATH"

# Linker script and startup file paths (assumed to be with the script)
LINKER_SCRIPT="$SCRIPT_DIR/linker.ld"
STARTUP_S_FILE="$SCRIPT_DIR/startup.S"

if [ ! -f "$LINKER_SCRIPT" ]; then
    print_error "Linker script $LINKER_SCRIPT not found. It should be in the same directory as build-tests.sh."
    exit 1
fi
if [ ! -f "$STARTUP_S_FILE" ]; then
    print_error "Startup file $STARTUP_S_FILE not found. It should be in the same directory as build-tests.sh."
    exit 1
fi

print_success "Found linker script and startup files"

# Flags for RV32I bare-metal compilation
CFLAGS=(-march=rv32i -mabi=ilp32 -nostdlib -nostartfiles -static -ffreestanding -O2 -Wl,--no-warn-rwx-segments)
LDFLAGS="-T$LINKER_SCRIPT"

# Create output directories within the specified output base directory
BIN_DIR="$OUTPUT_BASE_DIR/bin"
HEX_DIR="$OUTPUT_BASE_DIR/hex"
DISASM_DIR="$OUTPUT_BASE_DIR/disasm"

print_processing "Creating output directories..."
mkdir -p "$BIN_DIR" "$HEX_DIR" "$DISASM_DIR"
print_success "Created output directories"

# Compile startup code
print_processing "Compiling startup code ($STARTUP_S_FILE)..."
if $CC "${CFLAGS[@]}" -c "$STARTUP_S_FILE" -o "$BIN_DIR/startup.o" 2>/dev/null; then
    print_success "Compiled startup code"
else
    print_error "Failed to compile startup code"
    exit 1
fi

# Compile and link each test
compile_test() {
    local test_full_path=$1
    local test_file_name=$(basename "$test_full_path")
    local output_base=$(basename "$test_file_name" .c)

    print_processing "Compiling $test_file_name..."

    # Compile the actual test file
    if ! $CC "${CFLAGS[@]}" -c "$test_full_path" -o "$BIN_DIR/${output_base}.o" 2>/dev/null; then
        print_error "Failed to compile $test_file_name"
        return 1
    fi

    # Link with startup code
    if ! $CC "${CFLAGS[@]}" "$LDFLAGS" -o "$BIN_DIR/${output_base}.elf" \
        "$BIN_DIR/startup.o" "$BIN_DIR/${output_base}.o" -lgcc 2>/dev/null; then
        print_error "Failed to link $test_file_name"
        return 1
    fi

    # Generate HEX file for memory initialization
    if ! $OBJCOPY -O verilog "$BIN_DIR/${output_base}.elf" "$HEX_DIR/${output_base}.hex" 2>/dev/null; then
        print_error "Failed to generate HEX file for $test_file_name"
        return 1
    fi

    # Generate binary file
    if ! $OBJCOPY -O binary "$BIN_DIR/${output_base}.elf" "$BIN_DIR/${output_base}.bin" 2>/dev/null; then
        print_error "Failed to generate binary file for $test_file_name"
        return 1
    fi

    # Generate disassembly for analysis
    if ! $OBJDUMP -d -M no-aliases,numeric "$BIN_DIR/${output_base}.elf" > "$DISASM_DIR/${output_base}.lst" 2>/dev/null; then
        print_error "Failed to generate disassembly for $test_file_name"
        return 1
    fi

    print_success "Built $output_base successfully"
    print_info "  ELF: $BIN_DIR/${output_base}.elf"
    print_info "  HEX: $HEX_DIR/${output_base}.hex"
    print_info "  LST: $DISASM_DIR/${output_base}.lst"
    return 0
}

# Compile all test files from the specified source directory
if [ ! -d "$TEST_SRC_DIR" ]; then
    print_error "Test source directory $TEST_SRC_DIR not found."
    exit 1
fi

print_header "Compiling Tests"
print_info "Source directory: $TEST_SRC_DIR"
print_info "Output directory: $OUTPUT_BASE_DIR"

found_tests=0
failed_tests=0
successful_tests=0

# Temporarily disable exit on error for individual test compilation
set +e

# Use find to robustly handle cases with no matches or special filenames
while IFS= read -r -d $'\0' test_file_path; do
    if compile_test "$test_file_path"; then
        successful_tests=$((successful_tests + 1))
    else
        failed_tests=$((failed_tests + 1))
    fi
    found_tests=$((found_tests + 1))
done < <(find "$TEST_SRC_DIR" -maxdepth 1 -name 'test*.c' -type f -print0)

# Re-enable exit on error
set -e

echo # Empty line for spacing

if [ "$found_tests" -eq 0 ]; then
    print_warning "No .c test files found matching 'test*.c' in $TEST_SRC_DIR"
    exit 0
fi

# Print summary
print_header "Build Summary"
print_info "Total tests found: $found_tests"
print_success "Successful builds: $successful_tests"

if [ "$failed_tests" -gt 0 ]; then
    print_error "Failed builds: $failed_tests"
    print_error "Build process completed with errors"
    exit 1
else
    print_success "All tests compiled successfully!"
    print_info "Output locations:"
    print_info "  ELF binaries: $BIN_DIR/"
    print_info "  HEX files: $HEX_DIR/"
    print_info "  Disassemblies: $DISASM_DIR/"
    print_success "Build process completed successfully"
fi
