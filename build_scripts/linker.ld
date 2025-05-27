/* linker.ld - Linker script for bare-metal RV32I tests */
OUTPUT_ARCH(riscv)
ENTRY(_start_asm)

MEMORY
{
    /* Code and read-only data - Read and Execute only */
    ROM (rx)  : ORIGIN = 0x80000000, LENGTH = 32K
    /* Read-write data - Read and Write only */
    RAM (rw)  : ORIGIN = 0x80008000, LENGTH = 32K
}

SECTIONS
{
    . = 0x80000000;

    /* Executable sections - ROM region */
    .text : {
        *(.text.init)
        *(.text)
        *(.text.*)
        . = ALIGN(4);
        _etext = .;
    } > ROM

    /* Read-only data - ROM region */
    .rodata : {
        *(.rodata)
        *(.rodata.*)
        . = ALIGN(4);
        _erodata = .;
    } > ROM

    /* Initialized data - Load in ROM, run in RAM */
    .data : AT(_erodata) {
        . = ALIGN(4);
        _data_start = .;
        *(.data)
        *(.data.*)
        . = ALIGN(4);
        _data_end = .;
    } > RAM

    /* Uninitialized data - RAM region */
    .bss : {
        . = ALIGN(4);
        PROVIDE(_bss_start = .);
        *(.bss)
        *(.bss.*)
        *(COMMON)
        . = ALIGN(4);
        PROVIDE(_bss_end = .);
    } > RAM

    /* Stack - at end of RAM */
    .stack (NOLOAD) : {
        . = ALIGN(16);
        . = . + 4K; /* 4KB stack */
        _stack_top = .;
    } > RAM

    /* Ensure we don't exceed memory bounds */
    ASSERT(. <= 0x80010000, "Program too large for memory")
}
