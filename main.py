#!/usr/bin/env python3
"""
SharedComputing — single entry point.

Pipeline:
  1. Splash (:mod:`splash`)
  2. Main menu (:mod:`main_menu`)
       • **N** — :func:`dataset_picker.pick_dataset_folder` → :func:`run_config.run_interactive`
         → :func:`confirm.review_and_confirm` → :func:`training_monitor.run_training_monitor`
       • **H** — :func:`results.show_results` · **P** — predict (stub)
       • **Q** — quit

Those modules are preloaded by :func:`_load_pipeline` so a broken install fails before the splash.

Run: ``python3 main.py``
"""

from __future__ import annotations

import importlib
import os

# Same default as ``dataset_picker`` so curses UIs behave on minimal TERM.
if os.environ.get("TERM", "") not in ("xterm-256color", "xterm", "screen-256color"):
    os.environ["TERM"] = "xterm-256color"

from splash import draw_splash
from main_menu import run

_PIPELINE_MODULES = (
    "confirm",
    "dataset_picker",
    "results",
    "run_config",
    "training_monitor",
)


def _load_pipeline() -> None:
    """Import pipeline packages so missing or broken modules fail immediately."""
    for name in _PIPELINE_MODULES:
        importlib.import_module(name)


def main() -> None:
    _load_pipeline()
    draw_splash()
    run()


if __name__ == "__main__":
    main()
