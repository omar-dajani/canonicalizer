# AST Identifier Canonicalizer

A `nanoagent.plugin/v0001` plugin, created by `nanoagent plugin new` with the
structure of NanoAgent's reference plugin,
[arxiv-source](https://github.com/zeyuyang8/arxiv-source).

## Tools

| Tool | Does | Code |
|---|---|---|
| `canonicalize_code` | Renames every user-defined variable and function in a Python snippet to `var_<n>` and `func_<n>`, numbered by first appearance, and checks the syntax tree has the same node types before and after | `src/plugin/canonicalize.py` |
| `reference_canonicalize` | The reference answer for the task: the same rules written a second way (a visitor and a transformer instead of one walk), so the two can be compared. The agent is not given it | `src/plugin/reference.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `canonicalize-snippet` | Canonicalizes a Python snippet's identifiers | `agent`, with `canonicalize_code` |

Variables, parameters, exception and pattern names become `var_<n>`; a name
that is ever defined with `def` becomes `func_<n>`. Numbers start at 0 and
follow the position of each name's first appearance in the source. Classes,
imports, attributes, keyword names, builtins and dunder names keep their names.
A snippet that is not valid Python, or that already uses a `var_<n>` or
`func_<n>` name the plugin would not rename, is an error.

The verifier cannot import `ast`, so it cannot canonicalize a snippet itself.
`verifier/canonicalize.py` checks what plain text can say (renames are numbered
in order, each original name occurs in the source, each canonical name occurs in
the code) and `verify_task` compares the submitted output field by field with
`reference_canonicalize`'s, which NanoAgent pins before the agent starts.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs, never values
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, and the plugin's own modules
├── tests/
├── ui/              # how the page draws the outputs: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
```

NanoAgent passes the folder the plugin may write to as `NANOAGENT_WORKSPACE`.
This plugin writes nothing there.
