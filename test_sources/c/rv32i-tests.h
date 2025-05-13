// rv32i-tests.h - Common definitions for all tests
#ifndef RV32I_TESTS_H
#define RV32I_TESTS_H

// Memory-mapped I/O addresses (example)
#define UART_TX         0x10000000  // UART transmit register
#define TEST_RESULT     0x20000000  // Memory address to write test results
#define TEST_PASSED     0x1         // Value indicating test passed
#define TEST_FAILED     0x2         // Value indicating test failed

// Helper functions
static inline void write_reg(volatile unsigned int* addr, unsigned int val) {
    *addr = val;
}

static inline unsigned int read_reg(volatile unsigned int* addr) {
    return *addr;
}

// Simple function to report test status
static inline void report_result(int passed) {
    volatile unsigned int* result = (volatile unsigned int*)TEST_RESULT;
    *result = passed ? TEST_PASSED : TEST_FAILED;

    // Infinite loop to signal end of test
    while(1) { }
}

// Define entry point - this ensures proper linkage
#define ENTRY_POINT              \
    void _start(void) __attribute__((section(".text.init")));  \
    void _start(void)

#endif // RV32I_TESTS_H
