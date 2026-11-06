"""Day 3 — the four record types."""
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import NamedTuple, NotRequired, TypedDict


class Role(StrEnum):
    ADMIN = auto()          # value "admin"
    VIEWER = auto()


@dataclass
class User:
    id: int
    name: str
    role: Role = Role.VIEWER
    tags: list[str] = field(default_factory=list)   # never `= []`

    def is_admin(self) -> bool:
        return self.role is Role.ADMIN


u = User(1, "Ada", tags=["core"])
v = User(1, "Ada", tags=["core"])
print(u)                 # User(id=1, name='Ada', role=<Role.VIEWER: 'viewer'>, tags=['core']) — free __repr__
print(u == v)            # True — free __eq__ (field-wise)
u.tags.append("x")
print(u.tags, v.tags)    # separate lists thanks to default_factory


@dataclass(frozen=True, slots=True, order=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0

    @classmethod
    def parse(cls, s: str) -> "Version":
        parts = [int(p) for p in s.split(".")]
        return cls(*parts)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


a = Version.parse("1.2.3")
b = Version(1, 10)
print(a < b, sorted([b, a]), str(a), {a: "hashable because frozen"})
try:
    a.major = 9  # type: ignore[misc]
except AttributeError as e:
    print("frozen:", e)


class Point(NamedTuple):
    x: float
    y: float

    def dist(self) -> float:
        return float((self.x**2 + self.y**2) ** 0.5)


p = Point(3, 4)
x, y = p                 # unpacks like a tuple
print(p, p.x, p[0], p.dist(), p._replace(x=0))


class Movie(TypedDict):
    title: str
    year: int
    rating: NotRequired[float]


m: Movie = {"title": "Arrival", "year": 2016}    # still a plain dict at runtime
m["rating"] = 8.0
print(m, type(m))
# m["director"] = "V"   # mypy: TypedDict "Movie" has no key "director"


@dataclass(kw_only=True)
class Config:
    host: str
    port: int = 8000
    debug: bool = False

    def __post_init__(self) -> None:
        if not (0 < self.port < 65536):
            raise ValueError(f"bad port {self.port}")


print(Config(host="localhost"))
try:
    Config(host="x", port=0)
except ValueError as e:
    print("validated:", e)
