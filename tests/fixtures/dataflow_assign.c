/* Fixture for variable_dataflow_sites: local decl, = write, += write, static global. */

static int counter;

int main(void) {
    int x;
    x = 1;
    x += 2;
    counter = x;
    return counter;
}
