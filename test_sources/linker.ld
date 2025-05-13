// linker.ld - Linker script for bare-metal RV32I tests
OUTPUT_ARCH( "riscv" )
ENTRY( _start )

SECTIONS
{
  /* Code begins at address 0 */
  . = 0x00000000;

  .text : {
    *(.text.init)     /* Startup code first */
    *(.text)          /* Then other code */
    *(.text.*)
    . = ALIGN(4);
  }

  /* Read-only data section */
  .rodata : {
    *(.rodata)
    *(.rodata.*)
    . = ALIGN(4);
  }

  /* Initialized data section */
  .data : {
    *(.data)
    *(.data.*)
    . = ALIGN(4);
  }

  /* Zero-initialized data section */
  .bss : {
    *(.bss)
    *(.bss.*)
    *(COMMON)
    . = ALIGN(4);
  }

  /* Stack section - place at end of RAM */
  . = 0x80001000;  /* Example: 4KB of RAM starting at 0x80000000 */

  _stack_top = .;  /* Stack grows downward from here */
}
