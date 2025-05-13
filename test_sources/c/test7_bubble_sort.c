// test7_bubble_sort.c - Bubble sort implementation test
#include "rv32i-tests.h"

// Bubble sort implementation
void bubble_sort(int arr[], int n) {
    int i, j, temp;
    for (i = 0; i < n - 1; i++) {
        for (j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                // Swap
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

// Check if array is sorted
int is_sorted(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        if (arr[i] > arr[i + 1]) {
            return 0;
        }
    }
    return 1;
}

ENTRY_POINT {
    int passed = 1;

    // Test case 1: Already sorted array
    int arr1[] = {1, 2, 3, 4, 5};
    bubble_sort(arr1, 5);
    if (!is_sorted(arr1, 5)) {
        passed = 0;
    }

    // Test case 2: Reverse sorted array
    int arr2[] = {5, 4, 3, 2, 1};
    bubble_sort(arr2, 5);
    if (!is_sorted(arr2, 5) || arr2[0] != 1 || arr2[4] != 5) {
        passed = 0;
    }

    // Test case 3: Random array
    int arr3[] = {3, 1, 4, 1, 5, 9, 2, 6, 5};
    bubble_sort(arr3, 9);
    if (!is_sorted(arr3, 9) || arr3[0] != 1 || arr3[8] != 9) {
        passed = 0;
    }

    // Test case 4: Array with duplicates
    int arr4[] = {3, 3, 1, 4, 1};
    bubble_sort(arr4, 5);
    if (!is_sorted(arr4, 5) || arr4[0] != 1 || arr4[4] != 4) {
        passed = 0;
    }

    report_result(passed);
}
