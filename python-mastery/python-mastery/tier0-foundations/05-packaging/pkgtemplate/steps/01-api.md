# The functions the package exports

**Checkpoint:** from this directory, `uv sync && uv run pytest checkpoints tests`

`pyproject.toml`, `noxfile.py`, and `.github/workflows/` stay in this folder because reading and retyping them is the packaging lesson. The function bodies do not. `src/pkgtemplate/core.py` raises `NotImplementedError` until you fill it in. `reference/pkgtemplate/` is a finished copy of the whole package; open it after the checkpoint is green.

## Your turn

`slugify(text, *, sep="-")`: lowercase, collapse every run of characters that aren't `a-z` or `0-9` into a single `sep`, and strip `sep` from both ends. `"Hello, World!"` → `hello-world`. `"  a  b "` → `a-b`.

`greet(name)`: `Hello, {name}!`

`old_greet(name)`: the same string, and a `DeprecationWarning` (so `pytest.deprecated_call` sees it) whose message says it is deprecated. `stacklevel` must point at the caller, not at `old_greet`.

`__init__.py` already re-exports `__version__`, `greet`, and `slugify`. `__version__` comes from hatch-vcs (`src/pkgtemplate/_version.py`, generated, gitignored). Don't hand-write a version string.

## Explain it back

1. Why is `_version.py` generated and gitignored instead of committed?
2. What does `stacklevel=2` change about who the warning blames?
