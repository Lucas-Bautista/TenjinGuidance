#include <stdio.h>

/*
 * Sieve of Eratosthenes to find all primes up to a limit.
 * Then computes:
 *   - Count of primes found
 *   - Sum of all primes
 *   - Twin prime pairs
 *   - Largest prime gap in the range
 */

#define LIMIT 10000

int main(void) {
    char is_composite[LIMIT + 1];
    int i, j;

    /* Initialize sieve */
    for (i = 0; i <= LIMIT; i++) {
        is_composite[i] = 0;
    }
    is_composite[0] = 1;
    is_composite[1] = 1;

    /* Run sieve */
    int sqrt_limit = 1;
    while ((sqrt_limit + 1) * (sqrt_limit + 1) <= LIMIT) {
        sqrt_limit++;
    }

    int composites_marked = 0;
    for (i = 2; i <= sqrt_limit; i++) {
        if (!is_composite[i]) {
            for (j = i * i; j <= LIMIT; j += i) {
                if (!is_composite[j]) {
                    is_composite[j] = 1;
                    composites_marked++;
                }
            }
        }
    }

    /* Collect results */
    int prime_count = 0;
    long long prime_sum = 0;
    int largest_prime = 0;
    int smallest_prime = 0;

    int twin_count = 0;
    int prev_prime = 0;
    int max_gap = 0;
    int max_gap_start = 0;
    int max_gap_end = 0;

    for (i = 2; i <= LIMIT; i++) {
        if (!is_composite[i]) {
            prime_count++;
            prime_sum += i;
            largest_prime = i;
            if (smallest_prime == 0) smallest_prime = i;

            if (prev_prime > 0) {
                int gap = i - prev_prime;
                if (gap > max_gap) {
                    max_gap = gap;
                    max_gap_start = prev_prime;
                    max_gap_end = i;
                }
                if (gap == 2) {
                    twin_count++;
                }
            }
            prev_prime = i;
        }
    }

    double avg_prime = (double)prime_sum / (double)prime_count;
    double density = (double)prime_count / (double)LIMIT;

    /* Goldbach check for even numbers 4..100 */
    int goldbach_verified = 0;
    int goldbach_failed = 0;
    int n;
    for (n = 4; n <= 100; n += 2) {
        int found = 0;
        int ga = 0, gb = 0;
        for (j = 2; j <= n / 2; j++) {
            if (!is_composite[j] && !is_composite[n - j]) {
                found = 1;
                ga = j;
                gb = n - j;
                break;
            }
        }
        if (found) {
            goldbach_verified++;
        } else {
            goldbach_failed++;
        }
    }

    printf("Primes up to %d:\n", LIMIT);
    printf("  Count:    %d\n", prime_count);
    printf("  Sum:      %lld\n", prime_sum);
    printf("  Smallest: %d\n", smallest_prime);
    printf("  Largest:  %d\n", largest_prime);
    printf("  Average:  %.2f\n", avg_prime);
    printf("  Density:  %.4f\n", density);
    printf("  Twin pairs:   %d\n", twin_count);
    printf("  Largest gap:  %d (between %d and %d)\n",
           max_gap, max_gap_start, max_gap_end);
    printf("  Composites marked: %d\n", composites_marked);
    printf("  Goldbach verified: %d/%d even numbers\n",
           goldbach_verified, goldbach_verified + goldbach_failed);

    return 0;
}
