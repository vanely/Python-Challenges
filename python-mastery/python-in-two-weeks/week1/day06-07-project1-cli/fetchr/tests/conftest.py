from pathlib import Path

import pytest

from fetchr.cache import Cache


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(directory=tmp_path / "cache", ttl=60)


@pytest.fixture
def repo_payload() -> dict[str, object]:
    return {
        "full_name": "encode/httpx",
        "description": "HTTP client",
        "stargazers_count": 13000,
        "forks_count": 800,
        "open_issues_count": 50,
        "language": "Python",
        "html_url": "https://github.com/encode/httpx",
        "pushed_at": "2026-01-02T03:04:05Z",
    }
