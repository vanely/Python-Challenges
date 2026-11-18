"""
Problem 8 — Paginated API Client with Retries (SOLUTION)

Two loops:
  - The OUTER loop walks through the pages.
  - The INNER loop retries a single page when it fails for a moment.
"""

import time


class TransientAPIError(Exception):
    """A temporary failure (timeout, 429, 5xx). Worth retrying."""


class PermanentAPIError(Exception):
    """A failure retrying won't fix (400, 401, 404). Stop right away."""


def fetch_page_with_retry(fetch_page, page_number, max_retries, base_delay, sleep):
    """
    Try to fetch one page. On a TransientAPIError, wait and try again,
    doubling the wait each time. PermanentAPIError is NOT caught, so it
    passes straight up to the caller.
    """
    attempt = 0
    while True:
        try:
            return fetch_page(page_number)

        except TransientAPIError:
            if attempt >= max_retries:
                # Out of retries: re-raise the error we just caught.
                raise

            # Exponential backoff: 0.5s, 1s, 2s, 4s ...
            delay = base_delay * (2 ** attempt)
            sleep(delay)
            attempt += 1


def fetch_all_records(fetch_page, max_retries=3, base_delay=0.5, sleep=time.sleep):
    all_records = []
    page_number = 1

    # Keep going until the API says there is no next page.
    while page_number is not None:
        response = fetch_page_with_retry(
            fetch_page, page_number, max_retries, base_delay, sleep
        )

        all_records.extend(response["data"])
        page_number = response["next_page"]

    return all_records


# ---------------------------------------------------------------------------
# Tests: a fake API we fully control, so there's no real network or waiting.
# ---------------------------------------------------------------------------
class FakeLoanAPI:
    """
    Pretends to be a vendor API with 3 pages of loan records.
    `failures` says how many times each page fails before it works,
    e.g. {2: 2} means page 2 fails twice, then succeeds.
    """

    PAGES = {
        1: {"data": [{"loan_id": "L1"}, {"loan_id": "L2"}], "next_page": 2},
        2: {"data": [{"loan_id": "L3"}, {"loan_id": "L4"}], "next_page": 3},
        3: {"data": [{"loan_id": "L5"}], "next_page": None},
    }

    def __init__(self, failures=None, permanent_fail_page=None):
        self.failures_left = dict(failures or {})
        self.permanent_fail_page = permanent_fail_page
        self.calls = []  # record every page requested, to check behavior

    def fetch_page(self, page_number):
        self.calls.append(page_number)

        if page_number == self.permanent_fail_page:
            raise PermanentAPIError("401 Unauthorized")

        if self.failures_left.get(page_number, 0) > 0:
            self.failures_left[page_number] -= 1
            raise TransientAPIError("503 Service Unavailable")

        return self.PAGES[page_number]


class FakeSleep:
    """Records how long we were asked to sleep, without actually waiting."""

    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


def run_tests():
    all_ids = ["L1", "L2", "L3", "L4", "L5"]

    # 1) The happy path: no failures, all pages collected in order
    api, sleeper = FakeLoanAPI(), FakeSleep()
    records = fetch_all_records(api.fetch_page, sleep=sleeper)
    assert [r["loan_id"] for r in records] == all_ids
    assert api.calls == [1, 2, 3]
    assert sleeper.delays == []

    # 2) Page 2 fails twice, then works. Backoff doubles: 0.5, then 1.0
    api, sleeper = FakeLoanAPI(failures={2: 2}), FakeSleep()
    records = fetch_all_records(api.fetch_page, sleep=sleeper)
    assert [r["loan_id"] for r in records] == all_ids
    assert api.calls == [1, 2, 2, 2, 3]
    assert sleeper.delays == [0.5, 1.0]

    # 3) Page 2 keeps failing: 1 try + 3 retries, then give up
    api, sleeper = FakeLoanAPI(failures={2: 99}), FakeSleep()
    try:
        fetch_all_records(api.fetch_page, max_retries=3, sleep=sleeper)
        assert False, "should have raised TransientAPIError"
    except TransientAPIError:
        pass
    assert api.calls == [1, 2, 2, 2, 2]
    assert sleeper.delays == [0.5, 1.0, 2.0]

    # 4) A permanent error is NOT retried
    api, sleeper = FakeLoanAPI(permanent_fail_page=2), FakeSleep()
    try:
        fetch_all_records(api.fetch_page, sleep=sleeper)
        assert False, "should have raised PermanentAPIError"
    except PermanentAPIError:
        pass
    assert api.calls == [1, 2]
    assert sleeper.delays == []

    print("All tests passed!")


if __name__ == "__main__":
    run_tests()
