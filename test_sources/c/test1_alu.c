// test1_alu.c - Basic ALU operations test
#include "rv32i-tests.h"

ENTRY_POINT {
    int a = 10;
    int b = 5;
    int result = 0;
    int expected = 0;
    int passed = 1;

    // Test addition
    result = a + b;
    expected = 15;
    if (result != expected) {
        passed = 0;
    }

    // Test subtraction
    result = a - b;
    expected = 5;
    if (result != expected) {
        passed = 0;
    }

    // Test bitwise AND
    result = a & b;
    expected = 0;  // 1010 & 0101 = 0000
    if (result != expected) {
        passed = 0;
    }

    // Test bitwise OR
    result = a | b;
    expected = 15; // 1010 | 0101 = 1111
    if (result != expected) {
        passed = 0;
    }

    // Test bitwise XOR
    result = a ^ b;
    expected = 15; // 1010 ^ 0101 = 1111
    if (result != expected) {
        passed = 0;
    }

    // Test logical shift left
    result = a << 1;
    expected = 20; // 1010 << 1 = 10100 (20)
    if (result != expected) {
        passed = 0;
    }

    // Test logical shift right
    result = a >> 1;
    expected = 5;  // 1010 >> 1 = 0101 (5)
    if (result != expected) {
        passed = 0;
    }

    // Report final result
    report_result(passed);
}
