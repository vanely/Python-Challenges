# 0.1 — Descriptors and metaclasses: how Django's `Model` actually works

You've used `class Article(models.Model): title = models.CharField()` a thousand times. This module makes you able to write it from nothing.

## Objectives
- Explain the descriptor protocol (`__get__`, `__set__`, `__set_name__`) and why `@property`, methods, `classmethod`, and Django fields are all descriptors
- Explain what a metaclass is, what `type(name, bases, ns)` does, and when `__init_subclass__` is enough instead
- Build `tinyorm`: descriptor-based fields, a metaclass that collects them, a lazy query builder, SQLite backend

## Readings

| Source | Where | Read |
|---|---|---|
| Descriptor HowTo (Raymond Hettinger) | https://docs.python.org/3/howto/descriptor.html | **All.** The single best document on the topic. Includes pure-Python implementations of `property`, `classmethod`, `staticmethod`, and functions-as-descriptors — read those implementations line by line. |
| Data model: customizing attribute access | https://docs.python.org/3/reference/datamodel.html#customizing-attribute-access | `__getattribute__`, `__getattr__`, descriptors, `__slots__` |
| Data model: metaclasses | https://docs.python.org/3/reference/datamodel.html#metaclasses | "Customizing class creation" through "Metaclass example" incl. `__prepare__`, `__init_subclass__`, `__set_name__` |
| PEP 487 | https://peps.python.org/pep-0487/ | `__init_subclass__` and `__set_name__` — the "you don't need a metaclass" PEP |
| Fluent Python ch. 23 "Attribute Descriptors" | Book | All |
| Fluent Python ch. 24 "Class Metaprogramming" | Book | All |
| Django source | `django/db/models/base.py` → `class ModelBase(type)`, `__new__`, `_prepare`, `add_to_class`; `django/db/models/fields/__init__.py` → `Field.contribute_to_class`; `django/db/models/query_utils.py` → `DeferredAttribute`; `related_descriptors.py` | Read `ModelBase.__new__` fully; then how `contribute_to_class` + `DeferredAttribute` give you `article.title` |
| SQLAlchemy | `sqlalchemy/orm/decl_base.py` and `orm/attributes.py` `InstrumentedAttribute` | Skim — the same pattern with different tradeoffs |

## Reading summaries

### Attribute lookup order (memorise this)
For `obj.x`, `object.__getattribute__` does:
1. Look for `x` in `type(obj).__mro__`. If found **and** it defines `__set__` or `__delete__` → **data descriptor** → return `desc.__get__(obj, type(obj))`. (This is why `@property` wins over an instance dict entry.)
2. Else if `x` in `obj.__dict__` → return it.
3. Else if found on the type and it defines `__get__` → **non-data descriptor** → call `__get__`. (Functions are non-data descriptors; that's how bound methods happen, and why instance attributes can shadow methods.)
4. Else plain class attribute; else `__getattr__` if defined; else `AttributeError`.

Assignment `obj.x = v` checks the type for a data descriptor first and calls `__set__`; otherwise writes `obj.__dict__`.

### The descriptor protocol
- `__get__(self, obj, objtype=None)` — `obj is None` when accessed on the class; conventionally return `self` then.
- `__set__(self, obj, value)` / `__delete__(self, obj)` make it a data descriptor.
- `__set_name__(self, owner, name)` (3.6+) is called at class-creation time with the attribute name — this is how a field learns its own name without repeating it. Django fields do this via `contribute_to_class`, which predates `__set_name__`.
- Store per-instance state on `obj` (in `obj.__dict__[self.name]` or a private name), **never** on the descriptor — the descriptor is shared by all instances.
- `property` is just a data descriptor with `fget/fset/fdel`. `classmethod`/`staticmethod` are non-data descriptors that rebind. `functools.cached_property` is a *non-data* descriptor that writes into `__dict__` once so step 2 wins next time — read its source; it's ~20 lines.

### Metaclasses
- A class is an instance of its metaclass. `type` is the default. `class C(B, metaclass=M):` → Python calls `M.__prepare__(name, bases)` for the namespace, executes the body into it, then `M(name, bases, ns)` → `M.__new__` → `M.__init__`.
- Override `__new__` to inspect/alter the namespace before the class exists (collect fields, validate, inject attributes). Override `__call__` on the metaclass to control instantiation (singletons, registries).
- Django's `ModelBase.__new__`: creates the class with every attribute that *lacks* `contribute_to_class` (so plain attributes get normal `__set_name__` handling), builds `_meta`, then calls `add_to_class` for the held-back ones — fields — which calls their `contribute_to_class`. That's the whole trick.
- **Prefer** `__init_subclass__` (runs on the *parent* when a subclass is created) + `__set_name__` for 90% of "collect the fields" use cases. Reach for a real metaclass only when you need `__prepare__`, need to alter the namespace before creation, or need to change what `isinstance`/`__call__` mean.

### Where this shows up beyond ORMs
`enum.EnumMeta`, `abc.ABCMeta` (`register`, `__instancecheck__`), `typing.Protocol`, pydantic's `ModelMetaclass`, `dataclasses` (no metaclass — decorator design, deliberately), attrs.

## Copy
`copy/01_descriptors.py` — the protocol, `__set_name__`, pure-Python `property`/`classmethod`/`cached_property`, and a validated field.
`copy/02_metaclasses.py` — `type()` by hand, `__prepare__`, a registry metaclass, `__init_subclass__` doing the same job, metaclass `__call__`.

## Analysis prompts (write answers in `NOTES.md`)
1. Why does Django's `ModelBase.__new__` pass only attributes *without* `contribute_to_class` to `super_new(cls, name, bases, new_attrs, **kwargs)` and add fields afterwards via `add_to_class`?
2. `DeferredAttribute.__get__` checks `instance.__dict__` first, then `refresh_from_db`. Why is it a *non-data* descriptor? What would break if it defined `__set__`?
3. `functools.cached_property` used to hold a lock (removed in 3.12). Read the 3.11 and 3.12 sources. Why was it removed?
4. Reimplement `staticmethod` from the HowTo. Then explain why `@staticmethod` functions became callable directly in 3.10.

## Build: `tinyorm`
Spec in `tinyorm/README.md`. The reference implementation there is complete and tested — build yours first.
