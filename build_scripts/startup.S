// startup.S - Assembly startup code for RV32I bare-metal
.section .text.init
.globl _start_asm

_start_asm:
    # Initialize stack pointer
    li sp, 0x000003FC

    # Clear BSS section
    la a0, _bss_start
    la a1, _bss_end
    bge a0, a1, 2f
1:
    sw zero, 0(a0)
    addi a0, a0, 4
    blt a0, a1, 1b
2:

    # Call C entry point
    jal ra, _start

    # Should never return here, but if it does:
    j halt

halt:
    j halt

# Define global symbols for BSS section boundaries
.section .bss
.align 4
.globl _bss_start
_bss_start:

# Space for BSS will be allocated by the linker

.globl _bss_end
_bss_end:
