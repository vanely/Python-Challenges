//! logparse_rs::_native — parse an access log and aggregate per (status, endpoint).
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::{HashMap, HashSet};
use std::fs;

#[derive(Default)]
struct Agg {
    lats: Vec<u32>,
    users: HashSet<String>,
}

fn parse_line(line: &str) -> Option<(u16, &str, &str, u32)> {
    // "<ts> <status> <endpoint> user=<u> latency_ms=<n>"
    let mut it = line.split(' ');
    let _ts = it.next()?;
    let status: u16 = it.next()?.parse().ok()?;
    let ep = it.next()?;
    let user = it.next()?.strip_prefix("user=")?;
    let lat: u32 = it.next()?.strip_prefix("latency_ms=")?.trim_end().parse().ok()?;
    Some((status, ep, user, lat))
}

fn aggregate_str(text: &str) -> HashMap<(u16, String), Agg> {
    let mut map: HashMap<(u16, String), Agg> = HashMap::new();
    for line in text.lines() {
        if let Some((status, ep, user, lat)) = parse_line(line) {
            let e = map.entry((status, ep.to_owned())).or_default();
            e.lats.push(lat);
            if !e.users.contains(user) {
                e.users.insert(user.to_owned());
            }
        }
    }
    map
}

/// aggregate(path) -> dict[str, dict[str, int | float]]
/// Keys are "status|endpoint"; values have count, mean, p95, unique_users, rank.
#[pyfunction]
fn aggregate(py: Python<'_>, path: &str) -> PyResult<Py<PyAny>> {
    let text = fs::read_to_string(path)?;
    // Everything below is pure Rust: detach from the interpreter (release the GIL) so other Python threads can run.
    let mut rows: Vec<(u16, String, usize, f64, u32, usize)> = py.detach(|| {
        let map = aggregate_str(&text);
        map.into_iter()
            .map(|((status, ep), mut a)| {
                a.lats.sort_unstable();
                let n = a.lats.len();
                let mean = a.lats.iter().map(|&x| x as f64).sum::<f64>() / n as f64;
                let p95 = a.lats[((n - 1) as f64 * 0.95) as usize];
                (status, ep, n, mean, p95, a.users.len())
            })
            .collect()
    });
    rows.sort_by(|a, b| b.2.cmp(&a.2));
    let out = PyDict::new(py);
    for (rank, (status, ep, count, mean, p95, uniq)) in rows.into_iter().enumerate() {
        let d = PyDict::new(py);
        d.set_item("status", status)?;
        d.set_item("endpoint_len", ep.len())?;
        d.set_item("count", count)?;
        d.set_item("mean", mean)?;
        d.set_item("p95", p95)?;
        d.set_item("unique_users", uniq)?;
        d.set_item("rank", rank + 1)?;
        out.set_item(format!("{status}|{ep}"), d)?;
    }
    Ok(out.into_any().unbind())
}

// PyO3 >= 0.28 defaults to gil_used = false; opt out until exercise 3 audits the module.
#[pymodule(gil_used = true)]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(aggregate, m)?)?;
    Ok(())
}
