#include <stdio.h>

/*
 * Numerical integration using Trapezoidal and Simpson's 1/3 rule.
 * Integrates several known functions and compares against exact answers.
 * Studies convergence as number of intervals increases.
 */

int main(void) {
    /*
     * Test functions evaluated inline (no function pointers, primitives only):
     *   f0(x) = x^2           on [0,1], exact = 1/3
     *   f1(x) = x^3           on [0,2], exact = 4
     *   f2(x) = 1/(1+x^2)    on [0,1], exact = pi/4
     *   f3(x) = x*e^(-x)     on [0,5], approximate e^(-x) via Taylor
     */

    double exact[4];
    exact[0] = 1.0 / 3.0;
    exact[1] = 4.0;
    exact[2] = 0.7853981633974483;  /* pi/4 */
    exact[3] = 0.9595723180054873;  /* 1 - 6*e^(-5), via integration by parts */

    double lo[4] = {0.0, 0.0, 0.0, 0.0};
    double hi[4] = {1.0, 2.0, 1.0, 5.0};

    int intervals[] = {4, 8, 16, 32, 64, 128, 256, 512, 1024};
    int num_intervals = 9;

    int func;
    for (func = 0; func < 4; func++) {
        double a = lo[func];
        double b = hi[func];
        double exact_val = exact[func];

        printf("=== Function %d on [%.0f, %.0f], exact = %.15f ===\n",
               func, a, b, exact_val);
        printf("%-8s  %-18s %-12s  %-18s %-12s\n",
               "N", "Trapezoidal", "Error", "Simpson", "Error");

        int ni;
        for (ni = 0; ni < num_intervals; ni++) {
            int n = intervals[ni];
            double h = (b - a) / (double)n;

            /* Trapezoidal rule */
            double trap_sum = 0.0;
            int i;
            for (i = 0; i <= n; i++) {
                double x = a + (double)i * h;
                double fx;

                switch (func) {
                    case 0: fx = x * x; break;
                    case 1: fx = x * x * x; break;
                    case 2: fx = 1.0 / (1.0 + x * x); break;
                    case 3: {
                        /* e^(-x) via Taylor series (20 terms) */
                        double ex = 1.0;
                        double term = 1.0;
                        int t;
                        for (t = 1; t <= 20; t++) {
                            term *= (-x) / (double)t;
                            ex += term;
                        }
                        fx = x * ex;
                        break;
                    }
                    default: fx = 0.0;
                }

                if (i == 0 || i == n) {
                    trap_sum += fx;
                } else {
                    trap_sum += 2.0 * fx;
                }
            }
            double trap_result = trap_sum * h / 2.0;
            double trap_error = trap_result - exact_val;
            if (trap_error < 0.0) trap_error = -trap_error;

            /* Simpson's 1/3 rule (requires even n) */
            double simp_result = 0.0;
            double simp_error = 0.0;
            int simp_n = n;
            if (simp_n % 2 != 0) simp_n++;  /* make even */
            double simp_h = (b - a) / (double)simp_n;

            double simp_sum = 0.0;
            for (i = 0; i <= simp_n; i++) {
                double x = a + (double)i * simp_h;
                double fx;

                switch (func) {
                    case 0: fx = x * x; break;
                    case 1: fx = x * x * x; break;
                    case 2: fx = 1.0 / (1.0 + x * x); break;
                    case 3: {
                        double ex = 1.0;
                        double term = 1.0;
                        int t;
                        for (t = 1; t <= 20; t++) {
                            term *= (-x) / (double)t;
                            ex += term;
                        }
                        fx = x * ex;
                        break;
                    }
                    default: fx = 0.0;
                }

                if (i == 0 || i == simp_n) {
                    simp_sum += fx;
                } else if (i % 2 == 1) {
                    simp_sum += 4.0 * fx;
                } else {
                    simp_sum += 2.0 * fx;
                }
            }
            simp_result = simp_sum * simp_h / 3.0;
            simp_error = simp_result - exact_val;
            if (simp_error < 0.0) simp_error = -simp_error;

            printf("%-8d  %-18.15f %.4e  %-18.15f %.4e\n",
                   n, trap_result, trap_error, simp_result, simp_error);
        }
        printf("\n");
    }

    /* Convergence rate analysis for f0 = x^2 */
    printf("=== Convergence Rates for x^2 on [0,1] ===\n");
    printf("(Trap should be O(h^2), Simpson O(h^4) but exact for poly<=3)\n");
    double prev_trap_err = 0.0;
    double prev_simp_err = 0.0;

    int ni;
    for (ni = 0; ni < num_intervals; ni++) {
        int n = intervals[ni];
        double h = 1.0 / (double)n;

        double trap = 0.0;
        int i;
        for (i = 0; i <= n; i++) {
            double x = (double)i * h;
            double w = (i == 0 || i == n) ? 1.0 : 2.0;
            trap += w * x * x;
        }
        trap *= h / 2.0;
        double te = trap - exact[0];
        if (te < 0.0) te = -te;

        double trap_ratio = (prev_trap_err > 0.0 && te > 0.0) ?
                             prev_trap_err / te : 0.0;

        printf("  n=%-5d  trap_err=%.4e  ratio=%.2f\n",
               n, te, trap_ratio);
        prev_trap_err = te;
    }

    return 0;
}
