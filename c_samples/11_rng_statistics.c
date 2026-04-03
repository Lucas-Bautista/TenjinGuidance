#include <stdio.h>

/*
 * Implements a linear congruential generator (LCG) and runs basic
 * statistical quality tests:
 *   - Mean / variance
 *   - Chi-squared uniformity test (bucket test)
 *   - Runs test (count runs up/down)
 *   - Serial correlation
 */

#define NUM_SAMPLES 10000
#define NUM_BUCKETS 20

int main(void) {
    /* LCG parameters (glibc style) */
    unsigned long long a = 1103515245ULL;
    unsigned long long c = 12345ULL;
    unsigned long long m = 2147483648ULL;  /* 2^31 */
    unsigned long long state = 42ULL;      /* seed */

    /* Generate samples as doubles in [0, 1) */
    double samples[NUM_SAMPLES];
    unsigned int raw_values[NUM_SAMPLES];

    int i;
    for (i = 0; i < NUM_SAMPLES; i++) {
        state = (a * state + c) % m;
        raw_values[i] = (unsigned int)state;
        samples[i] = (double)state / (double)m;
    }

    /* ---- Mean and Variance ---- */
    double sum = 0.0;
    for (i = 0; i < NUM_SAMPLES; i++) {
        sum += samples[i];
    }
    double mean = sum / (double)NUM_SAMPLES;

    double var_sum = 0.0;
    for (i = 0; i < NUM_SAMPLES; i++) {
        double diff = samples[i] - mean;
        var_sum += diff * diff;
    }
    double variance = var_sum / (double)(NUM_SAMPLES - 1);

    /* Expected: mean=0.5, variance=1/12=0.08333 */
    double expected_mean = 0.5;
    double expected_var = 1.0 / 12.0;
    double mean_error = mean - expected_mean;
    double var_error = variance - expected_var;
    if (mean_error < 0.0) mean_error = -mean_error;
    if (var_error < 0.0) var_error = -var_error;

    /* ---- Chi-squared bucket test ---- */
    int buckets[NUM_BUCKETS];
    for (i = 0; i < NUM_BUCKETS; i++) buckets[i] = 0;

    for (i = 0; i < NUM_SAMPLES; i++) {
        int b = (int)(samples[i] * NUM_BUCKETS);
        if (b >= NUM_BUCKETS) b = NUM_BUCKETS - 1;
        buckets[b]++;
    }

    double expected_per_bucket = (double)NUM_SAMPLES / (double)NUM_BUCKETS;
    double chi_squared = 0.0;
    int min_bucket = NUM_SAMPLES;
    int max_bucket = 0;
    for (i = 0; i < NUM_BUCKETS; i++) {
        double diff = (double)buckets[i] - expected_per_bucket;
        chi_squared += (diff * diff) / expected_per_bucket;
        if (buckets[i] < min_bucket) min_bucket = buckets[i];
        if (buckets[i] > max_bucket) max_bucket = buckets[i];
    }

    /* degrees of freedom = NUM_BUCKETS - 1 = 19 */
    /* critical value at p=0.05 for df=19 is ~30.14 */
    double chi_critical = 30.14;
    int chi_pass = (chi_squared < chi_critical) ? 1 : 0;

    /* ---- Runs test ---- */
    int num_runs = 1;
    int run_up = (samples[1] > samples[0]) ? 1 : 0;
    for (i = 2; i < NUM_SAMPLES; i++) {
        int going_up = (samples[i] > samples[i - 1]) ? 1 : 0;
        if (going_up != run_up) {
            num_runs++;
            run_up = going_up;
        }
    }

    /* Expected runs for n items: (2n - 1) / 3 */
    double expected_runs = (2.0 * NUM_SAMPLES - 1.0) / 3.0;
    /* Variance of runs: (16n - 29) / 90 */
    double runs_variance = (16.0 * NUM_SAMPLES - 29.0) / 90.0;
    double runs_stddev = 1.0;
    /* Newton's method for sqrt */
    double rs = runs_variance;
    int iter;
    for (iter = 0; iter < 50; iter++) {
        if (runs_stddev <= 0.0) break;
        runs_stddev = (runs_stddev + rs / runs_stddev) / 2.0;
    }

    double runs_z = ((double)num_runs - expected_runs) / runs_stddev;
    int runs_pass = (runs_z > -1.96 && runs_z < 1.96) ? 1 : 0;

    /* ---- Serial correlation ---- */
    double sum_xy = 0.0;
    double sum_x = 0.0;
    double sum_y = 0.0;
    double sum_x2 = 0.0;
    double sum_y2 = 0.0;
    int n_pairs = NUM_SAMPLES - 1;

    for (i = 0; i < n_pairs; i++) {
        double x = samples[i];
        double y = samples[i + 1];
        sum_xy += x * y;
        sum_x += x;
        sum_y += y;
        sum_x2 += x * x;
        sum_y2 += y * y;
    }

    double np = (double)n_pairs;
    double corr_num = np * sum_xy - sum_x * sum_y;
    double corr_den_a = np * sum_x2 - sum_x * sum_x;
    double corr_den_b = np * sum_y2 - sum_y * sum_y;
    double corr_den = corr_den_a * corr_den_b;

    /* sqrt via Newton's */
    double corr_den_sqrt = corr_den / 2.0;
    for (iter = 0; iter < 50; iter++) {
        if (corr_den_sqrt <= 0.0) break;
        corr_den_sqrt = (corr_den_sqrt + corr_den / corr_den_sqrt) / 2.0;
    }

    double correlation = (corr_den_sqrt > 0.0) ? corr_num / corr_den_sqrt : 0.0;
    int corr_pass = (correlation > -0.05 && correlation < 0.05) ? 1 : 0;

    /* ---- Output ---- */
    printf("LCG Parameters: a=%llu c=%llu m=%llu seed=42\n", a, c, m);
    printf("Samples: %d\n\n", NUM_SAMPLES);

    printf("=== Distribution ===\n");
    printf("  Mean:     %.6f (expected %.6f, error=%.6f)\n",
           mean, expected_mean, mean_error);
    printf("  Variance: %.6f (expected %.6f, error=%.6f)\n\n",
           variance, expected_var, var_error);

    printf("=== Chi-Squared Uniformity ===\n");
    printf("  Buckets: %d, expected %.0f per bucket\n",
           NUM_BUCKETS, expected_per_bucket);
    printf("  Range: [%d, %d]\n", min_bucket, max_bucket);
    printf("  Chi^2 = %.4f (critical=%.2f) -> %s\n\n",
           chi_squared, chi_critical, chi_pass ? "PASS" : "FAIL");

    printf("=== Runs Test ===\n");
    printf("  Runs: %d (expected %.0f)\n", num_runs, expected_runs);
    printf("  Z-score: %.4f -> %s\n\n", runs_z, runs_pass ? "PASS" : "FAIL");

    printf("=== Serial Correlation ===\n");
    printf("  r = %.6f -> %s\n", correlation, corr_pass ? "PASS" : "FAIL");

    int total_pass = chi_pass + runs_pass + corr_pass;
    printf("\nOverall: %d/3 tests passed\n", total_pass);

    return 0;
}
