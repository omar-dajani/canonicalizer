import ast
import re
from pathlib import Path

from contract import CanonicalizeInput, CanonicalizeOutput, Rename

DUNDER = re.compile(r"__\w+__")


def parse(source: str) -> ast.Module:
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError) as error:
        raise ValueError(f"source is not valid Python: {error}") from error


def sightings(tree: ast.Module) -> list[tuple[int, int, str, str]]:
    found = []
    for node in ast.walk(tree):
        match node:
            case ast.Name():
                found.append(
                    (node.lineno, node.col_offset, node.id, "use" if isinstance(node.ctx, ast.Load) else "bind")
                )
            case ast.arg():
                found.append((node.lineno, node.col_offset, node.arg, "bind"))
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                found.append((node.lineno, node.col_offset, node.name, "def"))
            case ast.ExceptHandler() | ast.MatchAs() | ast.MatchStar() if node.name:
                found.append((node.lineno, node.col_offset, node.name, "bind"))
            case ast.MatchMapping() if node.rest:
                found.append((node.lineno, node.col_offset, node.rest, "bind"))
            case ast.Global() | ast.Nonlocal():
                found.extend((node.lineno, node.col_offset, name, "use") for name in node.names)
    return found


def external_names(tree: ast.Module) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update((alias.asname or alias.name.split(".")[0]) for alias in node.names)
    return names


def rename_table(tree: ast.Module) -> tuple[dict[str, str], list[str], list[str]]:
    found = sightings(tree)
    skip = external_names(tree)
    bound = {name for _, _, name, role in found if role != "use" and name not in skip and not DUNDER.fullmatch(name)}
    defined = {name for _, _, name, role in found if role == "def"} & bound
    order = list(dict.fromkeys(name for _, _, name, _ in sorted(found) if name in bound))
    functions = [name for name in order if name in defined]
    variables = [name for name in order if name not in defined]
    table = {name: f"func_{i}" for i, name in enumerate(functions)}
    table |= {name: f"var_{i}" for i, name in enumerate(variables)}
    clash = {name for _, _, name, _ in found if name not in table} & set(table.values())
    if clash:
        raise ValueError(f"source already uses the canonical name {min(clash)} for something it does not rename")
    return table, variables, functions


def apply_table(tree: ast.Module, table: dict[str, str]) -> None:
    for node in ast.walk(tree):
        match node:
            case ast.Name():
                node.id = table.get(node.id, node.id)
            case ast.arg():
                node.arg = table.get(node.arg, node.arg)
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                node.name = table.get(node.name, node.name)
            case ast.ExceptHandler() | ast.MatchAs() | ast.MatchStar() if node.name:
                node.name = table.get(node.name, node.name)
            case ast.MatchMapping() if node.rest:
                node.rest = table.get(node.rest, node.rest)
            case ast.Global() | ast.Nonlocal():
                node.names = [table.get(name, name) for name in node.names]


def node_types(tree: ast.AST) -> list[str]:
    return [type(node).__name__ for node in ast.walk(tree)]


def canonicalize_code(given: CanonicalizeInput, workspace: Path) -> CanonicalizeOutput:
    original = parse(given.source)
    table, variables, functions = rename_table(original)
    renamed = parse(given.source)
    apply_table(renamed, table)
    code = ast.unparse(renamed)
    before = node_types(original)
    if node_types(parse(code)) != before:
        raise ValueError("renaming changed the structure of the syntax tree")
    return CanonicalizeOutput(
        canonical_code=code,
        variables=[Rename(original=name, canonical=table[name]) for name in variables],
        functions=[Rename(original=name, canonical=table[name]) for name in functions],
        node_count=len(before),
    )
