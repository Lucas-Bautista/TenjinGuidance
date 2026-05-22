from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from clang_config import clang_parse_args, configure_libclang
from clang.cindex import Index, CursorKind, Cursor


def _ensure_clang() -> None:
    configure_libclang()

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


def _var_key_for_decl(func: str, name: str) -> str:
    if func == "GLOBAL":
        return f"GLOBAL:{name}"
    return f"{func}:{name}"


def _cursor_same(a: Cursor, b: Cursor) -> bool:
    """Match cursors; libclang may return distinct objects for the same AST node."""
    if a == b:
        return True
    if a.kind != b.kind:
        return False
    loc_a, loc_b = a.location, b.location
    if loc_a.file is None or loc_b.file is None:
        return False
    return (
        loc_a.file.name == loc_b.file.name
        and loc_a.line == loc_b.line
        and loc_a.column == loc_b.column
    )


def _cursor_contains(ancestor: Cursor, target: Cursor) -> bool:
    """True if target appears anywhere under ancestor in the AST subtree."""
    if _cursor_same(ancestor, target):
        return True
    for child in ancestor.get_children():
        if _cursor_contains(child, target):
            return True
    return False


def _wrapper_expr_kinds() -> frozenset[int]:
    names = (
        "UNEXPOSED_EXPR",
        "PAREN_EXPR",
        "IMPLICIT_CAST_EXPR",
        "CSTYLE_CAST_EXPR",
        "CAST_EXPR",
    )
    kinds: set[int] = set()
    for name in names:
        k = getattr(CursorKind, name, None)
        if k is not None:
            kinds.add(k)
    return frozenset(kinds)


def _lhs_root(cursor: Cursor) -> Cursor:
    """Peel transparent wrappers to the left-hand root of an assignment."""
    cur = cursor
    while cur.kind in _wrapper_expr_kinds():
        children = list(cur.get_children())
        if not children:
            break
        cur = children[0]
    return cur


def _binary_is_plain_assign(anc: Cursor) -> bool:
    """True for '=' assignment (not ==, +=, etc.)."""
    try:
        bo = anc.binary_operator
        if bo and bo.is_assignment:
            return True
    except Exception:
        pass
    toks = [t.spelling for t in anc.get_tokens()]
    if "=" not in toks:
        return False
    compound = ("+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=")
    if any(t in toks for t in compound):
        return False
    if any(t in ("==", "!=", "<=", ">=") for t in toks):
        return False
    return toks.count("=") == 1


def _decl_ref_is_write(node: Cursor, ancestors: tuple[Cursor, ...]) -> bool:
    """
    True if this DECL_REF is written: assignment LHS, compound assign LHS, or ++/-- operand.

    libclang version/platform differences often wrap refs in casts between the ref and the
    assignment operator, so we walk the ancestor chain from the recursive visit (not only the
    immediate parent).
    """
    for anc in ancestors:
        if anc.kind == CursorKind.COMPOUND_ASSIGNMENT_OPERATOR:
            children = list(anc.get_children())
            if children and _cursor_same(_lhs_root(children[0]), node):
                return True
            continue

        if anc.kind == CursorKind.BINARY_OPERATOR:
            children = list(anc.get_children())
            if not children or not _binary_is_plain_assign(anc):
                continue
            # Only the direct LHS (e.g. x in `x = 1`, not x in `counter = x`).
            if _cursor_same(_lhs_root(children[0]), node):
                return True
            continue

        if anc.kind == CursorKind.UNARY_OPERATOR:
            children = list(anc.get_children())
            if not children or not _cursor_contains(children[0], node):
                continue
            try:
                uo = anc.unary_operator
            except Exception:
                uo = None
            if uo is not None:
                spelling = (getattr(uo, "spelling", None) or "").strip()
                if spelling in ("++", "--") or spelling.endswith("++") or spelling.endswith("--"):
                    return True
            # Fallback when unary_operator metadata is missing (some Linux libclang builds).
            tokens = [t.spelling for t in anc.get_tokens()]
            if any(t in ("++", "--") for t in tokens):
                return True

    return False


