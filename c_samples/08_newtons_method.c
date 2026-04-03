#include <stdio.h>

/*
 * Newton-Raphson method for finding roots of functions:
 *   1. Square root (f(x) = x^2 - n)
 *   2. Cube root   (f(x) = x^3 - n)
 *   3. General polynomial root finding
 * Tracks convergence rate (quadratic for Newton's method).
 */

int main(void) {
    double tolerance = 1e-12;
    int max_iter = 100;

    /* ---- Square root via Newton's method ---- */
    double sqrt_inputs[] = {2.0, 3.0, 10.0, 144.0, 0.25, 1000000.0};
    int num_sqrt = 6;

    printf("=== Square Root (Newton's Method) ===\n");
    printf("%-12s %-20s %-6s %-12s\n", "Input", "Result", "Iters", "Error^2/Err");

    int i;
    for (i = 0; i < num_sqrt; i++) {
        double n = sqrt_inputs[i];
        double x = n / 2.0;
        if (x < 1.0) x = 1.0;

        int iters = 0;
        double prev_err = 0.0;
        double convergence_ratio = 0.0;

        while (iters < max_iter) {
            double fx = x * x - n;
            double fpx = 2.0 * x;

            double err = fx;
            if (err < 0.0) err = -err;

            if (iters > 1 && prev_err > tolerance) {
                convergence_ratio = err / (prev_err * prev_err);
            }

            if (err < tolerance) break;

            prev_err = err;
            x = x - fx / fpx;
            iters++;
        }

        double residual = x * x - n;
        if (residual < 0.0) residual = -residual;

        printf("%-12.1f %-20.15f %-6d %.6e\n",
               n, x, iters, convergence_ratio);
    }

    /* ---- Cube root ---- */
    double cbrt_inputs[] = {8.0, 27.0, 2.0, -8.0, 1000.0};
    int num_cbrt = 5;

    printf("\n=== Cube Root (Newton's Method) ===\n");
    printf("%-12s %-20s %-6s\n", "Input", "Result", "Iters");

    for (i = 0; i < num_cbrt; i++) {
        double n = cbrt_inputs[i];
        double x = n / 3.0;
        if (x > -1.0 && x < 1.0) x = (n >= 0.0) ? 1.0 : -1.0;

        int iters = 0;

        while (iters < max_iter) {
            double fx = x * x * x - n;
            double fpx = 3.0 * x * x;

            if (fpx == 0.0) {
                x += 0.1;
                continue;
            }

            double err = fx;
            if (err < 0.0) err = -err;
            if (err < tolerance) break;

            x = x - fx / fpx;
            iters++;
        }

        double check = x * x * x;
        double residual = check - n;
        if (residual < 0.0) residual = -residual;

        printf("%-12.1f %-20.15f %-6d  (x^3=%.10f, res=%.2e)\n",
               n, x, iters, check, residual);
    }

    /* ---- Polynomial: x^4 - 5x^2 + 4 = (x^2-1)(x^2-4) roots at +-1, +-2 ---- */
    double guesses[] = {0.5, 1.5, -0.8, -2.5, 3.0, -1.5};
    int num_guesses = 6;

    printf("\n=== Polynomial x^4 - 5x^2 + 4 ===\n");
    printf("%-10s %-20s %-6s %-12s\n", "Guess", "Root Found", "Iters", "f(root)");

    int g;
    for (g = 0; g < num_guesses; g++) {
        double x = guesses[g];
        int iters = 0;
        int converged = 1;

        while (iters < max_iter) {
            double x2 = x * x;
            double fx = x2 * x2 - 5.0 * x2 + 4.0;
            double fpx = 4.0 * x * x2 - 10.0 * x;

            double err = fx;
            if (err < 0.0) err = -err;
            if (err < tolerance) break;

            if (fpx == 0.0) {
                converged = 0;
                break;
            }

            x = x - fx / fpx;
            iters++;
        }

        double x2 = x * x;
        double fval = x2 * x2 - 5.0 * x2 + 4.0;

        if (converged) {
            printf("%-10.1f %-20.15f %-6d %.2e\n",
                   guesses[g], x, iters, fval);
        } else {
            printf("%-10.1f  ** did not converge **\n", guesses[g]);
        }
    }

    /* ---- Convergence table for sqrt(2) showing quadratic convergence ---- */
    printf("\n=== Convergence Detail for sqrt(2) ===\n");
    printf("%-4s %-22s %-15s\n", "Iter", "Estimate", "Error");

    double x = 1.0;
    int iter;
    for (iter = 0; iter < 8; iter++) {
        double err = x * x - 2.0;
        if (err < 0.0) err = -err;
        printf("%-4d %-22.18f %.6e\n", iter, x, err);

        double fx = x * x - 2.0;
        double fpx = 2.0 * x;
        x = x - fx / fpx;
    }

    return 0;
}
