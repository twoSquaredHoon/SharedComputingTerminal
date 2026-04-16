#!/usr/bin/env python3
"""
Single entry: splash → main menu → (e.g. dataset picker on New run).
Run:  python3 main.py
"""

from splash import draw_splash
from main_menu import bump_viewport_top, run


def main() -> None:
    bump_viewport_top()
    draw_splash()
    run()


if __name__ == "__main__":
    main()
