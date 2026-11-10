from Cython.Build import cythonize
from setuptools import setup

setup(ext_modules=cythonize("v3_parse.pyx", annotate=True))
