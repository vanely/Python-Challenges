# logparse_rs — Rust/PyO3 extension scaffold (unbuilt here; build locally)

This directory is the baseline you extend (parallel parse, columnar output, free-threading, abi3). It is not hidden under `reference/`, because the lesson starts by building and measuring this scaffold. Read `tests/test_native.py` and write down the function signature in `NOTES.md` before you read `src/lib.rs`.

```bash
winget install Rustlang.Rustup               # once, Windows (needs MSVC build tools); macOS/Linux: curl https://sh.rustup.rs -sSf | sh
uv pip install maturin pytest
cd rust-ext
maturin develop --release                     # builds and installs into the active venv
pytest
python -c "import logparse_rs; print(logparse_rs.aggregate('../../tier0-foundations/04-profiling/lab/access.log'))"
```

Layout: mixed Rust/Python project — `src/lib.rs` is the native module (`logparse_rs._native`), `python/logparse_rs/__init__.py` is the typed Python façade, and `python/logparse_rs/_native.pyi` types the native module so `mypy --strict` passes on the façade. CI builds wheels with `cibuildwheel` for Linux/macOS/Windows × 3.12/3.13 and uploads them as artifacts; wire the release job to PyPI exactly as in Tier 0.5.

Exercises once it builds:
1. Add `rayon` and parallelise line parsing (`read_to_string` → `par_lines()`), wrap in `py.detach`. Measure.
2. Return a `polars`-consumable columnar result (`Vec<u16>`, `Vec<String>`, …) instead of a dict and compare conversion cost.
3. Make the module free-threading compatible: audit shared state, change `#[pymodule(gil_used = true)]` to `#[pymodule(gil_used = false)]` (PyO3 0.28, where `false` is the default and `lib.rs` opts out explicitly), run tests under `python3.13t` and check `sys._is_gil_enabled()` stays `False` with no `RuntimeWarning`.
4. Switch to `abi3-py312` and check the wheel filename.
