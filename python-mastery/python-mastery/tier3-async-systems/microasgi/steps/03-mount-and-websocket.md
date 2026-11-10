# Step 3 — Mount, root_path, websockets

**Checkpoint:** from `student/`, `uv run pytest ../checkpoints`

README items 4 (Mount) and 7–8.

- `Mount` appends its prefix to `root_path` and leaves `path` as the full request target. Routing matches `path` minus `root_path`, so `uvicorn --root-path` works. `get_route_path` is the helper the tests import.
- `WebSocket` supports `accept`, `receive_text`, `send_text`, `close`, and raises `WebSocketDisconnect`. `WebSocketTester` drives it without a server.

## Finish

The checkpoint file is green, `mypy --strict` is clean on `src`, and `NOTES.md` has the three prompts at the bottom of `README.md`. Then diff `reference/microasgi/src`.

## Explain it back

1. What is `root_path` for, and why must Mount not rewrite `path`?
