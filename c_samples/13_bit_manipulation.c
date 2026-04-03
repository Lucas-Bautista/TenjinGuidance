#include <stdio.h>

/*
 * Bit manipulation algorithms using only primitive types:
 *   - Population count (Hamming weight)
 *   - Bit reversal
 *   - Counting leading/trailing zeros
 *   - Power-of-two checks
 *   - Next power of two
 *   - Bit rotation
 *   - Parity
 *   - Isolating lowest/highest set bit
 */

int main(void) {
    unsigned int test_values[] = {
        0u, 1u, 2u, 7u, 15u, 16u, 255u, 256u,
        1023u, 1024u, 65535u, 0xDEADBEEFu, 0xFFFFFFFFu, 0x80000000u
    };
    int num_values = 14;

    int i;
    printf("=== Bit Properties ===\n");
    printf("%-12s %-34s %-5s %-5s %-5s %-5s %-5s\n",
           "Value", "Binary (low 16)", "Pop", "LZ", "TZ", "Pow2", "Par");

    for (i = 0; i < num_values; i++) {
        unsigned int v = test_values[i];

        /* Population count (Brian Kernighan's algorithm) */
        unsigned int pc_tmp = v;
        int popcount = 0;
        while (pc_tmp) {
            pc_tmp &= (pc_tmp - 1);
            popcount++;
        }

        /* Leading zeros (32-bit) */
        int leading_zeros = 0;
        if (v == 0) {
            leading_zeros = 32;
        } else {
            unsigned int lz_tmp = v;
            while (!(lz_tmp & 0x80000000u)) {
                leading_zeros++;
                lz_tmp <<= 1;
            }
        }

        /* Trailing zeros */
        int trailing_zeros = 0;
        if (v == 0) {
            trailing_zeros = 32;
        } else {
            unsigned int tz_tmp = v;
            while (!(tz_tmp & 1u)) {
                trailing_zeros++;
                tz_tmp >>= 1;
            }
        }

        /* Power of two check */
        int is_pow2 = (v != 0 && (v & (v - 1)) == 0) ? 1 : 0;

        /* Parity (1 if odd number of bits set) */
        unsigned int par_tmp = v;
        par_tmp ^= par_tmp >> 16;
        par_tmp ^= par_tmp >> 8;
        par_tmp ^= par_tmp >> 4;
        par_tmp ^= par_tmp >> 2;
        par_tmp ^= par_tmp >> 1;
        int parity = (int)(par_tmp & 1u);

        /* Print binary (low 16 bits) */
        char bin[33];
        int b;
        for (b = 0; b < 32; b++) {
            bin[31 - b] = (v & (1u << b)) ? '1' : '0';
        }
        bin[32] = '\0';

        printf("0x%08X   %s  %-5d %-5d %-5d %-5d %-5d\n",
               v, bin + 16, popcount, leading_zeros, trailing_zeros,
               is_pow2, parity);
    }

    /* Bit reversal */
    printf("\n=== Bit Reversal (32-bit) ===\n");
    unsigned int rev_tests[] = {1u, 0x80000000u, 0xFF00FF00u, 0xAAAAAAAAu, 0x12345678u};
    int num_rev = 5;

    int r;
    for (r = 0; r < num_rev; r++) {
        unsigned int v = rev_tests[r];
        unsigned int reversed = v;

        /* Swap adjacent bits */
        reversed = ((reversed & 0x55555555u) << 1) | ((reversed & 0xAAAAAAAAu) >> 1);
        /* Swap pairs */
        reversed = ((reversed & 0x33333333u) << 2) | ((reversed & 0xCCCCCCCCu) >> 2);
        /* Swap nibbles */
        reversed = ((reversed & 0x0F0F0F0Fu) << 4) | ((reversed & 0xF0F0F0F0u) >> 4);
        /* Swap bytes */
        reversed = ((reversed & 0x00FF00FFu) << 8) | ((reversed & 0xFF00FF00u) >> 8);
        /* Swap halfwords */
        reversed = (reversed << 16) | (reversed >> 16);

        printf("  0x%08X -> 0x%08X\n", v, reversed);
    }

    /* Next power of two */
    printf("\n=== Next Power of Two ===\n");
    unsigned int np2_tests[] = {0u, 1u, 2u, 3u, 5u, 100u, 1000u, 1023u, 1024u, 65000u};
    int num_np2 = 10;

    int p;
    for (p = 0; p < num_np2; p++) {
        unsigned int v = np2_tests[p];
        unsigned int next;

        if (v == 0) {
            next = 1;
        } else {
            next = v - 1;
            next |= next >> 1;
            next |= next >> 2;
            next |= next >> 4;
            next |= next >> 8;
            next |= next >> 16;
            next++;
        }

        printf("  %-8u -> %-8u\n", v, next);
    }

    /* Bit rotation */
    printf("\n=== Bit Rotation (32-bit) ===\n");
    unsigned int rot_val = 0xDEADBEEFu;
    int rotations[] = {0, 1, 4, 8, 12, 16, 31};
    int num_rots = 7;

    int rot;
    for (rot = 0; rot < num_rots; rot++) {
        int n = rotations[rot];
        unsigned int left_rot = (rot_val << n) | (rot_val >> (32 - n));
        unsigned int right_rot = (rot_val >> n) | (rot_val << (32 - n));
        printf("  ROL(%d): 0x%08X  ROR(%d): 0x%08X\n",
               n, left_rot, n, right_rot);
    }

    /* Isolating bits */
    printf("\n=== Bit Isolation ===\n");
    unsigned int iso_val = 0x00A0C050u;
    unsigned int lowest_set = iso_val & (~iso_val + 1);
    unsigned int clear_lowest = iso_val & (iso_val - 1);

    unsigned int highest_set = iso_val;
    highest_set |= highest_set >> 1;
    highest_set |= highest_set >> 2;
    highest_set |= highest_set >> 4;
    highest_set |= highest_set >> 8;
    highest_set |= highest_set >> 16;
    highest_set = (highest_set + 1) >> 1;

    printf("  Value:        0x%08X\n", iso_val);
    printf("  Lowest set:   0x%08X\n", lowest_set);
    printf("  Clear lowest: 0x%08X\n", clear_lowest);
    printf("  Highest set:  0x%08X\n", highest_set);

    return 0;
}
