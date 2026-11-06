import pytest

from tests.conftest import Product
from tinyorm import Database, DoesNotExist, MultipleObjectsReturned, ValidationError


# --- descriptors + metaclass -------------------------------------------------------------------
def test_fields_collected_in_order_with_auto_pk() -> None:
    assert list(Product._meta.fields) == ["created", "id", "name", "price", "stock", "note"]
    assert Product._meta.pk.name == "id"
    assert Product._meta.table == "products"


def test_field_descriptor_validates() -> None:
    p = Product(name="x")
    with pytest.raises(ValidationError, match="expected str"):
        p.name = 5  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="longer"):
        p.name = "y" * 21
    with pytest.raises(ValidationError, match="null"):
        p.name = None
    p.note = None  # null=True
    p.price = 3  # int coerced to float
    assert p.price == 3.0 and isinstance(p.price, float)
    assert "_f_name" in p.__dict__ and "name" not in p.__dict__  # stored on instance, not field


def test_class_access_returns_field() -> None:
    assert Product.name.max_length == 20  # obj is None branch


def test_manager_is_class_only(db: Database) -> None:
    assert Product.objects.count() == 0
    with pytest.raises(AttributeError, match="instances"):
        _ = Product(name="x").objects


def test_per_model_does_not_exist(db: Database) -> None:
    assert issubclass(Product.DoesNotExist, DoesNotExist)
    with pytest.raises(Product.DoesNotExist):
        Product.objects.get(id=99)


# --- persistence ----------------------------------------------------------------------------------
def test_save_insert_then_update(db: Database) -> None:
    p = Product(name="a", price=1)
    assert p.pk is None
    p.save()
    assert p.pk == 1
    p.price = 2
    p.save()
    p.refresh_from_db()
    assert p.price == 2.0
    assert Product.objects.count() == 1
    p.delete()
    assert p.pk is None and Product.objects.count() == 0


def test_eq_and_hash(products: list[Product]) -> None:
    a = Product.objects.get(id=1)
    assert a == products[0] and hash(a) == hash(products[0])
    with pytest.raises(TypeError):
        hash(Product(name="unsaved"))


# --- laziness + immutability ----------------------------------------------------------------------
def test_queryset_is_lazy(db: Database, products: list[Product]) -> None:
    db.log.clear()
    qs = Product.objects.filter(price__gt=5).order_by("-price")
    assert db.log == []  # nothing executed yet
    names = [p.name for p in qs]
    assert names == ["gizmo", "widget"]
    assert len(db.log) == 1
    list(qs)
    assert len(db.log) == 1  # cached; no second query
    assert "?" in db.log[0][0] and db.log[0][1] == (5,)  # parameterised


def test_chaining_returns_new_querysets(products: list[Product]) -> None:
    base = Product.objects.all()
    cheap = base.filter(price__lt=10)
    assert base.count() == 3 and cheap.count() == 2
    assert base is not cheap


@pytest.mark.parametrize(
    ("lookup", "expected"),
    [
        ({"name": "gizmo"}, {"gizmo"}),
        ({"price__gte": 9.5}, {"widget", "gizmo"}),
        ({"price__lte": 9.5}, {"widget", "doohickey"}),
        ({"name__contains": "o"}, {"gizmo", "doohickey"}),
        ({"name__startswith": "w"}, {"widget"}),
        ({"stock__in": [0, 10]}, {"gizmo", "doohickey"}),
        ({"stock__in": []}, set()),
        ({"note__isnull": True}, {"widget", "gizmo"}),
        ({"note__isnull": False}, {"doohickey"}),
        ({"pk": 2}, {"gizmo"}),
    ],
)
def test_lookups(products: list[Product], lookup: dict[str, object], expected: set[str]) -> None:
    assert {p.name for p in Product.objects.filter(**lookup)} == expected


def test_exclude(products: list[Product]) -> None:
    assert {p.name for p in Product.objects.exclude(stock=0)} == {"widget", "doohickey"}


def test_slicing_uses_limit_offset(db: Database, products: list[Product]) -> None:
    db.log.clear()
    page = Product.objects.order_by("id")[1:3]
    assert [p.id for p in page] == [2, 3]
    assert "LIMIT 2 OFFSET 1" in db.log[-1][0]
    assert Product.objects.order_by("-id")[0].id == 3
    assert Product.objects.order_by("id").first().id == 1  # type: ignore[union-attr]


def test_count_and_exists_respect_slicing(products: list[Product]) -> None:
    qs = Product.objects.order_by("id")
    assert qs[:2].count() == len(qs[:2]) == 2
    assert qs[1:].count() == len(qs[1:]) == 2
    assert qs[5:].count() == 0
    assert qs[1:].exists() and qs[:1].exists()
    assert not qs[3:].exists()


def test_nested_slicing_composes(products: list[Product]) -> None:
    qs = Product.objects.order_by("id")
    assert [p.id for p in qs[:2][1:]] == [2]
    assert [p.id for p in qs[1:][:1]] == [2]
    assert [p.id for p in qs[:3][1:10]] == [2, 3]
    assert qs[:2][1:].count() == 1
    assert list(qs[:1][2:]) == [] and qs[:1][2:].count() == 0
    assert qs[1:][1].id == 3
    with pytest.raises(IndexError):
        qs[:1][1]


def test_get_errors(products: list[Product]) -> None:
    with pytest.raises(MultipleObjectsReturned):
        Product.objects.get(price__gt=0)
    with pytest.raises(ValueError, match="no field"):
        Product.objects.filter(nope=1)


def test_bulk_update_and_delete(products: list[Product]) -> None:
    assert Product.objects.filter(stock=0).update(stock=5) == 1
    assert Product.objects.get(name="gizmo").stock == 5
    with pytest.raises(ValidationError):
        Product.objects.all().update(stock="x")
    assert Product.objects.filter(price__lt=5).delete() == 1
    assert Product.objects.count() == 2


def test_values(products: list[Product]) -> None:
    rows = Product.objects.order_by("id").values("id", "name")
    assert rows[0] == {"id": 1, "name": "widget"}
