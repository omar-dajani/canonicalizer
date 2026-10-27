from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    CANONICALIZE_CODE = "canonicalize_code"
    REFERENCE_CANONICALIZE = "reference_canonicalize"


class Task(Enum):
    CANONICALIZE_SNIPPET = "canonicalize-snippet"


@dataclass
class Rename(Output):
    original: Annotated[str, "The identifier as written in the snippet"]
    canonical: Annotated[str, "The identifier that replaced it: var_<n> for a variable, func_<n> for a function"]


@dataclass
class CanonicalizeInput(Output):
    source: Annotated[str, "A syntactically valid Python snippet"]


@dataclass
class CanonicalizeOutput(Output):
    canonical_code: Annotated[
        str, "The snippet with every user-defined variable and function renamed, as ast.unparse prints it"
    ]
    variables: Annotated[list[Rename], "Every renamed variable, in order of first appearance: var_0, var_1, ..."]
    functions: Annotated[list[Rename], "Every renamed function, in order of first appearance: func_0, func_1, ..."]
    node_count: Annotated[int, "How many AST nodes the snippet has, before and after renaming"]


TOOLS = {
    Tool.CANONICALIZE_CODE: (CanonicalizeInput, CanonicalizeOutput),
    Tool.REFERENCE_CANONICALIZE: (CanonicalizeInput, CanonicalizeOutput),
}
TASKS = {
    Task.CANONICALIZE_SNIPPET: (CanonicalizeInput, CanonicalizeOutput),
}
