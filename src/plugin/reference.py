import ast
import re
from pathlib import Path

from contract import CanonicalizeInput, CanonicalizeOutput, Rename


class Scan(ast.NodeVisitor):
    def __init__(self):
        self.first = {}
        self.bound = set()
        self.defined = set()
        self.external = set()

    def note(self, node, name, binds=False):
        key = (node.lineno, node.col_offset, name)
        if name not in self.first or key < self.first[name]:
            self.first[name] = key
        if binds:
            self.bound.add(name)

    def visit_Name(self, node):
        self.note(node, node.id, not isinstance(node.ctx, ast.Load))

    def visit_arg(self, node):
        self.note(node, node.arg, True)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.note(node, node.name, True)
        self.defined.add(node.name)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.external.add(node.name)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.external.add(alias.asname or alias.name.split(".")[0])

    visit_ImportFrom = visit_Import

    def visit_ExceptHandler(self, node):
        if node.name:
            self.note(node, node.name, True)
        self.generic_visit(node)

    def visit_Global(self, node):
        for name in node.names:
            self.note(node, name)

    visit_Nonlocal = visit_Global

    def visit_MatchAs(self, node):
        if node.name:
            self.note(node, node.name, True)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        if node.rest:
            self.note(node, node.rest, True)
        self.generic_visit(node)


class Swap(ast.NodeTransformer):
    def __init__(self, table):
        self.table = table

    def visit_Name(self, node):
        node.id = self.table.get(node.id, node.id)
        return node

    def visit_arg(self, node):
        node.arg = self.table.get(node.arg, node.arg)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.name = self.table.get(node.name, node.name)
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ExceptHandler(self, node):
        if node.name:
            node.name = self.table.get(node.name, node.name)
        return self.generic_visit(node)

    visit_MatchAs = visit_ExceptHandler

    def visit_MatchStar(self, node):
        node.name = self.table.get(node.name, node.name) if node.name else None
        return node

    def visit_MatchMapping(self, node):
        if node.rest:
            node.rest = self.table.get(node.rest, node.rest)
        return self.generic_visit(node)

    def visit_Global(self, node):
        node.names = [self.table.get(name, name) for name in node.names]
        return node

    visit_Nonlocal = visit_Global


def reference_canonicalize(given: CanonicalizeInput, workspace: Path) -> CanonicalizeOutput:
    try:
        tree = ast.parse(given.source)
    except (SyntaxError, ValueError) as error:
        raise ValueError(f"source is not valid Python: {error}") from error
    scan = Scan()
    scan.visit(tree)
    names = sorted(
        (name for name in scan.bound if name not in scan.external and not re.fullmatch(r"__\w+__", name)),
        key=lambda name: scan.first[name],
    )
    functions = [name for name in names if name in scan.defined]
    variables = [name for name in names if name not in scan.defined]
    table = {name: f"func_{index}" for index, name in enumerate(functions)}
    table.update({name: f"var_{index}" for index, name in enumerate(variables)})
    untouched = set(scan.first) - set(table)
    taken = untouched & set(table.values())
    if taken:
        raise ValueError(f"source already uses the canonical name {min(taken)} for something it does not rename")
    count = sum(1 for _ in ast.walk(tree))
    code = ast.unparse(Swap(table).visit(tree))
    return CanonicalizeOutput(
        canonical_code=code,
        variables=[Rename(original=name, canonical=table[name]) for name in variables],
        functions=[Rename(original=name, canonical=table[name]) for name in functions],
        node_count=count,
    )
