# Empty on purpose. pytest adds the directory containing this file to
# Python's import path before collecting any tests — that's the only
# thing making `from src...` work when running the plain `pytest`
# command. Without this, only `python -m pytest` (which adds the
# current folder to the path itself, as a side effect of `-m`) works;
# the bare `pytest` command does not. Do not delete this file even
# though it has no code in it.
