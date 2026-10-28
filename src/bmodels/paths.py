"""Repo-relative locations shared by every tool and product script."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # src/bmodels/paths.py -> repo root (editable install)
PROJECTS = ROOT / "projects"
BUILD = ROOT / "build"
TEMPLATES = ROOT / "templates"
