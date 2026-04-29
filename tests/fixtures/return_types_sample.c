/* Fixture for function_return_types tests: multiple definitions, one prototype, static, void. */

int only_prototype(int x);

int with_proto_then_def(int x);

int with_proto_then_def(int x) { return x; }

void returns_void(void) {}

static long static_helper(double x) {
	(void)x;
	return 0L;
}

int main(void) { return 0; }
