"""Compatibility entrypoint for the live artifact adapter (no bootstrap constants)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _adapter():
    spec = importlib.util.spec_from_file_location(
        "meydenbauer_artifacts", Path(__file__).with_name("build_from_artifacts.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build():
    return _adapter().build()


if __name__ == "__main__":
    _adapter().main()
