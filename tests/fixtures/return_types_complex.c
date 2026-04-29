/*
 * Heavier coverage for function_return_types: stdint, structs, enums,
 * pointer / qualified-pointer, float, and pointer-to-function return types.
 * Intentionally C11, same mode as the rest of Tractor.
 */
#include <stddef.h>
#include <stdint.h>

/* --- struct and typedef returns --- */
struct point {
    int x;
    int y;
};

struct point returns_struct(struct point p) { return p; }

typedef struct {
    int id;
} thing_t;

thing_t returns_thing(void) {
    thing_t t;
    t.id = 0;
    return t;
}

/* --- enum return --- */
enum color { RED, GREEN, BLUE };

enum color pick_color(int i) { return (enum color)(i % 3); }

/* --- stdint and stddef --- */
uint32_t read_u32(void) { return 0U; }

size_t bytes_for(void) { return sizeof(int); }

_Bool flag_is_set(void) { return 0; }

/* --- float / long long --- */
float fsum(float a, float b) { return a + b; }

double dprod(double a, double b) { return a * b; }

unsigned long long big_counter(void) { return 0ULL; }

/* --- pointer returns --- */
int *int_ptr(int *p) { return p; }

const void *cvp(void) { return (const void *)0; }

void *malloc_like(size_t n) { (void)n; return (void *)0; }

volatile int *g_volatile_ptr;

volatile int *volatile_get(void) { return g_volatile_ptr; }

/* return type is pointer to function: int(int, int) */
int (*get_binop(int tag))(int, int) { (void)tag; return 0; }

int main(void) { return 0; }
