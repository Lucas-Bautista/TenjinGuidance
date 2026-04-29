/* Unions, const-qualified struct return, static inline, and restrict (C99). */
#include <stddef.h>

typedef union {
    int i;
    float f;
} number_t;

number_t as_number(int v) {
    number_t n;
    n.i = v;
    return n;
}

struct pair {
    int a;
    int b;
};

const struct pair *pair_addr(const struct pair *p) { return p; }

static inline int inline_add(int x, int y) { return x + y; }

int *restrict alloc_block(void) { return 0; }

int main(void) { return 0; }
