#include <stdio.h>

/*
 * Implements and compares three sorting algorithms on the same data:
 *   - Bubble sort
 *   - Insertion sort
 *   - Selection sort
 * Tracks comparison and swap counts for each.
 */

#define N 50

int main(void) {
    int original[N];
    int arr_bubble[N];
    int arr_insert[N];
    int arr_select[N];

    /* Generate pseudo-random data using LCG */
    unsigned int seed = 12345u;
    int i;
    for (i = 0; i < N; i++) {
        seed = seed * 1103515245u + 12345u;
        original[i] = (int)((seed >> 16) % 1000);
    }

    /* Copy to each working array */
    for (i = 0; i < N; i++) {
        arr_bubble[i] = original[i];
        arr_insert[i] = original[i];
        arr_select[i] = original[i];
    }

    /* ---- Bubble Sort ---- */
    long bubble_comps = 0;
    long bubble_swaps = 0;
    int sorted = 0;
    while (!sorted) {
        sorted = 1;
        int j;
        for (j = 0; j < N - 1; j++) {
            bubble_comps++;
            if (arr_bubble[j] > arr_bubble[j + 1]) {
                int tmp = arr_bubble[j];
                arr_bubble[j] = arr_bubble[j + 1];
                arr_bubble[j + 1] = tmp;
                bubble_swaps++;
                sorted = 0;
            }
        }
    }

    /* ---- Insertion Sort ---- */
    long insert_comps = 0;
    long insert_shifts = 0;
    int k;
    for (k = 1; k < N; k++) {
        int key = arr_insert[k];
        int j = k - 1;
        while (j >= 0) {
            insert_comps++;
            if (arr_insert[j] > key) {
                arr_insert[j + 1] = arr_insert[j];
                insert_shifts++;
                j--;
            } else {
                break;
            }
        }
        arr_insert[j + 1] = key;
    }

    /* ---- Selection Sort ---- */
    long select_comps = 0;
    long select_swaps = 0;
    for (i = 0; i < N - 1; i++) {
        int min_idx = i;
        int min_val = arr_select[i];
        int j;
        for (j = i + 1; j < N; j++) {
            select_comps++;
            if (arr_select[j] < min_val) {
                min_idx = j;
                min_val = arr_select[j];
            }
        }
        if (min_idx != i) {
            int tmp = arr_select[i];
            arr_select[i] = arr_select[min_idx];
            arr_select[min_idx] = tmp;
            select_swaps++;
        }
    }

    /* Verify all three produced the same result */
    int all_match = 1;
    int is_sorted = 1;
    for (i = 0; i < N; i++) {
        if (arr_bubble[i] != arr_insert[i] || arr_insert[i] != arr_select[i]) {
            all_match = 0;
        }
        if (i > 0 && arr_bubble[i] < arr_bubble[i - 1]) {
            is_sorted = 0;
        }
    }

    int final_min = arr_bubble[0];
    int final_max = arr_bubble[N - 1];
    int median = arr_bubble[N / 2];

    printf("Array size: %d\n", N);
    printf("Range: [%d, %d], Median: %d\n", final_min, final_max, median);
    printf("All match: %s, Sorted: %s\n\n",
           all_match ? "yes" : "NO", is_sorted ? "yes" : "NO");

    printf("Algorithm        Comparisons    Swaps/Shifts\n");
    printf("-----------------------------------------------\n");
    printf("Bubble sort      %8ld       %8ld\n", bubble_comps, bubble_swaps);
    printf("Insertion sort   %8ld       %8ld\n", insert_comps, insert_shifts);
    printf("Selection sort   %8ld       %8ld\n", select_comps, select_swaps);

    double bubble_ratio = (double)bubble_comps / (double)(N * N);
    double insert_ratio = (double)insert_comps / (double)(N * N);
    double select_ratio = (double)select_comps / (double)(N * N);

    printf("\nComparisons / N^2:\n");
    printf("  Bubble:    %.4f\n", bubble_ratio);
    printf("  Insertion: %.4f\n", insert_ratio);
    printf("  Selection: %.4f\n", select_ratio);

    return 0;
}
