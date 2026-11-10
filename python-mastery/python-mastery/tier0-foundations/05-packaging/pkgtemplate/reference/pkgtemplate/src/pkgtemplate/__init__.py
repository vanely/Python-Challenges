"""pkgtemplate — the public API is what's listed in __all__."""

from pkgtemplate._version import __version__
from pkgtemplate.core import greet, slugify

__all__ = ["__version__", "greet", "slugify"]
