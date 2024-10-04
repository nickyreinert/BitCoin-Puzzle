#python bitcoinPuzzle-v4-setup.py build_ext --inplace
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize("bitcoinPuzzle-v4.pyx")
)

