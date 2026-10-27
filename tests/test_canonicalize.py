from pathlib import Path

import pytest

from contract import CanonicalizeInput
from plugin import canonicalize_code, reference_canonicalize

SNIPPETS = [
    "x = 1\ny = x + 2\nprint(y)\n",
    "def add(a, b):\n    total = a + b\n    return total\n\nresult = add(1, 2)\n",
    "import os\nfrom math import sqrt\n\ndef norm(v):\n    return sqrt(sum(c * c for c in v))\n\nprint(os.getcwd(), norm([3, 4]))\n",
    "class Box:\n    def __init__(self, item):\n        self.item = item\n\n    def get(self):\n        return self.item\n\nbox = Box(3)\nbox.get()\n",
    "try:\n    risky()\nexcept ValueError as err:\n    print(err)\n",
    "def outer():\n    count = 0\n    def bump():\n        nonlocal count\n        count += 1\n    bump()\n    return count\n",
    "match point:\n    case (x, y):\n        print(x, y)\n    case {'k': v, **rest}:\n        print(v, rest)\n    case [first, *others]:\n        print(first, others)\n",
    "squares = [n * n for n in range(10) if n % 2]\nlookup = {k: v for k, v in zip('ab', 'cd')}\nfn = lambda q: q + 1\n",
    "async def fetch(url):\n    data = await get(url)\n    return data\n",
    "if (m := compute()) is not None:\n    print(m)\n",
    "__all__ = ['a']\na = 1\n",
]


def run(source):
    return canonicalize_code(CanonicalizeInput(source=source), Path("."))


def test_renames_variables_and_functions_by_first_appearance():
    made = run("def add(a, b):\n    total = a + b\n    return total\n\nresult = add(1, 2)\n")
    assert (
        made.canonical_code
        == "def func_0(var_0, var_1):\n    var_2 = var_0 + var_1\n    return var_2\nvar_3 = func_0(1, 2)"
    )
    assert [(r.original, r.canonical) for r in made.functions] == [("add", "func_0")]
    assert [(r.original, r.canonical) for r in made.variables] == [
        ("a", "var_0"),
        ("b", "var_1"),
        ("total", "var_2"),
        ("result", "var_3"),
    ]


def test_two_snippets_that_differ_only_in_names_come_out_identical():
    first = run("def f(a):\n    b = a * 2\n    return b\n")
    second = run("def area(width):\n    doubled = width * 2\n    return doubled\n")
    assert first.canonical_code == second.canonical_code
    assert first.node_count == second.node_count


def test_names_that_are_not_user_defined_are_kept():
    made = run(
        "import os\nfrom math import sqrt\n\nclass Box:\n    pass\n\nprint(os.getcwd(), sqrt(4), Box())\n__all__ = []\n"
    )
    assert made.variables == [] and made.functions == []
    assert "os.getcwd()" in made.canonical_code and "sqrt(4)" in made.canonical_code and "Box()" in made.canonical_code
    assert "__all__" in made.canonical_code


def test_attributes_and_keyword_names_are_not_renamed():
    made = run("point = Point(x=1)\nx = point.x\n")
    assert made.canonical_code == "var_0 = Point(x=1)\nvar_1 = var_0.x"


def test_node_count_is_the_size_of_the_tree():
    assert run("x = 1").node_count == 5
    assert run("pass").node_count == 2


def test_empty_source_is_a_valid_boundary():
    made = run("")
    assert made.canonical_code == "" and made.node_count == 1


@pytest.mark.parametrize("source", ["def broken(:\n    pass", "x = = 1", "print('unterminated", "\x00"])
def test_invalid_python_is_rejected(source):
    with pytest.raises(ValueError, match="not valid Python"):
        run(source)
    with pytest.raises(ValueError, match="not valid Python"):
        reference_canonicalize(CanonicalizeInput(source=source), Path("."))


def test_a_clash_with_a_canonical_name_is_rejected():
    with pytest.raises(ValueError, match="var_0"):
        run("x = var_0\n")


@pytest.mark.parametrize("source", SNIPPETS)
def test_both_implementations_agree(source):
    assert run(source) == reference_canonicalize(CanonicalizeInput(source=source), Path("."))
