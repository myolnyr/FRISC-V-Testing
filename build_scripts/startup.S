// startup.S - Assembly startup code for RV32I bare-metal
.section .text.init
.globl _start_asm
.globl _bss_start
.globl _bss_end
.globl _data_start
.globl _data_end
.globl _erodata
.globl _start

_start_asm:
    # Initialize stack pointer
    la sp, _stack_top

    # Copy initialized data from ROM to RAM
    la a0, _erodata      # Source (in ROM)
    la a1, _data_start   # Destination (in RAM)
    la a2, _data_end     # End of data section
    bgeu a1, a2, 2f      # Skip if no data to copy
1:
    lw t0, 0(a0)         # Load from ROM
    sw t0, 0(a1)         # Store to RAM
    addi a0, a0, 4
    addi a1, a1, 4
    bltu a1, a2, 1b
2:

    # Clear BSS section
    la a0, _bss_start
    la a1, _bss_end
    bgeu a0, a1, 4f
3:
    sw zero, 0(a0)
    addi a0, a0, 4
    bltu a0, a1, 3b
4:

    # Call C entry point
    jal ra, _start

    # Should never return here, but if it does:
    j halt

halt:
    j halt
