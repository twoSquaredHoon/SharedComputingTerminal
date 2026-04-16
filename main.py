#!/usr/bin/env python3
"""
SharedComputing — single entry point.

Pipeline:
  1. Splash (:mod:`splash`)
  2. Main menu (:mod:`main_menu`)
       • **N** — :func:`dataset_picker.pick_dataset_folder` → :func:`run_config.run_interactive`
         → :func:`confirm.review_and_confirm`
       • **H** / **P** — stubs for history / predict
       • **Q** — quit

Run: ``python3 main.py``
"""

from __future__ import annotations

import os

# Same default as ``dataset_picker`` so curses UIs behave on minimal TERM.
if os.environ.get("TERM", "") not in ("xterm-256color", "xterm", "screen-256color"):
    os.environ["TERM"] = "xterm-256color"

from splash import draw_splash
from main_menu import run


def main() -> None:
    draw_splash()
    run()


if __name__ == "__main__":
    main()
