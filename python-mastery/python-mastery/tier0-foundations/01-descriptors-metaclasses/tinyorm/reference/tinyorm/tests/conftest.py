from collections.abc import Iterator

import pytest

from tinyorm import Database, FloatField, IntegerField, Model, TextField


class Timestamped(Model):
    class Meta:
        abstract = True

    created = IntegerField(default=0)


class Product(Timestamped):
    class Meta:
        table = "products"

    name = TextField(max_length=20)
    price = FloatField(default=0.0)
    stock = IntegerField(default=0)
    note = TextField(null=True)


@pytest.fixture
def db() -> Iterator[Database]:
    d = Database(":memory:")
    d.create_tables(Product)
    yield d
    d.close()


@pytest.fixture
def products(db: Database) -> list[Product]:
    return [
        Product.objects.create(name="widget", price=9.5, stock=3),
        Product.objects.create(name="gizmo", price=24.0, stock=0),
        Product.objects.create(name="doohickey", price=3.25, stock=10, note="cheap"),
    ]
