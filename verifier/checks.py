import re


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def token(name, text):
    return re.search(rf"(?<![\w.]){re.escape(name)}(?!\w)", text) is not None


def numbering_problem(renames, prefix):
    for index, rename in enumerate(renames):
        if rename.canonical != f"{prefix}_{index}":
            return f"{prefix} renames must be numbered {prefix}_0, {prefix}_1, ... in order; found {rename.canonical}"
        if not rename.original.isidentifier():
            return f"{rename.original!r} is not an identifier"
    return None
