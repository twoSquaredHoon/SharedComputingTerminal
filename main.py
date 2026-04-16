#!/usr/bin/env python3
"""
Single entry: splash → main menu → (e.g. dataset picker on New run).
Run:  python3 main.py
"""

from splash import DIM, RESET, draw_splash


def main() -> None:
    draw_splash()
    input(f"  {DIM}Press Enter to continue...{RESET}\n")

    from main_menu import run

    run()


if __name__ == "__main__":
    main()
