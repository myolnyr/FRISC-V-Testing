// test4_jumps.c - Jump instructions test
#include "rv32i-tests.h"

// Forward declarations
void function1(void);
void function2(int* val);
void function3(void);

ENTRY_POINT {
    int result = 0;
    int passed = 1;

    // Test JAL (jump and link) - call function1
    function1();

    // Test JALR (jump and link register) - call function2
    function2(&result);

    // Result should be 42 after function2
    if (result != 42) {
        passed = 0;
    }

    // Test complex control flow with multiple jumps
    result = 0;
    int i;
    for (i = 0; i < 10; i++) {
        if (i % 2 == 0) {
            result += i;
        } else {
            result += 2 * i;
        }
    }

    // Sum should be 0 + 2 + 2 + 6 + 4 + 10 + 6 + 14 + 8 + 18 = 70
    if (result != 70) {
        passed = 0;
    }

    report_result(passed);
}

// Function using JAL to call another function
void function1(void) {
    // This function just calls function3
    function3();
    return;
}

// Function that sets a value via a pointer
void function2(int* val) {
    *val = 42;
    return;
}

// Simple function to test JALR return
void function3(void) {
    // Do nothing
    return;
}
