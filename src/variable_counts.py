from clang.cindex import Index, CursorKind
from collections import Counter

def count_variables(filename):
    index = Index.create()
    tu = index.parse(filename)
    
    counts = Counter()
    
    def visit(node):
        # Variable declarations
        if node.kind == CursorKind.VAR_DECL:
            counts[(node.spelling, node.type.spelling)] += 1
        # References to variables (every time you use one)
        elif node.kind == CursorKind.DECL_REF_EXPR:
            ref = node.referenced
            if ref and ref.kind == CursorKind.VAR_DECL:
                counts[(node.spelling, node.type.spelling)] += 1
        
        for child in node.get_children():
            visit(child)
    
    visit(tu.cursor)
    return counts

# results = count_variables("../c_samples/02_gcd_lcm.c")
# for name, count in results.most_common():
#     print(f"{name}: {count}")