"""Day 9 — subprocess, json, csv."""
import csv
import io
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

# --- subprocess ------------------------------------------------------------------------------
r = subprocess.run(["python3", "-c", "print('hi'); import sys; print('err', file=sys.stderr)"],
                   capture_output=True, text=True, check=True, timeout=10)
print(repr(r.stdout), repr(r.stderr), r.returncode)

try:
    subprocess.run(["python3", "-c", "raise SystemExit(3)"], check=True)
except subprocess.CalledProcessError as e:
    print("failed with", e.returncode)

try:
    subprocess.run(["definitely-not-a-command"])
except FileNotFoundError as e:
    print("missing binary:", e.filename)

# --- json --------------------------------------------------------------------------------------
@dataclass
class Order:
    id: int
    total: Decimal
    placed: datetime


def encode(o: object) -> Any:                     # json.dumps(default=...)
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(f"cannot serialise {type(o).__name__}")


order = Order(1, Decimal("19.99"), datetime.now(UTC))
text = json.dumps(asdict(order), default=encode, indent=2)
print(text)
back = json.loads(text)
print(type(back), back["total"], type(back["total"]))     # strings come back as strings


def decode(d: dict[str, Any]) -> dict[str, Any]:  # json.loads(object_hook=...)
    if "placed" in d:
        d["placed"] = datetime.fromisoformat(d["placed"])
    return d


print(json.loads(text, object_hook=decode)["placed"].year)
print(json.dumps({"b": 1, "a": [None, True, 1.5]}, sort_keys=True))   # null/true/1.5

# --- csv --------------------------------------------------------------------------------------
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["sku", "qty", "price"])
w.writeheader()
w.writerows([{"sku": "A1", "qty": 2, "price": "9.50"}, {"sku": "B2", "qty": 1, "price": "1,000.00"}])
print(buf.getvalue())

buf.seek(0)
for row in csv.DictReader(buf):                   # every value is a str
    print(row["sku"], int(row["qty"]) * Decimal(row["price"].replace(",", "")))

# real files: open(path, newline="", encoding="utf-8")
