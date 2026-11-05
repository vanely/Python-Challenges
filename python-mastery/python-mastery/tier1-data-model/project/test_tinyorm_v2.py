"""Skeleton for tinyorm v2. Adjust imports to your package. Run inside your tinyorm project."""
import pytest

from tinyorm import Database, ForeignKey, IntegerField, Model, Q, TextField  # type: ignore[attr-defined]


class Author(Model):
    name = TextField()


class Post(Model):
    title = TextField()
    author = ForeignKey(Author, related_name="posts")
    views = IntegerField(default=0)


@pytest.fixture
def db():  # type: ignore[no-untyped-def]
    d = Database(":memory:")
    d.create_tables(Author, Post)
    a = Author.objects.create(name="ada")
    b = Author.objects.create(name="bob")
    Post.objects.bulk_create([Post(title="p1", author=a, views=5), Post(title="p2", author=a), Post(title="p3", author=b)])
    yield d
    d.close()


def test_fk_stores_id_and_is_lazy(db):  # type: ignore[no-untyped-def]
    p = Post.objects.get(title="p1")
    assert p.author_id == 1 and "author" not in p.__dict__
    db.log.clear()
    assert p.author.name == "ada"
    assert len(db.log) == 1
    assert p.author.name == "ada" and len(db.log) == 1      # cached


def test_fk_assignment(db):  # type: ignore[no-untyped-def]
    p = Post.objects.get(title="p3")
    p.author = Author.objects.get(name="ada")
    p.save()
    assert Post.objects.get(title="p3").author_id == 1


def test_reverse_manager(db):  # type: ignore[no-untyped-def]
    a = Author.objects.get(name="ada")
    assert {p.title for p in a.posts.all()} == {"p1", "p2"}
    assert a.posts.filter(views__gt=0).count() == 1


def test_select_related_one_query(db):  # type: ignore[no-untyped-def]
    db.log.clear()
    posts = list(Post.objects.select_related("author").order_by("id"))
    names = [p.author.name for p in posts]
    assert names == ["ada", "ada", "bob"] and len(db.log) == 1 and "JOIN" in db.log[0][0]


def test_q_objects(db):  # type: ignore[no-untyped-def]
    qs = Post.objects.filter(Q(views__gt=0) | Q(title="p3"))
    assert {p.title for p in qs} == {"p1", "p3"}
    assert {p.title for p in Post.objects.filter(~Q(title="p1") & Q(author__name="ada"))} == {"p2"}


def test_iterator_does_not_cache(db):  # type: ignore[no-untyped-def]
    qs = Post.objects.all()
    it = qs.iterator()
    db.log.clear()
    next(it); list(it)
    list(qs.iterator())
    assert len(db.log) == 2


def test_bulk_create_single_statement(db):  # type: ignore[no-untyped-def]
    db.log.clear()
    Post.objects.bulk_create([Post(title=f"b{i}", author_id=1) for i in range(5)])
    assert len(db.log) == 1 and Post.objects.count() == 8
