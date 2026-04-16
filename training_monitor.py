"""
Live training dashboard: same curses styling as ``run_config`` / ``confirm``.

Shows run config plus placeholder metrics until a training process feeds updates.
**q** / **Esc** exits the screen and returns to the caller.
"""

from __future__ import annotations

import curses
import os
import shutil
from typing import Any, Optional

from dataset_picker import (
    P_DIVIDER,
    P_HINT,
    P_NORMAL,
    P_TITLE,
    P_WARN,
    _cp,
    _fit_width,
    _init_curses_palette,
    addstr,
    divider_line,
)
from run_config import load_config

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


C_TITLE = fg(180, 50, 50)
C_DIVIDER = fg(120, 35, 35)
C_HINT = fg(110, 95, 95)
C_NORMAL = fg(200, 190, 190)


def _bump_stdio() -> None:
    import sys

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _run_monitor_curses(stdscr, cfg: dict[str, Any], result: dict[str, Any]) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.start_color()
    _init_curses_palette()

    run_name = str(cfg.get("run_name", ""))
    arch = str(cfg.get("model_name", ""))
    try:
        target_epochs = int(cfg.get("epochs", 0))
    except (TypeError, ValueError):
        target_epochs = 0

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 20:
            addstr(
                stdscr,
                0,
                0,
                _fit_width("Terminal too short (need height ≥ 20). Press any key.", max(0, w - 1)),
                _cp(P_WARN),
            )
            stdscr.getch()
            result["ok"] = False
            return

        addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            1,
            0,
            "  " + divider_line(max(0, w - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )
        addstr(stdscr, 2, 0, "  Training monitor", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            3,
            0,
            "  "
            + _fit_width(
                "Metrics update here when the training loop is connected. q / Esc: leave.",
                max(0, w - 4),
            ),
            _cp(P_HINT) | curses.A_DIM,
        )
        addstr(
            stdscr,
            4,
            0,
            "  " + divider_line(max(0, w - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )

        rows: list[tuple[str, str]] = [
            ("Run", run_name or "(empty)"),
            ("Architecture", arch or "—"),
            ("Epoch", f"0 / {target_epochs}" if target_epochs else "—"),
            ("Train loss", "—"),
            ("Val loss", "—"),
            ("Val accuracy", "—"),
            ("Status", "idle — trainer not connected"),
        ]

        label_w = 16
        y = 6
        for label, val in rows:
            if y >= h - 3:
                break
            prefix = f"  {label:<{label_w}}  "
            px = len(prefix)
            disp = _fit_width(val, max(0, w - px - 1))
            addstr(stdscr, y, 0, prefix, _cp(P_HINT) | curses.A_DIM)
            addstr(stdscr, y, px, disp, _cp(P_NORMAL))
            y += 1

        addstr(
            stdscr,
            h - 2,
            2,
            _fit_width("q / Esc: return", max(0, w - 4)),
            _cp(P_HINT) | curses.A_DIM,
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            result["ok"] = True
            return


def _run_monitor_stdio(cfg: dict[str, Any]) -> None:
    _bump_stdio()
    run_name = str(cfg.get("run_name", ""))
    arch = str(cfg.get("model_name", ""))
    try:
        te = int(cfg.get("epochs", 0))
    except (TypeError, ValueError):
        te = 0

    print()
    print(f"  {C_TITLE}{BOLD}Training monitor{RESET}")
    print(f"  {C_DIVIDER}{DIM}{divider_line(max(0, shutil.get_terminal_size().columns - 2))}{RESET}")
    print()
    print(f"  {C_HINT}{'Run':<16}{RESET}  {C_NORMAL}{run_name or '(empty)'}{RESET}")
    print(f"  {C_HINT}{'Architecture':<16}{RESET}  {C_NORMAL}{arch or '—'}{RESET}")
    print(f"  {C_HINT}{'Epoch':<16}{RESET}  {C_NORMAL}{'0 / ' + str(te) if te else '—'}{RESET}")
    print(f"  {C_HINT}{'Train loss':<16}{RESET}  {C_NORMAL}—{RESET}")
    print(f"  {C_HINT}{'Val loss':<16}{RESET}  {C_NORMAL}—{RESET}")
    print(f"  {C_HINT}{'Val accuracy':<16}{RESET}  {C_NORMAL}—{RESET}")
    print(f"  {C_HINT}{'Status':<16}{RESET}  {C_NORMAL}idle — trainer not connected{RESET}")
    print()


def run_training_monitor(cfg: Optional[dict[str, Any]] = None) -> None:
    """
    Show the training dashboard. Loads ``runtime/run_config.json`` if ``cfg`` is omitted.

    Blocks until the user leaves with **q** or **Esc** (curses) or **Enter** (stdio fallback).
    Does nothing if there is no config to display.
    """
    if cfg is None:
        cfg = load_config()
    if not cfg:
        return

    result: dict[str, Any] = {"ok": False}

    def _wrapped(stdscr) -> None:
        _run_monitor_curses(stdscr, cfg, result)

    try:
        os.environ.setdefault("NCURSES_NO_ALTERNATE_SCREEN", "1")
        curses.wrapper(_wrapped)
    except Exception:
        _run_monitor_stdio(cfg)
        input(f"  {C_HINT}Press Enter to continue…{RESET}  ")


if __name__ == "__main__":
    if load_config():
        run_training_monitor()
    else:
        print("No saved config — run run_config first.")
