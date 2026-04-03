#include <stdio.h>

/*
 * Computes GCD (Euclidean algorithm) and LCM for pairs of integers.
 * Tests against a batch of input pairs.
 */

int main(void) {
    int pairs_a[] = {48, 270, 17, 0, 1024, 13, 100, 56};
    int pairs_b[] = {18, 192, 13, 5, 768, 169, 75, 98};
    int num_pairs = 8;

    int i;
    for (i = 0; i < num_pairs; i++) {
        int a = pairs_a[i];
        int b = pairs_b[i];
        int orig_a = a;
        int orig_b = b;

        /* Euclidean algorithm */
        int temp;
        int x = a;
        int y = b;
        while (y != 0) {
            temp = y;
            y = x % y;
            x = temp;
        }
        int gcd = x;

        /* LCM = |a*b| / gcd, avoid overflow with division first */
        long long la = (long long)orig_a;
        long long lb = (long long)orig_b;
        long long lcm;
        if (gcd == 0) {
            lcm = 0;
        } else {
            lcm = (la / gcd) * lb;
            if (lcm < 0) lcm = -lcm;
        }

        int step_count = 0;
        int sa = orig_a;
        int sb = orig_b;
        while (sb != 0) {
            int sr = sa % sb;
            sa = sb;
            sb = sr;
            step_count++;
        }

        printf("gcd(%d, %d) = %d, lcm = %lld  [%d steps]\n",
               orig_a, orig_b, gcd, lcm, step_count);
    }

    /* Extended GCD for the first pair */
    int a = 48, b = 18;
    int old_r = a, r = b;
    int old_s = 1, s = 0;
    int old_t = 0, t = 1;
    int quotient;

    while (r != 0) {
        quotient = old_r / r;
        int tmp_r = r;    r = old_r - quotient * r;    old_r = tmp_r;
        int tmp_s = s;    s = old_s - quotient * s;    old_s = tmp_s;
        int tmp_t = t;    t = old_t - quotient * t;    old_t = tmp_t;
    }

    int gcd_ext = old_r;
    int coeff_a = old_s;
    int coeff_b = old_t;

    printf("\nExtended GCD: %d*%d + %d*%d = %d\n",
           coeff_a, a, coeff_b, b, gcd_ext);

    return 0;
}
