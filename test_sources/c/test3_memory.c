// test3_memory.c - Memory operations test
#include "rv32i-tests.h"

ENTRY_POINT {
    volatile int *mem = (volatile int *)0x80000000; // Example base memory address
    int passed = 1;

    // Test word store/load
    mem[0] = 0xDEADBEEF;
    if (mem[0] != 0xDEADBEEF) {
        passed = 0;
    }

    // Test half-word store/load
    volatile unsigned short *mem_h = (volatile unsigned short *)mem;
    mem_h[4] = 0xABCD;
    if (mem_h[4] != 0xABCD) {
        passed = 0;
    }

    // Test signed half-word load
    volatile short *mem_sh = (volatile short *)mem;
    mem_sh[6] = -5;
    if (mem_sh[6] != -5) {
        passed = 0;
    }

    // Test byte store/load
    volatile unsigned char *mem_b = (volatile unsigned char *)mem;
    mem_b[16] = 0x42;
    if (mem_b[16] != 0x42) {
        passed = 0;
    }

    // Test signed byte load
    volatile signed char *mem_sb = (volatile signed char *)mem;
    mem_sb[20] = -10;
    if (mem_sb[20] != -10) {
        passed = 0;
    }

    report_result(passed);
}