def variable_dataflow_sites(filename: str) -> dict[str, Any]:
    """
    Per-variable def/ref lines in the main translation unit, keyed like guidance:
    GLOBAL:x for file scope, f:x for locals/params in function f.

    Each entry is {"c_type": str, "sites": [{"line", "role"}, ...]} with roles
    decl, param, read, write (write = lhs of = or += style assignment; uses AST parent
    because libclang often omits semantic_parent on DECL_REF_EXPR).
    """
    _ensure_clang()
    index = Index.create()
    args = clang_parse_args()
    tu = index.parse(filename, args=args)
    if tu.diagnostics:
        print("=== clang diagnostics ===")
        for d in tu.diagnostics:
            print(d)
        print("=========================")

    main_file = Path(tu.spelling).resolve()
    site_lists: dict[str, list[dict[str, Any]]] = defaultdict(list)
    c_types: dict[str, str] = {}

    def in_main_file(cur: Cursor) -> bool:
        if not cur.location.file:
            return False
        try:
            return Path(cur.location.file.name).resolve() == main_file
        except OSError:
            return False

    def visit(node: Cursor, ancestors: tuple[Cursor, ...] = ()) -> None:
        if node.kind == CursorKind.VAR_DECL and in_main_file(node):
            n = (node.spelling or "").strip()
            if not n:
                return
            func = _enclosing_function_name(node)
            k = _var_key_for_decl(func, n)
            line = int(node.location.line)
            site_lists[k].append({"line": line, "role": "decl"})
            c_types[k] = node.type.spelling
        elif node.kind == CursorKind.PARM_DECL and in_main_file(node):
            p = node.semantic_parent
            if p is not None and p.kind == CursorKind.FUNCTION_DECL and not p.is_definition():
                return
            n = (node.spelling or "").strip()
            if not n:
                return
            if p is not None and p.kind == CursorKind.FUNCTION_DECL:
                func = p.spelling or "<anonymous>"
            else:
                func = _enclosing_function_name(node)
            k = _var_key_for_decl(func, n)
            site_lists[k].append(
                {"line": int(node.location.line), "role": "param"}
            )
            c_types[k] = node.type.spelling
        elif node.kind == CursorKind.DECL_REF_EXPR:
            ref = node.referenced
            if not ref or ref.kind not in (
                CursorKind.VAR_DECL,
                CursorKind.PARM_DECL,
            ):
                return
            if ref.kind == CursorKind.PARM_DECL:
                pfun = ref.semantic_parent
                if (
                    pfun is not None
                    and pfun.kind == CursorKind.FUNCTION_DECL
                    and not pfun.is_definition()
                ):
                    return
            if not in_main_file(node):
                return
            n = (ref.spelling or node.spelling or "").strip()
            if not n:
                return
            func = _enclosing_function_name(ref)
            k = _var_key_for_decl(func, n)
            if k not in c_types and ref.type.spelling:
                c_types[k] = ref.type.spelling
            if _decl_ref_is_write(node, ancestors):
                site_lists[k].append(
                    {"line": int(node.location.line), "role": "write"}
                )
            else:
                site_lists[k].append(
                    {"line": int(node.location.line), "role": "read"}
                )

        for c in node.get_children():
            visit(c, ancestors + (node,))

    visit(tu.cursor)

    out: dict[str, Any] = {}
    for k, sl in site_lists.items():
        out[k] = {
            "c_type": c_types.get(k, ""),
            "sites": sorted(sl, key=lambda s: (s["line"], s["role"])),
        }
    return out


def count_variables(filename: str) -> Counter:
    _ensure_clang()
    index = Index.create()

    args = clang_parse_args()
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


def function_return_types(filename: str) -> dict[str, str]:
    """
    Maps each function defined in the main file to its C return type spelling (as clang reports it).
    Used as input for LLM / tenjin `fn_return_type` guidance (Rust types are inferred separately).
    """
    _ensure_clang()
    index = Index.create()

    args = clang_parse_args()
    tu = index.parse(filename, args=args)
    if tu.diagnostics:
        print("=== clang diagnostics ===")
        for d in tu.diagnostics:
            print(d)
        print("=========================")
    out: dict[str, str] = {}

    main_file = Path(tu.spelling).resolve()

    def in_main_file(cur: Cursor) -> bool:
        if not cur.location.file:
            return False
        try:
            return Path(cur.location.file.name).resolve() == main_file
        except OSError:
            return False

    def visit(node: Cursor) -> None:
        if (
            node.kind == CursorKind.FUNCTION_DECL
            and in_main_file(node)
            and node.is_definition()
        ):
            name = node.spelling
            if name:
                out[name] = node.result_type.spelling
        for child in node.get_children():
            visit(child)

    visit(tu.cursor)
    return out

if __name__ == "__main__":
    # Only runs when you execute: python src/variable_counts.py
    sample = (Path(__file__).resolve().parent / ".." / "c_samples" / "02_gcd_lcm.c").resolve()
    print("Parsing:", sample)
    print("variable counts:", count_variables(str(sample)))
    print("function return types:", function_return_types(str(sample)))