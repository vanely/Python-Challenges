"""T2 w3 — the import system: meta path, specs, loaders, namespace packages, reload."""
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import textwrap
import types

print("meta_path:", [getattr(f, "__name__", type(f).__name__) for f in sys.meta_path])  # finders are classes
print("path_hooks:", [h.__name__ if hasattr(h, "__name__") else type(h).__name__ for h in sys.path_hooks])

spec = importlib.util.find_spec("json")
print("json spec:", spec.name, type(spec.loader).__name__, spec.submodule_search_locations)  # type: ignore[union-attr]


# --- a finder + loader: import .ini files as modules -----------------------------------------------
class IniLoader(importlib.abc.Loader):
    def __init__(self, path: str) -> None:
        self.path = path

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType | None:
        return None                         # default: a plain ModuleType

    def exec_module(self, module: types.ModuleType) -> None:
        import configparser
        cp = configparser.ConfigParser()
        cp.read(self.path)
        for section in cp.sections():
            setattr(module, section, types.SimpleNamespace(**cp[section]))
        module.__file__ = self.path


class IniFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: object, target: object = None) -> importlib.machinery.ModuleSpec | None:
        for d in sys.path:
            candidate = os.path.join(d, fullname + ".ini")
            if os.path.isfile(candidate):
                return importlib.util.spec_from_loader(fullname, IniLoader(candidate), origin=candidate)
        return None


tmp = tempfile.mkdtemp()
with open(os.path.join(tmp, "settings.ini"), "w") as f:
    f.write("[db]\nhost = localhost\nport = 5432\n")
sys.path.insert(0, tmp)
sys.meta_path.insert(0, IniFinder())
import settings  # type: ignore[import-not-found]  # noqa: E402

print("ini module:", settings.db.host, settings.db.port, settings.__spec__.origin)

# --- reload re-executes into the SAME module object ---------------------------------------------
with open(os.path.join(tmp, "settings.ini"), "a") as f:
    f.write("[cache]\nttl = 30\n")
before = settings
importlib.reload(settings)
print("same object after reload:", settings is before, "new attr:", settings.cache.ttl)

# --- sys.modules is populated BEFORE exec: partial modules and circular imports -----------------
with open(os.path.join(tmp, "a_mod.py"), "w") as f:
    f.write(textwrap.dedent("""
        import b_mod                     # b_mod imports a_mod back; sees a partially-initialised a_mod
        A_VALUE = 1
        def a_fn(): return b_mod.b_fn()
    """))
with open(os.path.join(tmp, "b_mod.py"), "w") as f:
    f.write(textwrap.dedent("""
        import a_mod                     # OK: gets the partial module from sys.modules
        print("  in b_mod: a_mod has A_VALUE?", hasattr(a_mod, "A_VALUE"))
        def b_fn(): return a_mod.A_VALUE  # OK: looked up at call time
        # from a_mod import A_VALUE      # would FAIL: attribute doesn't exist yet
    """))
importlib.invalidate_caches()               # FileFinder caches directory listings
import a_mod  # type: ignore[import-not-found]  # noqa: E402

print("circular import resolved lazily:", a_mod.a_fn())

# --- namespace packages: no __init__.py, merged across sys.path -------------------------------------
for d in ("nsroot1", "nsroot2"):
    os.makedirs(os.path.join(tmp, d, "nspkg"), exist_ok=True)
    with open(os.path.join(tmp, d, "nspkg", f"{d}_mod.py"), "w") as f:
        f.write(f"NAME = {d!r}\n")
    sys.path.insert(0, os.path.join(tmp, d))
importlib.invalidate_caches()
import nspkg  # type: ignore[import-not-found]  # noqa: E402

print("namespace pkg paths:", list(nspkg.__path__), type(nspkg.__spec__.loader).__name__)
from nspkg import nsroot1_mod, nsroot2_mod  # noqa: E402

print(nsroot1_mod.NAME, nsroot2_mod.NAME)

# --- lazy import via LazyLoader --------------------------------------------------------------------
def lazy_import(name: str) -> types.ModuleType:
    spec = importlib.util.find_spec(name)
    assert spec and spec.loader
    spec.loader = importlib.util.LazyLoader(spec.loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)         # does NOT execute yet
    return module


dec = lazy_import("decimal")
print("lazy decimal in sys.modules, executed on first attribute access:", dec.Decimal("1.5"))
