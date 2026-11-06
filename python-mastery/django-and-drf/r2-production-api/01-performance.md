# R2.01 — Query budgets for APIs

**Time:** ~2.5 h · **Checkpoint:** `uv run pytest ../checkpoints/r2/test_r2_01_performance.py`

## What you'll have at the end

- Tests that fail if the issue list's query count grows with the number of issues.
- A project list that includes each project's open-issue count, computed in the same SQL query.

## Concepts

### Serializers are templates in disguise

Everything from D2.02 applies: a serializer touching `issue.assignee.username` or `issue.labels.all()` for each item in a list is a template loop. The difference is visibility. Nobody "looks at" JSON the way they look at a slow page, so API N+1s survive much longer. **Query-count tests are the only reliable defence.**

### Where the queries come from in a DRF list request

For `GET /api/projects/apollo/issues/` with token auth:
1. authentication: look up the token row and its user (`select_related("user")` inside DRF: 1 query);
2. `self.project`: 1 query (the membership-scoped project);
3. pagination: `SELECT COUNT(*)`: 1;
4. the page of issues, with `select_related` JOINs: 1;
5. `prefetch_related("labels")`: 1.

That's **5 queries, whatever the page size**. The checkpoint authenticates with `force_authenticate` (no token query) and requires the count to be **equal** for 2 and 20 issues, and at most 5.

### `SerializerMethodField` is the usual N+1 source

```python
open_issue_count = serializers.SerializerMethodField()

def get_open_issue_count(self, project):
    return project.issues.open().count()       # one query per project in the list
```

It looks harmless, and it's a query per row. The fix is to **compute it in the queryset** with `annotate()` (D2.03) and expose the annotation as a plain read-only field:

```python
# view
.annotate(open_issue_count=Count("issues", filter=~Q(issues__status="closed")))
# serializer
open_issue_count = serializers.IntegerField(read_only=True)
```

The serializer just reads an attribute that's already on each instance.

**One subtlety:** after `POST /api/projects/`, the instance comes from `create_project`, not from the annotated queryset, so it has no `open_issue_count` attribute. DRF omits a read-only field whose attribute is missing (it raises `SkipField` internally), so the create response simply lacks that key. That's acceptable here because a new project has 0 open issues anyway. If clients need the field on every response, re-fetch the created object through `get_queryset()` in `perform_create`, or set the attribute explicitly.

### Avoid fetching what you don't render

- `only()`/`defer()` limit columns. They're useful for wide tables with big text fields that list views don't show. But touching a deferred field later costs one query *per instance*, so use them carefully.
- `values()`/`values_list()` skip model instantiation entirely. They're fast for exports, and lose model methods.
- For big exports, `.iterator(chunk_size=2000)` streams rows instead of caching them all. It doesn't combine with `prefetch_related` unless you pass `chunk_size`, and even then prefetching happens per chunk.

## Build

### 1. Your own budget test first

Before changing code, write `tests/test_api_queries.py`: for the **project** list, assert the query count is the same with 2 projects and with 20, each project having a few issues. Then add the `SerializerMethodField` version of `open_issue_count` above and watch your test fail. That's the point of writing it first.

### 2. Your turn: compute it in SQL

Replace the method field with an annotation in `ProjectViewSet.get_queryset()` and a read-only `IntegerField` on the serializer. Requirements:
- counts only issues that aren't closed;
- projects with zero issues show `0`, not `null`, and aren't dropped from the list;
- the project list stays at a constant query count (≤ 3 with `force_authenticate`).

<details><summary>Hint 1</summary>

`Count(..., filter=...)`. What does `Count` return for a project whose LEFT JOIN produced no issue rows?
</details>

<details><summary>Hint 2</summary>

The queryset already filters by `memberships__user`. You're counting a *different* relation (`issues`). Does D2.03's filter-then-annotate surprise apply? Think through how many membership rows remain per project after the filter.
</details>

### 3. Check the issue list

The issue list should already be at a constant count from R1.04. Run the checkpoint. If it fails, read the SQL: `CaptureQueriesContext` gives you `ctx.captured_queries[i]["sql"]`.

## Checkpoint

```bash
uv run pytest ../checkpoints/r2/test_r2_01_performance.py
```

## Pitfalls

- **`SerializerMethodField` that queries.**
- **Nested serializers** (`IssueSerializer(many=True)` inside `ProjectSerializer`) without a `Prefetch` in the view. That's N+1, and often N×M.
- **Asserting a fixed number** (`== 5`) with no comparison. It breaks for harmless reasons and doesn't say what's actually wrong. Compare counts at two sizes, plus an upper bound.
- **Optimising before measuring.** Write the budget test first, every time.

## Explain it back

1. List the queries of the issue list request, as in the Concepts section, with token auth instead of `force_authenticate`. How many are there?
2. Why is a `SerializerMethodField` that queries worse in an API than the same thing in a template?
3. Why does filtering by `memberships__user` not distort `Count("issues")`? Under what change to the domain would it start to?
