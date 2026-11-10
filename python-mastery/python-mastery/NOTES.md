# Stage 3 notes

Answer these in this file, under the heading, before you open that project's `reference/`. A sentence that only restates the README is not an answer.

## 0.1 tinyorm

1. Why is a field a data descriptor rather than a value stored on the class?
2. What does a metaclass give you that `__init_subclass__` does not? Which one would you ship, after you try both?
3. Why is an unsaved instance unhashable?
4. Why is the SQL still parameterised when the lookup name was built dynamically?

## 0.2 typed decorators

For each exercise you got wrong the first time: the mypy error, and the rung of the decorator ladder it belongs to.

## 0.3 fetchd

1. Why does `TokenBucket` take `clock` and `sleep`?
2. Which failures are `FetchResult`s, and which are allowed to cancel the `TaskGroup`?
3. Why isn't the semaphore a substitute for the token bucket?
4. Write the shutdown order you implemented, including the Windows fallback.

## 0.4 profiling

Numbers and the "why" belong in `tier0-foundations/04-profiling/lab/REPORT.md`. Here: which of your predictions about v0 were wrong, and what you measured instead.

## 0.5 packaging

1. After `uv build`, what is in `*.dist-info/`, and which `pyproject.toml` key produced each file?
2. Why is `_version.py` generated instead of committed?
3. What did `stacklevel=2` change about the deprecation warning?

## Tier 1

One thing per chapter you would previously have got wrong. For `vector.py`: did you register it with `numbers.Real`, and why?

## Tier 2

`rust-ext`: the signature of the aggregate function, written before you read `src/lib.rs`. After you measure: which version you would run in production, counting build and deploy cost.

## Tier 3 microasgi

1. Line count versus Starlette, and which features you skipped.
2. The one design decision you would argue with Starlette about.
3. What `root_path` is for.

## Tier 3 mixed-executor

There is no reference implementation.

1. Why is `fork` the wrong start method once threads exist, and what did 3.14 change?
2. Show the test that proves `to_thread` copies context and `run_in_executor` does not.
3. The shutdown order you observed, and what a cancelled `/hash` does to the worker process.
