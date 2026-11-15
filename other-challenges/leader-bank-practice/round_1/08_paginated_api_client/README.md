# Problem 8 — Paginated API Client with Retries

The bank pulls loan records from a vendor's REST API (picture Encompass). The API returns **one page at a time**, and it sometimes fails for a moment.

So that the code runs without the internet, you don't call HTTP yourself. Instead, you're handed a function:

```python
fetch_page(page_number) -> {"data": [...records...], "next_page": 2}   # or None on the last page
```

`fetch_page` can raise two kinds of errors:

| Error | Meaning | What to do |
|---|---|---|
| `TransientAPIError` | Timeout, HTTP 429/500/503: try again later | **Retry** with exponential backoff |
| `PermanentAPIError` | HTTP 400/401/404: retrying won't help | **Fail right away** (re-raise) |

## Write

```python
fetch_all_records(fetch_page, max_retries=3, base_delay=0.5, sleep=time.sleep)
```

- Start at page 1 and follow `next_page` until it's `None`.
- Return **all records from all pages** as one list, in order.
- On a `TransientAPIError`, wait and retry the **same page**. The waits double each time: `base_delay`, then `2 × base_delay`, then `4 × base_delay`...
- If `max_retries` retries on the same page all fail, give up and raise the last error.
- `sleep` is passed in so tests don't actually wait. Call `sleep(seconds)` instead of `time.sleep` directly.

## Example

```
page 1 -> OK (2 records)
page 2 -> TransientAPIError    sleep(0.5)
page 2 -> TransientAPIError    sleep(1.0)
page 2 -> OK (2 records)
page 3 -> OK (1 record), next_page = None
=> returns 5 records
```

## Things to talk about

- **Why pass `fetch_page` and `sleep` in?** That's *dependency injection*. It makes the function testable without a network or real waiting.
- **Jitter:** in production, add a little randomness to each delay so 100 clients don't all retry at the same instant.
- **Idempotency:** GETs are safe to retry. A retried POST could create a duplicate unless the API supports an idempotency key.
- **Memory:** for a huge dataset, `yield` records page by page (a generator) instead of building one giant list.
- For HTTP 429 (rate limited), respect the `Retry-After` header if the server sends one.
