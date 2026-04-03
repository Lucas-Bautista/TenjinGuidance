#include <stdio.h>

/*
 * Reverse Polish Notation (RPN) calculator.
 * Evaluates multiple expressions using an array-based stack.
 * Supports: +, -, *, /, % (on integers), and demonstrates
 * both integer and floating-point evaluation modes.
 */

#define MAX_STACK 64
#define MAX_TOKENS 32
#define MAX_TOKEN_LEN 16

int main(void) {
    /* RPN expressions as token arrays, terminated by "" */
    /* Expression 0: "3 4 +" = 7 */
    char expr0[][MAX_TOKEN_LEN] = {"3", "4", "+", ""};
    /* Expression 1: "5 1 2 + 4 * + 3 -" = 14 */
    char expr1[][MAX_TOKEN_LEN] = {"5", "1", "2", "+", "4", "*", "+", "3", "-", ""};
    /* Expression 2: "2 3 * 4 5 * +" = 26 */
    char expr2[][MAX_TOKEN_LEN] = {"2", "3", "*", "4", "5", "*", "+", ""};
    /* Expression 3: "10 2 / 3 * 5 +" = 20 */
    char expr3[][MAX_TOKEN_LEN] = {"10", "2", "/", "3", "*", "5", "+", ""};
    /* Expression 4: "15 7 1 1 + - / 3 * 2 1 1 + + -" = 5 */
    char expr4[][MAX_TOKEN_LEN] = {"15", "7", "1", "1", "+", "-", "/",
                                    "3", "*", "2", "1", "1", "+", "+", "-", ""};
    /* Expression 5: "100 50 25 + -" = 25 */
    char expr5[][MAX_TOKEN_LEN] = {"100", "50", "25", "+", "-", ""};

    int expected[] = {7, 14, 26, 20, 5, 25};
    int num_exprs = 6;

    /* Process each expression */
    double stack[MAX_STACK];
    int sp;  /* stack pointer */

    int e;
    int passed = 0;
    int failed = 0;

    for (e = 0; e < num_exprs; e++) {
        sp = 0;
        int error = 0;
        int token_count = 0;

        /* Select expression */
        char (*tokens)[MAX_TOKEN_LEN];
        switch (e) {
            case 0: tokens = expr0; break;
            case 1: tokens = expr1; break;
            case 2: tokens = expr2; break;
            case 3: tokens = expr3; break;
            case 4: tokens = expr4; break;
            case 5: tokens = expr5; break;
            default: tokens = expr0;
        }

        /* Print expression */
        printf("Expr %d: ", e);
        int ti = 0;
        while (tokens[ti][0] != '\0') {
            printf("%s ", tokens[ti]);
            ti++;
        }

        /* Evaluate */
        ti = 0;
        while (tokens[ti][0] != '\0' && !error) {
            char *tok = tokens[ti];
            token_count++;

            /* Check if operator */
            int is_op = 0;
            char op = '\0';
            if (tok[1] == '\0') {
                if (tok[0] == '+' || tok[0] == '-' || tok[0] == '*' ||
                    tok[0] == '/' || tok[0] == '%') {
                    /* Could be operator or negative number.
                       It's an operator if single char and one of +-*%/ */
                    is_op = 1;
                    op = tok[0];
                }
            }

            if (is_op) {
                if (sp < 2) {
                    error = 1;  /* stack underflow */
                    break;
                }
                double b = stack[--sp];
                double a = stack[--sp];
                double result;

                switch (op) {
                    case '+': result = a + b; break;
                    case '-': result = a - b; break;
                    case '*': result = a * b; break;
                    case '/':
                        if (b == 0.0) { error = 2; result = 0.0; }
                        else result = a / b;
                        break;
                    case '%':
                        if ((int)b == 0) { error = 2; result = 0.0; }
                        else result = (double)((int)a % (int)b);
                        break;
                    default: result = 0.0; error = 3;
                }

                if (!error) {
                    stack[sp++] = result;
                }
            } else {
                /* Parse number */
                double num = 0.0;
                int sign = 1;
                int j = 0;
                int has_dot = 0;
                double decimal_place = 0.1;

                if (tok[0] == '-' && tok[1] != '\0') {
                    sign = -1;
                    j = 1;
                }

                while (tok[j] != '\0') {
                    if (tok[j] == '.') {
                        has_dot = 1;
                        j++;
                        continue;
                    }
                    if (tok[j] < '0' || tok[j] > '9') {
                        error = 4;  /* invalid token */
                        break;
                    }
                    int digit = tok[j] - '0';
                    if (has_dot) {
                        num += (double)digit * decimal_place;
                        decimal_place *= 0.1;
                    } else {
                        num = num * 10.0 + (double)digit;
                    }
                    j++;
                }

                num *= (double)sign;

                if (!error && sp < MAX_STACK) {
                    stack[sp++] = num;
                }
            }
            ti++;
        }

        /* Result */
        if (error) {
            printf("-> ERROR (code %d)\n", error);
            failed++;
        } else if (sp != 1) {
            printf("-> ERROR (stack has %d items, expected 1)\n", sp);
            failed++;
        } else {
            double result = stack[0];
            int int_result = (int)result;
            int correct = (int_result == expected[e]) ? 1 : 0;

            printf("= %.1f (expected %d) %s\n",
                   result, expected[e], correct ? "OK" : "FAIL");

            if (correct) passed++;
            else failed++;
        }
    }

    printf("\n%d/%d expressions evaluated correctly\n", passed, passed + failed);

    /* Bonus: evaluate a floating-point expression */
    /* "3.14 2 * 1.5 +" = 7.78 */
    printf("\nBonus (float): ");
    char fexpr[][MAX_TOKEN_LEN] = {"3.14", "2", "*", "1.5", "+", ""};

    sp = 0;
    int fi = 0;
    while (fexpr[fi][0] != '\0') {
        printf("%s ", fexpr[fi]);
        char *tok = fexpr[fi];

        int is_op = (tok[1] == '\0' && (tok[0] == '+' || tok[0] == '-' ||
                     tok[0] == '*' || tok[0] == '/'));

        if (is_op && sp >= 2) {
            double b = stack[--sp];
            double a = stack[--sp];
            double r;
            switch (tok[0]) {
                case '+': r = a + b; break;
                case '-': r = a - b; break;
                case '*': r = a * b; break;
                case '/': r = (b != 0.0) ? a / b : 0.0; break;
                default:  r = 0.0;
            }
            stack[sp++] = r;
        } else {
            double num = 0.0;
            int j = 0;
            int has_dot = 0;
            double dp = 0.1;
            while (tok[j]) {
                if (tok[j] == '.') { has_dot = 1; j++; continue; }
                int d = tok[j] - '0';
                if (has_dot) { num += d * dp; dp *= 0.1; }
                else { num = num * 10.0 + d; }
                j++;
            }
            stack[sp++] = num;
        }
        fi++;
    }
    printf("= %.4f\n", stack[0]);

    return 0;
}
