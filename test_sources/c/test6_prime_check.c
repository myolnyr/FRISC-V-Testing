// test6_prime_check.c - Prime number checking test
#include "rv32i-tests.h"

// Function to check if a number is prime
int is_prime(unsigned int n) {
    // Handle edge cases
    if (n <= 1) return 0;  // 0 and 1 are not prime
    if (n <= 3) return 1;  // 2 and 3 are prime
    if (n % 2 == 0 || n % 3 == 0) return 0;  // Check divisibility by 2 and 3

    // Check all numbers of form 6k±1 up to sqrt(n)
    for (unsigned int i = 5; i * i <= n; i += 6) {
        if (n % i == 0 || n % (i + 2) == 0) {
            return 0;
        }
    }

    return 1;  // If we reach here, n is prime
}

ENTRY_POINT {
    int passed = 1;

    // Known prime numbers under 100
    unsigned int primes[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41,
                             43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97};

    // Check all numbers from 1 to 100
    for (unsigned int i = 1; i <= 100; i++) {
        int should_be_prime = 0;

        // Check if i is in our list of primes
        for (unsigned int j = 0; j < sizeof(primes)/sizeof(primes[0]); j++) {
            if (primes[j] == i) {
                should_be_prime = 1;
                break;
            }
        }

        // Test if our is_prime function agrees
        if (is_prime(i) != should_be_prime) {
            passed = 0;
            break;
        }
    }

    report_result(passed);
}
