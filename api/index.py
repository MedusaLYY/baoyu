# -*- coding: utf-8 -*-
"""Vercel entrypoint for the abalone Flask app."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _find_project_dir() -> Path:
    for candidate in ROOT.iterdir():
        if candidate.is_dir() and (candidate / "app.py").is_file() and (candidate / "templates").is_dir():
            return candidate
    raise RuntimeError("Could not find Flask project directory with app.py and templates")


PROJECT_DIR = _find_project_dir()
sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("ABALONE_ENGINE", "local")
os.environ.setdefault("ABALONE_RUNTIME_DATA_DIR", "/tmp/abalone-demo")
os.environ.setdefault("ABALONE_MODEL_DIR", "/tmp/abalone-demo-model")

spec = importlib.util.spec_from_file_location("abalone_flask_app", PROJECT_DIR / "app.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load Flask app module")

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

app = module.app
