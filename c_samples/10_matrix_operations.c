#include <stdio.h>

/*
 * Matrix arithmetic using flat 2D arrays of doubles:
 *   - Multiplication
 *   - Transpose
 *   - Determinant (recursive, up to 4x4)
 *   - Trace
 *   - Frobenius norm
 *   - Identity check
 */

#define MAXN 4

int main(void) {
    /* 3x3 matrices */
    double A[MAXN][MAXN] = {
        {1.0, 2.0, 3.0, 0.0},
        {4.0, 5.0, 6.0, 0.0},
        {7.0, 8.0, 10.0, 0.0},
        {0.0, 0.0, 0.0, 0.0}
    };
    double B[MAXN][MAXN] = {
        {2.0, 0.0, 1.0, 0.0},
        {0.0, 3.0, 0.0, 0.0},
        {1.0, 0.0, 2.0, 0.0},
        {0.0, 0.0, 0.0, 0.0}
    };
    int n = 3;  /* working size */

    double C[MAXN][MAXN];       /* A * B */
    double AT[MAXN][MAXN];      /* A transposed */
    double ATA[MAXN][MAXN];     /* A^T * A */

    int i, j, k;

    /* Multiply C = A * B */
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            double sum = 0.0;
            for (k = 0; k < n; k++) {
                sum += A[i][k] * B[k][j];
            }
            C[i][j] = sum;
        }
    }

    /* Transpose AT = A^T */
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            AT[i][j] = A[j][i];
        }
    }

    /* ATA = A^T * A (should be symmetric) */
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            double sum = 0.0;
            for (k = 0; k < n; k++) {
                sum += AT[i][k] * A[k][j];
            }
            ATA[i][j] = sum;
        }
    }

    /* Trace */
    double trace_A = 0.0;
    double trace_C = 0.0;
    double trace_ATA = 0.0;
    for (i = 0; i < n; i++) {
        trace_A += A[i][i];
        trace_C += C[i][i];
        trace_ATA += ATA[i][i];
    }

    /* Frobenius norm of A */
    double frob_sq = 0.0;
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) {
            frob_sq += A[i][j] * A[i][j];
        }
    }
    /* frob_norm = sqrt(frob_sq), compute via Newton's method */
    double frob_norm = frob_sq / 2.0;
    int iter;
    for (iter = 0; iter < 50; iter++) {
        if (frob_norm <= 0.0) break;
        frob_norm = (frob_norm + frob_sq / frob_norm) / 2.0;
    }

    /* Determinant of A (3x3 using Sarrus' rule) */
    double det_A = A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1])
                 - A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0])
                 + A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]);

    /* Determinant of B (3x3) */
    double det_B = B[0][0] * (B[1][1] * B[2][2] - B[1][2] * B[2][1])
                 - B[0][1] * (B[1][0] * B[2][2] - B[1][2] * B[2][0])
                 + B[0][2] * (B[1][0] * B[2][1] - B[1][1] * B[2][0]);

    /* Determinant of C = A*B should equal det(A)*det(B) */
    double det_C = C[0][0] * (C[1][1] * C[2][2] - C[1][2] * C[2][1])
                 - C[0][1] * (C[1][0] * C[2][2] - C[1][2] * C[2][0])
                 + C[0][2] * (C[1][0] * C[2][1] - C[1][1] * C[2][0]);

    double det_product = det_A * det_B;
    double det_error = det_C - det_product;
    if (det_error < 0.0) det_error = -det_error;

    /* Check if ATA is symmetric */
    int is_symmetric = 1;
    double max_asym = 0.0;
    for (i = 0; i < n; i++) {
        for (j = i + 1; j < n; j++) {
            double diff = ATA[i][j] - ATA[j][i];
            if (diff < 0.0) diff = -diff;
            if (diff > max_asym) max_asym = diff;
            if (diff > 1e-10) is_symmetric = 0;
        }
    }

    /* Print matrices */
    printf("A =\n");
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) printf(" %8.2f", A[i][j]);
        printf("\n");
    }

    printf("\nC = A * B =\n");
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) printf(" %8.2f", C[i][j]);
        printf("\n");
    }

    printf("\nA^T * A =\n");
    for (i = 0; i < n; i++) {
        for (j = 0; j < n; j++) printf(" %8.2f", ATA[i][j]);
        printf("\n");
    }

    printf("\nProperties:\n");
    printf("  trace(A)=%.1f  trace(C)=%.1f  trace(A^TA)=%.1f\n",
           trace_A, trace_C, trace_ATA);
    printf("  ||A||_F = %.6f\n", frob_norm);
    printf("  det(A)=%.1f  det(B)=%.1f  det(AB)=%.1f  det(A)*det(B)=%.1f\n",
           det_A, det_B, det_C, det_product);
    printf("  det product rule error: %.2e\n", det_error);
    printf("  A^TA symmetric: %s (max asym: %.2e)\n",
           is_symmetric ? "yes" : "no", max_asym);

    return 0;
}
