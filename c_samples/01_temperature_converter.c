#include <stdio.h>

/*
 * Converts temperatures between Fahrenheit, Celsius, and Kelvin.
 * Prints a conversion table for a given range.
 */

int main(void) {
    double fahr_start = -40.0;
    double fahr_end = 212.0;
    double step = 10.0;

    double fahr = fahr_start;
    double celsius;
    double kelvin;

    int row_count = 0;

    printf("%10s %10s %10s\n", "Fahr", "Celsius", "Kelvin");
    printf("--------------------------------\n");

    while (fahr <= fahr_end) {
        celsius = (fahr - 32.0) * 5.0 / 9.0;
        kelvin = celsius + 273.15;
        printf("%10.1f %10.2f %10.2f\n", fahr, celsius, kelvin);
        fahr += step;
        row_count++;
    }

    double avg_fahr = (fahr_start + fahr_end) / 2.0;
    double avg_celsius = (avg_fahr - 32.0) * 5.0 / 9.0;

    printf("\nRows printed: %d\n", row_count);
    printf("Midpoint: %.1fF = %.2fC\n", avg_fahr, avg_celsius);

    return 0;
}
