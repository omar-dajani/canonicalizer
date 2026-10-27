from .checks import numbering_problem, result, token


def fields(value):
    return {
        "canonical_code": value.canonical_code,
        "variables": value.variables,
        "functions": value.functions,
        "node_count": value.node_count,
    }


def verify_input(value):
    if not value.source.strip():
        return result(False, "source must not be blank")
    return result(True, "source accepted")


def shape_problem(value):
    for renames, prefix in ((value.variables, "var"), (value.functions, "func")):
        problem = numbering_problem(renames, prefix)
        if problem:
            return problem
    originals = [rename.original for rename in value.variables + value.functions]
    if len(set(originals)) != len(originals):
        return "an identifier is renamed twice"
    if not value.canonical_code.strip():
        return "canonical_code must not be blank"
    if value.node_count < 1:
        return "node_count must be positive"
    for rename in value.variables + value.functions:
        if not token(rename.canonical, value.canonical_code):
            return f"{rename.canonical} does not appear in canonical_code"
    return None


def verify_output(input_value, output_value, workspace):
    problem = shape_problem(output_value)
    if problem:
        return result(False, problem)
    for rename in output_value.variables + output_value.functions:
        if not token(rename.original, input_value.source):
            return result(False, f"{rename.original!r} does not occur in the source")
    return result(
        True, "canonicalization is well formed", renamed=len(output_value.variables) + len(output_value.functions)
    )


def verify_task(arguments, output, reference, workspace):
    problem = verify_input(arguments)
    if not problem["valid"]:
        return problem
    judged = verify_output(arguments, output, workspace)
    if not judged["valid"]:
        return judged
    if reference is None:
        return result(False, "no reference answer to compare with")
    given, expected = fields(output), fields(reference)
    wrong = [field for field in expected if given[field] != expected[field]]
    if wrong:
        score = 1 - len(wrong) / len(expected)
        return result(False, f"differs from the reference in {', '.join(wrong)}", score=score, wrong=wrong)
    return result(True, "matches the reference canonicalization", node_count=output.node_count)
