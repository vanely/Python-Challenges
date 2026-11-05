# tinyorm — build spec

A Django-shaped ORM in ~350 lines over `sqlite3`. The point is the mechanism, not the feature list.

## Target API
```python
from tinyorm import Model, IntegerField, TextField, FloatField, Database

class Product(Model):
    class Meta:
        table = "products"
    name = TextField(max_length=100)
    price = FloatField(default=0.0)
    stock = IntegerField(default=0)

db = Database(":memory:")
db.create_tables(Product)

p = Product(name="widget", price=9.5)
p.save()                                       # INSERT; sets p.id
p.price = -1                                   # ValidationError via descriptor __set__
Product.objects.filter(price__gt=5).order_by("-price")[:10]      # lazy QuerySet; SQL built on iteration
Product.objects.get(id=1)                      # DoesNotExist / MultipleObjectsReturned
Product.objects.filter(name__contains="wid").count()
Product.objects.filter(stock=0).update(stock=10)
p.delete()
```

## Requirements
1. **Fields are data descriptors.** `__set_name__` learns the column name. `__set__` validates (type, `max_length`, `null`). Value stored on the instance, not the field. Each field knows its SQL type and how to convert to/from the DB (`to_db`, `from_db`).
2. **`ModelBase` metaclass** (a real one — this is the exercise) collects fields in declaration order into `cls._meta` (`table`, `fields`, `pk`), auto-adds an `id = IntegerField(primary_key=True)` if none declared, handles the inner `class Meta`, and attaches `objects = Manager()` bound to the model. Also implement the same thing with `__init_subclass__` in a separate branch and write in `NOTES.md` which you'd ship and why.
3. **Manager** is a descriptor that only works on the class (`Product.objects` OK, `p.objects` raises `AttributeError`) — exactly like Django.
4. **QuerySet** is lazy and immutable: `filter`, `exclude`, `order_by`, slicing, `__iter__`, `__len__`, `count`, `first`, `get`, `update`, `delete`, `values`. Chaining returns new QuerySets. SQL compiled once on evaluation; results cached on the instance (like Django's `_result_cache`). Lookups: exact (default), `gt/gte/lt/lte`, `contains`, `in`, `isnull`. Parameterised — never string-format values.
5. **Model instances**: `save()` does INSERT or UPDATE based on pk; `delete()`; `refresh_from_db()`; `__eq__` by pk and class; `__repr__`.
6. **Database** holds the `sqlite3` connection, `create_tables`, `execute`, and a `transaction()` context manager. Models find the DB through `Database.default` (set on construction) — a simplified global like Django's connection handler.
7. Errors: `ValidationError`, `DoesNotExist` (a per-model subclass, `Product.DoesNotExist`, like Django), `MultipleObjectsReturned`.

## Tests to write (reference has them)
Descriptor validation; field collection and inheritance (abstract base with shared fields); Manager class-only access; lazy evaluation (no SQL until iteration — assert via a query log); chaining immutability; every lookup; slicing → LIMIT/OFFSET; get() error cases; save insert vs update; per-model `DoesNotExist`.

## Stretch
- `ForeignKey` with a lazy related-object descriptor (this is Tier 1's project — leave it).
- `select_related`-style JOIN.
- `Q` objects with `&`/`|`/`~` via operator overloading.

## Reference
`src/tinyorm/` is a full implementation with `tests/`. Run `pytest`, `mypy --strict src`, `ruff check .`.
