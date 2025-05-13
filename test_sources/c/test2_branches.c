// test2_branches.c - Branch instructions test
#include "rv32i-tests.h"

ENTRY_POINT {
    int a = 10;
    int b = 5;
    int c = 10;
    int result = 0;
    int passed = 1;

    // Test branch equal - should branch
    if (a == c) {
        result += 1;
    }

    // Test branch not equal - should branch
    if (a != b) {
        result += 2;
    }

    // Test branch less than - should branch
    if (b < a) {
        result += 4;
    }

    // Test branch greater or equal - should branch
    if (a >= b) {
        result += 8;
    }

    // Test branch less than unsigned - should branch
    if ((unsigned int)b < (unsigned int)a) {
        result += 16;
    }

    // Test branch greater or equal unsigned - should branch
    if ((unsigned int)a >= (unsigned int)b) {
        result += 32;
    }

    // All branches should have been taken, result should be 63
    if (result != 63) {
        passed = 0;
    }

    // Negative test: branch equal - should not branch
    result = 100;
    if (a == b) {
        result = 200;
    }

    // Should still be 100
    if (result != 100) {
        passed = 0;
    }

    report_result(passed);
}
