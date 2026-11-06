"""Day 9 — pathlib and file I/O."""
import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    print(root.exists(), root.is_dir())

    # building paths
    data = root / "data" / "2026"
    data.mkdir(parents=True, exist_ok=True)
    f = data / "report.json"
    print(f.name, f.stem, f.suffix, f.parent.name, f.parts[-3:])
    print(f.with_suffix(".bak").name, f.with_name("other.txt").name)

    # writing / reading
    f.write_text('{"ok": true}\n', encoding="utf-8")
    print(f.read_text(encoding="utf-8").strip(), f.stat().st_size, "bytes")
    with f.open("a", encoding="utf-8") as fh:
        fh.write("// appended\n")
    print(f.read_text(encoding="utf-8").splitlines())

    # line-by-line (lazy — fine for huge files)
    with f.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            print(n, line.rstrip())

    # globbing
    for i in range(3):
        (data / f"part{i}.csv").write_text("a,b\n1,2\n")
    (root / "notes.md").write_text("# hi")
    print(sorted(p.name for p in data.glob("*.csv")))
    print(sorted(p.relative_to(root).as_posix() for p in root.rglob("*")))
    print([p.name for p in root.iterdir()])

    # copy / move / delete
    shutil.copy(f, root / "copy.json")
    (root / "copy.json").rename(root / "moved.json")
    (root / "moved.json").unlink()
    shutil.rmtree(data)
    print(sorted(p.name for p in root.iterdir()))

    # binary
    b = root / "blob.bin"
    b.write_bytes(bytes(range(8)))
    print(b.read_bytes().hex())

# --- datetime: always timezone-aware -------------------------------------------------------------
now = datetime.now(UTC)
ny = now.astimezone(ZoneInfo("America/New_York"))  # Windows: needs `tzdata` (uv run --with tzdata)
print(now.isoformat(), "|", ny.strftime("%Y-%m-%d %H:%M %Z"))
print(datetime.fromisoformat("2026-09-11T10:00:00+00:00") + timedelta(days=1, hours=2))
print((now - datetime(2026, 1, 1, tzinfo=UTC)).days, "days since new year")
naive = datetime(2026, 9, 11)          # no tzinfo — avoid mixing with aware values
print(naive.tzinfo is None)
