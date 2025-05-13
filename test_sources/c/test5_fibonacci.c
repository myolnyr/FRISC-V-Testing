// test5_fibonacci.c - Fibonacci sequence calculation
#include "rv32i-tests.h"

// Calculate the nth Fibonacci number
unsigned int fibonacci(unsigned int n) {
    if (n <= 1) {
        return n;
    }

    unsigned int prev = 0;
    unsigned int curr = 1;
    unsigned int next;

    for (unsigned int i = 2; i <= n; i++) {
        next = prev + curr;
        prev = curr;
        curr = next;
    }

    return curr;
}

ENTRY_POINT {
    int passed = 1;

    // Test known Fibonacci values
    unsigned int expected_values[] = {0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144};

    for (unsigned int i = 0; i <= 12; i++) {
        if (fibonacci(i) != expected_values[i]) {
            passed = 0;
            break;
        }
    }

    report_result(passed);
}
