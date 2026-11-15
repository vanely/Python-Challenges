"""
Problem 8 — Paginated API Client with Retries (PRACTICE)

Read ../README.md first. Fill in the TODOs, then run:
    python3 practice.py
"""

import time


class TransientAPIError(Exception):
    """A temporary failure (timeout, 429, 5xx). Worth retrying."""


class PermanentAPIError(Exception):
    """A failure retrying won't fix (400, 401, 404). Stop right away."""


def fetch_page_with_retry(fetch_page, page_number, max_retries, base_delay, sleep):
    # TODO: call fetch_page(page_number)
    # TODO: on TransientAPIError, sleep(base_delay * 2 ** attempt) and try again
    # TODO: once max_retries retries have failed, re-raise the error
    # TODO: let PermanentAPIError pass straight through (don't catch it)
    raise NotImplementedError


def fetch_all_records(fetch_page, max_retries=3, base_delay=0.5, sleep=time.sleep):
    # TODO: start at page 1, follow response["next_page"] until it's None,
    #       and collect every response["data"] into one list
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Tests: don't change anything below this line.
# ---------------------------------------------------------------------------
class FakeLoanAPI:
    PAGES = {
        1: {"data": [{"loan_id": "L1"}, {"loan_id": "L2"}], "next_page": 2},
        2: {"data": [{"loan_id": "L3"}, {"loan_id": "L4"}], "next_page": 3},
        3: {"data": [{"loan_id": "L5"}], "next_page": None},
    }

    def __init__(self, failures=None, permanent_fail_page=None):
        self.failures_left = dict(failures or {})
        self.permanent_fail_page = permanent_fail_page
        self.calls = []

    def fetch_page(self, page_number):
        self.calls.append(page_number)
        if page_number == self.permanent_fail_page:
            raise PermanentAPIError("401 Unauthorized")
        if self.failures_left.get(page_number, 0) > 0:
            self.failures_left[page_number] -= 1
            raise TransientAPIError("503 Service Unavailable")
        return self.PAGES[page_number]


class FakeSleep:
    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


def run_tests():
    all_ids = ["L1", "L2", "L3", "L4", "L5"]

    api, sleeper = FakeLoanAPI(), FakeSleep()
    records = fetch_all_records(api.fetch_page, sleep=sleeper)
    assert [r["loan_id"] for r in records] == all_ids
    assert api.calls == [1, 2, 3]
    assert sleeper.delays == []

    api, sleeper = FakeLoanAPI(failures={2: 2}), FakeSleep()
    records = fetch_all_records(api.fetch_page, sleep=sleeper)
    assert [r["loan_id"] for r in records] == all_ids
    assert api.calls == [1, 2, 2, 2, 3]
    assert sleeper.delays == [0.5, 1.0]

    api, sleeper = FakeLoanAPI(failures={2: 99}), FakeSleep()
    try:
        fetch_all_records(api.fetch_page, max_retries=3, sleep=sleeper)
        assert False, "should have raised TransientAPIError"
    except TransientAPIError:
        pass
    assert api.calls == [1, 2, 2, 2, 2]
    assert sleeper.delays == [0.5, 1.0, 2.0]

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
