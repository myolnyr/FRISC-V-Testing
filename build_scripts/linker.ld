/* linker.ld - Linker script for bare-metal RV32I tests */
OUTPUT_ARCH(riscv)
ENTRY(_start)

SECTIONS
{
  . = 0x00000000;

  .text : {
    *(.text.init)
    *(.text)
    *(.text.*)
    . = ALIGN(4);
  }

  .rodata : {
    *(.rodata)
    *(.rodata.*)
    . = ALIGN(4);
  }

  .data : {
    *(.data)
    *(.data.*)
    . = ALIGN(4);
  }

  .bss : {
    *(.bss)
    *(.bss.*)
    *(COMMON)
    . = ALIGN(4);
  }

  .stack (NOLOAD) : {
    . = 0x000003FC;
    _stack_top = .;
  }
}
