# Tier 5 — Teach it (ongoing)

If you can't write the explainer, you don't own the concept yet. Three briefs. Each is a ~1500–2500-word post (or a 20-minute talk) written for the engineer you were before Tier 0: production Django, competitive-programming Python, no idea what a descriptor is.

## Standard for every piece
- Opens with a concrete bug or surprise the reader has probably hit, not a definition.
- Every claim is demonstrable: a runnable snippet under 15 lines with its actual output.
- One diagram (draw it — attribute lookup order, the cancellation state machine, the GIL handoff).
- Ends with "what to do differently on Monday": 3 bullets.
- A "further down" section pointing at the CPython source file and line for the mechanism.
- Get it reviewed by someone who knows the topic (post it; a Reddit `r/Python` or discuss.python.org critique is worth a lot).

## Brief 1 — "What `Model.objects` actually is"
Descriptors, from Django's point of view. Cover: the lookup order (`type(obj).__mro__` data descriptors → instance dict → non-data descriptors); why `objects` is class-only (`ManagerDescriptor.__get__` raising on instance); how `DeferredAttribute` makes `.only()` lazy; why `@property` and `@functools.cached_property` behave differently on assignment (data vs non-data); `__set_name__`. Demo: your Tier 0 `tinyorm` field in 20 lines. Monday: stop reaching for `__getattr__` when a descriptor is the right tool.

## Brief 2 — "The GIL is not why your service is slow (and when it is)"
What the GIL protects (refcounts, interpreter state); the switch interval and `sys.setswitchinterval`; I/O releases it, C extensions may release it, pure Python never does; convoy effect; why threads still help for I/O and hurt for CPU; free-threaded 3.13t/3.14t — what changes (per-object locks, biased refcounting, specialisation impact), what breaks (data races in code that was accidentally safe), measured numbers from your Tier 2 experiment. Monday: use the decision table — `to_thread` for blocking I/O, process pool or native for CPU, measure before choosing.

## Brief 3 — "Cancellation is a message, not a kill"
`Task.cancel()` schedules a `CancelledError` at the next `await`; code between awaits can't be interrupted; `try/finally` and `async with` run on the way out; swallowing `CancelledError` breaks `TaskGroup` and `timeout`; `asyncio.shield` and when it's a footgun; edge- vs level-triggered (asyncio vs Trio) with the `uncancel()` counter; graceful SIGTERM shutdown pattern from Tier 0.3; what *can't* be cancelled (running executor futures). Monday: never `except Exception` around an `await` without re-raising `CancelledError`… and know that `CancelledError` is a `BaseException` since 3.8 for exactly this reason.

## After the three
Pick the next hardest thing you learned (import system, `__slots__` memory layout, `contextvars` across executors, `TaskGroup` vs `gather` error semantics) and repeat. When a colleague asks you a Python question and your answer includes "here's the line in CPython where that happens," you're done with the curriculum. Everything after is practice.
