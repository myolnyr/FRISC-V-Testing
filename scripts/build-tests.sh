#!/bin/bash
# build-tests.sh - Script to compile the RV32I tests

# Exit on error
set -e

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

# Flags for RV32I bare-metal compilation
CFLAGS="-march=rv32i -mabi=ilp32 -nostdlib -nostartfiles -static -ffreestanding -O2"
LDFLAGS="-Tlinker.ld"

# Create output directories
mkdir -p bin hex disasm

# Compile startup code
echo "Compiling startup code..."
$CC "$CFLAGS" -c startup.S -o bin/startup.o

# Compile and link each test
compile_test() {
    local test_file=$1
    local output_base=$(basename "$test_file" .c)

    echo "Compiling $test_file..."

    # Compile C file
    $CC "$CFLAGS" -c "$test_file" -o bin/"${output_base}".o

    # Link with startup code
    $CC "$CFLAGS" $LDFLAGS -o bin/"${output_base}".elf bin/startup.o bin/"${output_base}".o

    # Generate HEX file for memory initialization
    $OBJCOPY -O verilog bin/"${output_base}".elf hex/"${output_base}".hex

    # Generate binary file
    $OBJCOPY -O binary bin/"${output_base}".elf bin/"${output_base}".bin

    # Generate disassembly for analysis
    $OBJDUMP -d bin/"${output_base}".elf > disasm/"${output_base}".lst

    echo "Built $output_base"
}

# Compile all test files
for test_file in test*.c; do
    compile_test "$test_file"
done

echo "All tests compiled successfully!"
echo "- ELF binaries are in bin/"
echo "- HEX files for memory initialization are in hex/"
echo "- Disassemblies are in disasm/"