#include <stdio.h>

/*
 * Implements binary search and interpolation search on a sorted array.
 * Compares step counts for various targets including edge cases.
 */

#define SIZE 1000

int main(void) {
    int arr[SIZE];
    int i;

    /* Build a sorted array with some gaps */
    int val = 0;
    unsigned int rng = 42u;
    for (i = 0; i < SIZE; i++) {
        rng = rng * 2654435761u + 1;
        int gap = 1 + (int)((rng >> 16) % 5);
        val += gap;
        arr[i] = val;
    }

    int first_elem = arr[0];
    int last_elem = arr[SIZE - 1];

    /* Targets: some present, some missing, plus boundary cases */
    int targets[] = {
        arr[0], arr[SIZE - 1], arr[SIZE / 2], arr[1], arr[SIZE - 2],
        arr[250], arr[750], arr[499], arr[500],
        -1,              /* before range */
        last_elem + 100, /* after range */
        arr[333] + 1,    /* between elements */
        arr[100] - 1     /* between elements */
    };
    int num_targets = 13;

    printf("Array: %d elements, range [%d, %d]\n\n", SIZE, first_elem, last_elem);
    printf("%-10s  %-8s %-6s  %-8s %-6s\n",
           "Target", "Binary", "Steps", "Interp", "Steps");
    printf("---------------------------------------------------\n");

    int t;
    for (t = 0; t < num_targets; t++) {
        int target = targets[t];

        /* Binary search */
        int lo = 0;
        int hi = SIZE - 1;
        int bin_steps = 0;
        int bin_found = -1;
        while (lo <= hi) {
            bin_steps++;
            int mid = lo + (hi - lo) / 2;
            if (arr[mid] == target) {
                bin_found = mid;
                break;
            } else if (arr[mid] < target) {
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        /* Interpolation search */
        lo = 0;
        hi = SIZE - 1;
        int interp_steps = 0;
        int interp_found = -1;
        while (lo <= hi && target >= arr[lo] && target <= arr[hi]) {
            interp_steps++;

            if (lo == hi) {
                if (arr[lo] == target) interp_found = lo;
                break;
            }

            long long range = (long long)(arr[hi] - arr[lo]);
            long long offset = (long long)(target - arr[lo]);
            long long span = (long long)(hi - lo);
            int pos = lo + (int)((offset * span) / range);

            if (pos < lo) pos = lo;
            if (pos > hi) pos = hi;

            if (arr[pos] == target) {
                interp_found = pos;
                break;
            } else if (arr[pos] < target) {
                lo = pos + 1;
            } else {
                hi = pos - 1;
            }
        }

        char bin_str[16];
        char interp_str[16];

        if (bin_found >= 0) {
            int n = 0;
            int v = bin_found;
            char tmp[16];
            if (v == 0) { bin_str[0] = '0'; bin_str[1] = '\0'; }
            else {
                while (v > 0) { tmp[n++] = '0' + v % 10; v /= 10; }
                int j; for (j = 0; j < n; j++) bin_str[j] = tmp[n-1-j];
                bin_str[n] = '\0';
            }
        } else {
            bin_str[0] = '-'; bin_str[1] = '\0';
        }

        if (interp_found >= 0) {
            int n = 0;
            int v = interp_found;
            char tmp[16];
            if (v == 0) { interp_str[0] = '0'; interp_str[1] = '\0'; }
            else {
                while (v > 0) { tmp[n++] = '0' + v % 10; v /= 10; }
                int j; for (j = 0; j < n; j++) interp_str[j] = tmp[n-1-j];
                interp_str[n] = '\0';
            }
        } else {
            interp_str[0] = '-'; interp_str[1] = '\0';
        }

        printf("%-10d  idx=%-4s %3d     idx=%-4s %3d\n",
               target, bin_str, bin_steps, interp_str, interp_steps);
    }

    /* Summary statistics */
    int total_bin = 0, total_interp = 0;
    int max_bin = 0, max_interp = 0;
    /* Re-run just for counting */
    for (t = 0; t < num_targets; t++) {
        int target = targets[t];
        int lo = 0, hi = SIZE - 1, steps = 0;
        while (lo <= hi) {
            steps++;
            int mid = lo + (hi - lo) / 2;
            if (arr[mid] == target) break;
            else if (arr[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        total_bin += steps;
        if (steps > max_bin) max_bin = steps;

        lo = 0; hi = SIZE - 1; steps = 0;
        while (lo <= hi && target >= arr[lo] && target <= arr[hi]) {
            steps++;
            if (lo == hi) break;
            long long range = (long long)(arr[hi] - arr[lo]);
            long long offset = (long long)(target - arr[lo]);
            int pos = lo + (int)((offset * (hi - lo)) / range);
            if (pos < lo) pos = lo;
            if (pos > hi) pos = hi;
            if (arr[pos] == target) break;
            else if (arr[pos] < target) lo = pos + 1;
            else hi = pos - 1;
        }
        total_interp += steps;
        if (steps > max_interp) max_interp = steps;
    }

    double avg_bin = (double)total_bin / (double)num_targets;
    double avg_interp = (double)total_interp / (double)num_targets;

    printf("\nAvg steps:  binary=%.1f  interp=%.1f\n", avg_bin, avg_interp);
    printf("Max steps:  binary=%d    interp=%d\n", max_bin, max_interp);

    return 0;
}
