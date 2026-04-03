#include <stdio.h>

/*
 * Implements Caesar cipher encryption/decryption.
 * Then performs frequency analysis to crack an unknown shift.
 */

int main(void) {
    char plaintext[] = "The quick brown fox jumps over the lazy dog near the riverbank";
    int text_len = 0;
    while (plaintext[text_len] != '\0') text_len++;

    int shift = 13;
    char encrypted[256];
    char decrypted[256];

    /* Encrypt */
    int i;
    for (i = 0; i < text_len; i++) {
        char ch = plaintext[i];
        if (ch >= 'A' && ch <= 'Z') {
            int pos = ch - 'A';
            int shifted = (pos + shift) % 26;
            encrypted[i] = (char)('A' + shifted);
        } else if (ch >= 'a' && ch <= 'z') {
            int pos = ch - 'a';
            int shifted = (pos + shift) % 26;
            encrypted[i] = (char)('a' + shifted);
        } else {
            encrypted[i] = ch;
        }
    }
    encrypted[text_len] = '\0';

    /* Decrypt (shift by 26 - shift) */
    int reverse_shift = 26 - shift;
    for (i = 0; i < text_len; i++) {
        char ch = encrypted[i];
        if (ch >= 'A' && ch <= 'Z') {
            int pos = ch - 'A';
            int shifted = (pos + reverse_shift) % 26;
            decrypted[i] = (char)('A' + shifted);
        } else if (ch >= 'a' && ch <= 'z') {
            int pos = ch - 'a';
            int shifted = (pos + reverse_shift) % 26;
            decrypted[i] = (char)('a' + shifted);
        } else {
            decrypted[i] = ch;
        }
    }
    decrypted[text_len] = '\0';

    /* Verify round-trip */
    int match = 1;
    for (i = 0; i < text_len; i++) {
        if (plaintext[i] != decrypted[i]) {
            match = 0;
            break;
        }
    }

    printf("Plain:     %s\n", plaintext);
    printf("Encrypted: %s\n", encrypted);
    printf("Decrypted: %s\n", decrypted);
    printf("Round-trip: %s\n\n", match ? "OK" : "FAILED");

    /* Frequency analysis to crack unknown shift */
    /* English letter frequencies (percent, a-z) */
    double english_freq[26] = {
        8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015,
        6.094, 6.966, 0.153, 0.772, 4.025, 2.406, 6.749,
        7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758,
        0.978, 2.360, 0.150, 1.974, 0.074
    };

    /* Count frequencies in ciphertext */
    int freq[26];
    for (i = 0; i < 26; i++) freq[i] = 0;

    int letter_count = 0;
    for (i = 0; i < text_len; i++) {
        char ch = encrypted[i];
        if (ch >= 'a' && ch <= 'z') {
            freq[ch - 'a']++;
            letter_count++;
        } else if (ch >= 'A' && ch <= 'Z') {
            freq[ch - 'A']++;
            letter_count++;
        }
    }

    /* Try all 26 shifts, score by chi-squared against English */
    double best_score = 1e18;
    int best_shift = 0;
    double scores[26];

    int s;
    for (s = 0; s < 26; s++) {
        double chi_sq = 0.0;
        int c;
        for (c = 0; c < 26; c++) {
            int shifted_idx = (c + s) % 26;
            double observed = (double)freq[shifted_idx];
            double expected = english_freq[c] * (double)letter_count / 100.0;
            if (expected > 0.0) {
                double diff = observed - expected;
                chi_sq += (diff * diff) / expected;
            }
        }
        scores[s] = chi_sq;
        if (chi_sq < best_score) {
            best_score = chi_sq;
            best_shift = s;
        }
    }

    printf("Frequency analysis (top 5 candidates):\n");
    int rank;
    for (rank = 0; rank < 5; rank++) {
        double min_s = 1e18;
        int min_idx = 0;
        for (s = 0; s < 26; s++) {
            if (scores[s] < min_s) {
                min_s = scores[s];
                min_idx = s;
            }
        }
        printf("  shift=%2d  chi-sq=%8.2f %s\n",
               min_idx, min_s,
               min_idx == shift ? "<-- CORRECT" : "");
        scores[min_idx] = 1e18;  /* remove from future rounds */
    }

    return 0;
}
