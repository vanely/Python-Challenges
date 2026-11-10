# Step 1 — Request, response, router

**Checkpoint:** from `student/`, `uv run pytest ../checkpoints/test_microasgi.py -k "compile_path or routing or body_json"`

```bash
uv init --package student
cd student
```

Use a src layout (`src/microasgi`). Pytest adds `src/` when you run it from `student/`. The spec is the numbered list in `README.md`. This step is items 1–4, enough to serve a routed HTTP request.

The tests construct `App`, `Route`, `Router`, `Request`, `JSONResponse`, `PlainTextResponse` and call `compile_path` from `microasgi.routing`. Match those names. `client` in `microasgi.testclient` is how a test calls the app without a socket.

Don't open `reference/microasgi/src` until the whole checkpoint file is green.

## Explain it back

1. Why is `body()` cached, and what happens on a second read if it isn't?
