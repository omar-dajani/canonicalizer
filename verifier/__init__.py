from contract import Task, Tool

from . import canonicalize

TOOLS = {
    Tool.CANONICALIZE_CODE: canonicalize,
    Tool.REFERENCE_CANONICALIZE: canonicalize,
}

TASKS = {
    Task.CANONICALIZE_SNIPPET: canonicalize.verify_task,
}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
