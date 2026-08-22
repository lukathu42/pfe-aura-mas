"""Expose the `code/` package under its import name `aura_mas`.

The package directory was renamed `aura_mas/` -> `code/` but every intra-package
import (and the docs) still says `aura_mas`; `code` is also a stdlib module name,
so it must not be imported under that name. Loading it from its path under the
`aura_mas` alias keeps both the sources and the stdlib intact.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG_DIR = ROOT / "code"

if "aura_mas" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "aura_mas", PKG_DIR / "__init__.py",
        submodule_search_locations=[str(PKG_DIR)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["aura_mas"] = module
    spec.loader.exec_module(module)
