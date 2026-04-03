#include <stdio.h>

/*
 * Computes Fibonacci numbers three ways:
 *   1. Iterative
 *   2. Closed-form (Binet's formula approximation)
 *   3. Matrix exponentiation (2x2 matrix, fast doubling)
 * Compares results and tracks when overflow occurs.
 */

int main(void) {
    int n_max = 45;

    /* Method 1: Iterative */
    long long fib_prev = 0;
    long long fib_curr = 1;
    long long fib_table[46];
    fib_table[0] = 0;
    fib_table[1] = 1;

    int i;
    for (i = 2; i <= n_max; i++) {
        long long fib_next = fib_prev + fib_curr;
        fib_table[i] = fib_next;
        fib_prev = fib_curr;
        fib_curr = fib_next;
    }

    /* Method 2: Binet approximation (loses precision for large n) */
    double phi = 1.6180339887498948;
    double psi = -0.6180339887498948;
    double binet_results[46];

    for (i = 0; i <= n_max; i++) {
        double phi_n = 1.0;
        double psi_n = 1.0;
        int j;
        for (j = 0; j < i; j++) {
            phi_n *= phi;
            psi_n *= psi;
        }
        binet_results[i] = (phi_n - psi_n) / 2.2360679774997896;
    }

    /* Method 3: Fast doubling
     * F(2k)   = F(k) * [2*F(k+1) - F(k)]
     * F(2k+1) = F(k)^2 + F(k+1)^2
     */
    int test_values[] = {0, 1, 5, 10, 20, 30, 40, 45};
    int num_tests = 8;

    for (i = 0; i < num_tests; i++) {
        int n = test_values[i];
        long long a = 0;  /* F(0) */
        long long b = 1;  /* F(1) */

        /* Find highest bit */
        int bit;
        int highest = 0;
        int temp_n = n;
        while (temp_n > 0) {
            highest++;
            temp_n >>= 1;
        }

        int k;
        for (k = highest - 1; k >= 0; k--) {
            long long c = a * (2 * b - a);
            long long d = a * a + b * b;
            a = c;
            b = d;

            if ((n >> k) & 1) {
                long long next = a + b;
                a = b;
                b = next;
            }
        }

        long long fast_result = a;
        long long iter_result = fib_table[n];
        long long binet_rounded = (long long)(binet_results[n] + 0.5);

        int binet_match = (binet_rounded == iter_result) ? 1 : 0;
        int fast_match = (fast_result == iter_result) ? 1 : 0;

        printf("F(%2d) = %15lld  fast=%s  binet=%s\n",
               n, iter_result,
               fast_match ? "ok" : "MISMATCH",
               binet_match ? "ok" : "DRIFT");
    }

    /* Compute ratio convergence to golden ratio */
    double ratio;
    double error;
    printf("\nGolden ratio convergence:\n");
    for (i = 2; i <= 20; i++) {
        ratio = (double)fib_table[i] / (double)fib_table[i - 1];
        error = ratio - phi;
        if (error < 0) error = -error;
        printf("  F(%d)/F(%d) = %.15f  error=%.2e\n",
               i, i - 1, ratio, error);
    }

    return 0;
}
