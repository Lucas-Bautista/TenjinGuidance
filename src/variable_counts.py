import subprocess
from pathlib import Path
from collections import Counter
from clang.cindex import Config
Config.set_library_path("/opt/homebrew/opt/llvm/lib")
from clang.cindex import Index, CursorKind, Cursor
from collections import Counter


    
def _sdk_args() -> list[str]:
    sdk = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    # -isysroot should be sufficient; the -I is a pragmatic fallback if bindings/toolchain mismatch.
    return ["-isysroot", sdk, "-I", f"{sdk}/usr/include"]

def _enclosing_function_name(cur: Cursor) -> str:
    """
    Returns the function this cursor is semantically inside of.
    If it isn't inside a function, returns 'GLOBAL'.
    """
    p = cur.semantic_parent
    while p is not None:
        if p.kind == CursorKind.FUNCTION_DECL:
            return p.spelling or "<anonymous>"
        if p.kind == CursorKind.TRANSLATION_UNIT:
            return "GLOBAL"
        p = p.semantic_parent
    return "GLOBAL"

def count_variables(filename: str) -> Counter:
    index = Index.create()

    args = ["-x", "c", "-std=c11", *_sdk_args()]
    tu = index.parse(filename, args=args)
    if tu.diagnostics:
        print("=== clang diagnostics ===")
        for d in tu.diagnostics:
            print(d)
        print("=========================")
    counts = Counter()

    main_file = Path(tu.spelling).resolve()

    def in_main_file(cur) -> bool:
        # cur.location.file can be None for some synthetic nodes
        if not cur.location.file:
            return False
        try:
            return Path(cur.location.file.name).resolve() == main_file
        except OSError:
            return False
    
    def visit(node):
        # Variable declarations
        if node.kind == CursorKind.VAR_DECL and in_main_file(node):
            func = _enclosing_function_name(node)  # 'GLOBAL', 'main', 'perform_expensive_operations', ...
            # print(f"Visiting node: {node.spelling} (kind: {node.kind}), type: {node.type.spelling}), location: {node.location}, function: {func}\n")
            counts[(func, node.spelling, node.type.spelling)] += 1
        # References to variables (every time you use one)
        elif node.kind == CursorKind.DECL_REF_EXPR:
            ref = node.referenced
            if ref and (ref.kind == CursorKind.VAR_DECL or ref.kind == CursorKind.PARM_DECL) and in_main_file(node):
                origin = _enclosing_function_name(ref)
                # print(f"Visiting node: {node.spelling} (kind: {node.kind}), type: {node.type.spelling}), location: {node.location}, function: {origin}\n")
                counts[(origin, node.spelling, node.type.spelling)] += 1
        
        for child in node.get_children():
            visit(child)
    
    visit(tu.cursor)
    # print(f"Finished counting variables in {filename}. Total distinct variables: {len(counts)}\n\n\n\n")
    return counts

if __name__ == "__main__":
    # Only runs when you execute: python src/variable_counts.py
    sample = (Path(__file__).resolve().parent / ".." / "c_samples" / "02_gcd_lcm.c").resolve()
    print("Parsing:", sample)
    print(count_variables(str(sample)))