#include <stdio.h>

/*
 * Converts integers between bases 2-36.
 * Includes:
 *   - Integer to string in arbitrary base
 *   - String in arbitrary base to integer
 *   - Cross-base conversion table
 *   - Binary/octal/hex representations with manual formatting
 */

#define MAX_DIGITS 64

int int_to_base(unsigned long long value, int base, char *out) {
    char digits[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    char temp[MAX_DIGITS];
    int len = 0;

    if (value == 0) {
        out[0] = '0';
        out[1] = '\0';
        return 1;
    }

    unsigned long long v = value;
    while (v > 0) {
        int remainder = (int)(v % (unsigned long long)base);
        temp[len] = digits[remainder];
        len++;
        v /= (unsigned long long)base;
    }

    /* Reverse into output */
    int i;
    for (i = 0; i < len; i++) {
        out[i] = temp[len - 1 - i];
    }
    out[len] = '\0';

    return len;
}

unsigned long long base_to_int(const char *str, int base, int *valid) {
    unsigned long long result = 0;
    *valid = 1;

    int i = 0;
    while (str[i] != '\0') {
        char ch = str[i];
        int digit;

        if (ch >= '0' && ch <= '9') {
            digit = ch - '0';
        } else if (ch >= 'A' && ch <= 'Z') {
            digit = ch - 'A' + 10;
        } else if (ch >= 'a' && ch <= 'z') {
            digit = ch - 'a' + 10;
        } else {
            *valid = 0;
            return 0;
        }

        if (digit >= base) {
            *valid = 0;
            return 0;
        }

        unsigned long long prev = result;
        result = result * (unsigned long long)base + (unsigned long long)digit;

        /* Overflow check */
        if (result < prev) {
            *valid = 0;
            return 0;
        }

        i++;
    }

    return result;
}

int main(void) {
    /* Test values */
    unsigned long long values[] = {0, 1, 10, 42, 255, 1000, 65535, 1000000, 4294967295ULL};
    int num_values = 9;
    int bases[] = {2, 8, 10, 16, 36};
    int num_bases = 5;

    char buffer[MAX_DIGITS];
    int i, j;

    /* Conversion table */
    printf("%-12s", "Decimal");
    for (j = 0; j < num_bases; j++) {
        char header[16];
        int hlen = 0;
        header[hlen++] = 'B';
        header[hlen++] = 'a';
        header[hlen++] = 's';
        header[hlen++] = 'e';
        header[hlen++] = '-';
        if (bases[j] >= 10) {
            header[hlen++] = '0' + bases[j] / 10;
        }
        header[hlen++] = '0' + bases[j] % 10;
        header[hlen] = '\0';
        printf("%-16s", header);
    }
    printf("\n");

    for (i = 0; i < 80; i++) printf("-");
    printf("\n");

    for (i = 0; i < num_values; i++) {
        printf("%-12llu", values[i]);
        for (j = 0; j < num_bases; j++) {
            int len = int_to_base(values[i], bases[j], buffer);
            printf("%-16s", buffer);
            (void)len;
        }
        printf("\n");
    }

    /* Round-trip verification */
    printf("\nRound-trip verification:\n");
    int errors = 0;
    int tests = 0;
    for (i = 0; i < num_values; i++) {
        for (j = 0; j < num_bases; j++) {
            int_to_base(values[i], bases[j], buffer);
            int valid;
            unsigned long long recovered = base_to_int(buffer, bases[j], &valid);
            tests++;
            if (!valid || recovered != values[i]) {
                printf("  FAIL: %llu base %d -> '%s' -> %llu\n",
                       values[i], bases[j], buffer, recovered);
                errors++;
            }
        }
    }
    printf("  %d/%d tests passed\n", tests - errors, tests);

    /* Bit pattern analysis for powers of 2 */
    printf("\nPowers of 2 in binary:\n");
    unsigned long long power = 1;
    int p;
    for (p = 0; p < 20; p++) {
        int len = int_to_base(power, 2, buffer);
        int bit_count = 0;
        int k;
        for (k = 0; k < len; k++) {
            if (buffer[k] == '1') bit_count++;
        }
        printf("  2^%-2d = %-10llu = %-25s (%d bits set, %d digits)\n",
               p, power, buffer, bit_count, len);
        power *= 2;
    }

    return 0;
}
