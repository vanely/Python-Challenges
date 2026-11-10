# Step 1 — Fields and the metaclass

**Checkpoint:** from `student/`, `uv run pytest ../checkpoints/test_orm.py -k "fields or descriptor or class_access or manager or does_not_exist"`

Read the API in `README.md` first. This step is requirements 1–3 and the `DoesNotExist` half of requirement 7.

## What has to be true

- `IntegerField`, `TextField`, `FloatField` are data descriptors. `__set_name__` stores the column name. `__set__` validates type, `max_length`, and `null`. The value lives on the instance (`p.__dict__`), not on the field. Class access (`Product.name`) returns the field.
- `FloatField` coerces an int to float.
- `ModelBase` collects fields in declaration order, including inherited fields from an abstract base, into `cls._meta.fields`. It adds `id = IntegerField(primary_key=True)` when no pk was declared. It reads `class Meta` for `table` and `abstract`.
- `Product.DoesNotExist` is a subclass of the base `DoesNotExist`.
- `objects` is a descriptor that works on the class and raises `AttributeError` on an instance.
- `Database(":memory:")` with `create_tables` and `log` (a list of `(sql, params)` ) exists, because the manager tests touch it. Parameterised queries only.

Create the package with `uv init --package student` inside this folder, implement `src/tinyorm/`, and run the command above from `student/`. `reference/tinyorm/` stays closed until every checkpoint test passes.

## Explain it back

1. Why is a field a data descriptor rather than a value stored on the class?
2. What would `__init_subclass__` not give you that a metaclass does? (You'll try the other one as a branch later; answer from the reading first.)
