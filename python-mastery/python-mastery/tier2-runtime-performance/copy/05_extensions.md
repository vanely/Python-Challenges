# Extensions: Cython vs Rust/PyO3, side by side

## The same function

**Cython** (`fastsum.pyx`):
```cython
# cython: language_level=3, boundscheck=False, wraparound=False
def dot(double[::1] a, double[::1] b) -> double:       # typed memoryviews, C-contiguous
    cdef Py_ssize_t i, n = a.shape[0]
    cdef double acc = 0.0
    with nogil:                                        # releases the GIL: threads scale
        for i in range(n):
            acc += a[i] * b[i]
    return acc
```
Build: `pip install cython` + `setup.py` with `cythonize("fastsum.pyx", annotate=True)` → `python setup.py build_ext --inplace`. Open `fastsum.html`: white lines = pure C, yellow = Python API calls. Your goal is a white inner loop.

**Rust / PyO3** (`src/lib.rs`):
```rust
use pyo3::prelude::*;
use numpy::PyReadonlyArray1;

#[pyfunction]
fn dot(py: Python<'_>, a: PyReadonlyArray1<f64>, b: PyReadonlyArray1<f64>) -> PyResult<f64> {
    let (a, b) = (a.as_slice()?, b.as_slice()?);
    Ok(py.allow_threads(|| a.iter().zip(b).map(|(x, y)| x * y).sum()))   // GIL released
}

#[pymodule]
fn fastsum(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(dot, m)?)
}
```
`Cargo.toml`: `[lib] crate-type = ["cdylib"]`, deps `pyo3 = { version = "0.22", features = ["extension-module"] }`, `numpy = "0.22"`.
`pyproject.toml`: `[build-system] requires = ["maturin>=1.5"] build-backend = "maturin"`; `[tool.maturin] features = ["pyo3/extension-module"]`.
Build: `maturin develop --release` (installs into the active venv) / `maturin build --release` (wheel).

## Decision table
| | Cython | PyO3 |
|---|---|---|
| Speeding up existing Python gradually | ✅ add `cdef` types incrementally | ❌ rewrite |
| Wrapping an existing C library | ✅ `cdef extern` | ✅ via `bindgen`/`cxx`, more work |
| Memory safety / fearless threads | ❌ you're writing C | ✅ |
| Build toolchain | C compiler | Rust toolchain (+ C compiler for some crates) |
| Maintainability of a large extension | mediocre | good |
| What new major libraries choose | rarely | pydantic-core, polars, ruff, uv, tokenizers, orjson, cryptography |

## Shipping wheels
`cibuildwheel` in CI: builds in manylinux containers (Linux), on macOS runners (universal2 or arm64+x86_64), and Windows. Config in `pyproject.toml`:
```toml
[tool.cibuildwheel]
build = "cp312-* cp313-*"
skip = "*-musllinux_i686"
test-command = "pytest {project}/tests"
```
Consider `abi3-py312` (PyO3 feature `abi3-py312`) so one wheel per platform covers every 3.12+ version. Always publish the sdist too.

## Free-threading readiness
Cython: `# cython: freethreading_compatible = True` (3.1+). PyO3: `#[pymodule(gil_used = false)]` (0.23+) after auditing shared state. Test under `python3.13t` with `pytest -p no:cacheprovider` and `PYTHON_GIL=0`.
