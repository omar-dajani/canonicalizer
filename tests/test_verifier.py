from pathlib import Path

import pytest
from slimconfig import build_output, plain_output

import verifier
from contract import TASKS, TOOLS, CanonicalizeInput, Task, Tool
from plugin import canonicalize_code, reference_canonicalize

SOURCE = "def add(a, b):\n    total = a + b\n    return total\n\nresult = add(1, 2)\n"


def verify_input(tool, value):
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_output(tool, source, output):
    given, made = TOOLS[Tool(tool)]
    return verifier.verify_output(tool, build_output({"source": source}, given), build_output(output, made), ".")


def verify_task(source, output, reference):
    given, made = TASKS[Task.CANONICALIZE_SNIPPET]
    return verifier.verify_task(
        "canonicalize-snippet",
        build_output({"source": source}, given),
        build_output(output, made),
        None if reference is None else build_output(reference, made),
        ".",
    )


@pytest.fixture
def answer():
    return plain_output(canonicalize_code(CanonicalizeInput(source=SOURCE), Path(".")))


def test_accepts_a_correct_answer(answer):
    reference = plain_output(reference_canonicalize(CanonicalizeInput(source=SOURCE), Path(".")))
    assert verify_task(SOURCE, answer, reference)["valid"] is True
    assert verify_output("canonicalize_code", SOURCE, answer)["valid"] is True
    assert verify_output("reference_canonicalize", SOURCE, reference)["valid"] is True


def test_the_same_answer_always_gets_the_same_verdict(answer):
    assert verify_task(SOURCE, answer, answer) == verify_task(SOURCE, answer, answer)


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"canonical_code": "def func_0(var_0, var_1):\n    return var_0"}, "canonical_code"),
        ({"node_count": 1}, "node_count"),
        ({"functions": []}, "functions"),
    ],
)
def test_refuses_an_answer_that_differs_from_the_reference(answer, changes, field):
    verdict = verify_task(SOURCE, answer | changes, answer)
    assert verdict["valid"] is False
    assert 0.0 <= verdict["score"] < 1.0


def test_refuses_an_answer_that_misses_a_variable(answer):
    short = answer | {"variables": answer["variables"][:-1]}
    verdict = verify_task(SOURCE, short, answer)
    assert verdict["valid"] is False and "variables" in verdict["message"] or "var_3" in verdict["message"]


def test_refuses_names_numbered_out_of_order(answer):
    swapped = answer | {"variables": [answer["variables"][1], answer["variables"][0], *answer["variables"][2:]]}
    verdict = verify_output("canonicalize_code", SOURCE, swapped)
    assert verdict["valid"] is False and "numbered" in verdict["message"]


def test_refuses_a_rename_of_a_name_the_source_never_had(answer):
    invented = answer | {"variables": [{"original": "ghost", "canonical": "var_0"}, *answer["variables"][1:]]}
    assert verify_output("canonicalize_code", SOURCE, invented)["valid"] is False


def test_refuses_an_identifier_renamed_twice(answer):
    doubled = answer | {"variables": answer["variables"] + [{"original": "a", "canonical": "var_4"}]}
    verdict = verify_output("canonicalize_code", SOURCE, doubled)
    assert verdict["valid"] is False and "twice" in verdict["message"]


def test_refuses_empty_and_missing_output(answer):
    assert verify_output("canonicalize_code", SOURCE, answer | {"canonical_code": "  "})["valid"] is False
    assert verify_output("canonicalize_code", SOURCE, answer | {"node_count": 0})["valid"] is False
    assert verify_task(SOURCE, answer, None)["valid"] is False


def test_refuses_a_rename_missing_from_the_code(answer):
    gone = answer | {"canonical_code": "pass"}
    assert verify_output("canonicalize_code", SOURCE, gone)["valid"] is False


def test_checks_what_the_types_cannot_say():
    assert verify_input("canonicalize_code", {"source": "x = 1"})["valid"] is True
    assert verify_input("canonicalize_code", {"source": "  \n"})["valid"] is False
    assert verify_input("reference_canonicalize", {"source": ""})["valid"] is False
