# logparse_rs — Rust/PyO3 extension scaffold (unbuilt here; build locally)

```bash
curl https://sh.rustup.rs -sSf | sh          # once
uv pip install maturin pytest
cd rust-ext
maturin develop --release                     # builds and installs into the active venv
pytest
python -c "import logparse_rs; print(logparse_rs.aggregate('../../tier0-foundations/04-profiling/lab/access.log'))"
```

Layout: mixed Rust/Python project — `src/lib.rs` is the native module (`logparse_rs._native`), `python/logparse_rs/__init__.py` is the typed Python façade with a `.pyi`-free approach (types declared in Python). CI builds wheels with `cibuildwheel` for Linux/macOS/Windows × 3.12/3.13 and uploads them as artifacts; wire the release job to PyPI exactly as in Tier 0.5.

Exercises once it builds:
1. Add `rayon` and parallelise line parsing (`read_to_string` → `par_lines()`), wrap in `py.allow_threads`. Measure.
2. Return a `polars`-consumable columnar result (`Vec<u16>`, `Vec<String>`, …) instead of a dict and compare conversion cost.
3. Make the module free-threading compatible: `#[pymodule(gil_used = false)]`, run tests under `python3.13t`.
4. Switch to `abi3-py312` and check the wheel filename.
