"""
Full-screen review of the saved run config before training (or other next steps).
Matches ``dataset_picker`` / ``run_config`` curses styling; stdio fallback if curses fails.
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
    P_SUCCESS,
    P_TITLE,
    P_WARN,
    _cp,
    _fit_width,
    _init_curses_palette,
    addstr,
    divider_line,
)
from run_config import CONFIG_PATH, load_config

# Rows shown in order (key in config -> label)
_REVIEW_ROWS: tuple[tuple[str, str], ...] = (
    ("run_name", "Run name"),
    ("dataset_root", "Dataset"),
    ("training_mode", "Training"),
    ("model_name", "Architecture"),
    ("epochs", "Epochs"),
    ("batch_size", "Batch size"),
    ("learning_rate", "Learning rate"),
    ("created_at", "Saved at (UTC)"),
)


def _bump_stdio() -> None:
    import sys

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _format_value(key: str, cfg: dict[str, Any]) -> str:
    if key == "training_mode":
        v = cfg.get("training_mode")
        if v in (None, ""):
            return "from scratch"
        return str(v)
    v = cfg.get(key, "")
    if v is None:
        return ""
    if key == "learning_rate" and isinstance(v, (int, float)):
        return str(v)
    return str(v)


def _run_confirm_curses(stdscr, cfg: dict[str, Any], result: dict[str, Any]) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.start_color()
    _init_curses_palette()

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 18:
            addstr(
                stdscr,
                0,
                0,
                _fit_width("Terminal too short (need height ≥ 18). Press any key.", max(0, w - 1)),
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
        addstr(stdscr, 2, 0, "  Review run", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            3,
            0,
            "  "
            + _fit_width(
                "Check everything below before starting. No edits here — go back in the menu if needed.",
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

        row = 6
        label_w = 16
        for key, label in _REVIEW_ROWS:
            if row >= h - 4:
                break
            val = _format_value(key, cfg)
            if not val and key == "dataset_root":
                val = "(empty)"
            prefix = f"  {label:<{label_w}}  "
            px = len(prefix)
            disp = _fit_width(val, max(0, w - px - 1))
            addstr(stdscr, row, 0, prefix, _cp(P_HINT) | curses.A_DIM)
            addstr(stdscr, row, px, disp, _cp(P_NORMAL))
            row += 1

        cfg_line = f"Config file: {CONFIG_PATH}"
        if row < h - 4:
            addstr(stdscr, row, 2, _fit_width(cfg_line, max(0, w - 4)), _cp(P_HINT) | curses.A_DIM)
            row += 1

        addstr(
            stdscr,
            h - 2,
            2,
            _fit_width(
                "y / Enter: confirm and proceed   n / q / Esc: cancel",
                max(0, w - 4),
            ),
            _cp(P_HINT) | curses.A_DIM,
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("y"), ord("Y"), curses.KEY_ENTER, ord("\n"), ord("\r")):
            result["ok"] = True
            return
        if key in (ord("n"), ord("N"), ord("q"), 27):
            result["ok"] = False
            return


def _run_confirm_stdio(cfg: dict[str, Any]) -> bool:
    _bump_stdio()
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

    def fg(r: int, g: int, b: int) -> str:
        return f"\033[38;2;{r};{g};{b}m"

    C_TITLE = fg(180, 50, 50)
    C_DIV = fg(120, 35, 35)
    C_HINT = fg(110, 95, 95)
    C_NORM = fg(200, 190, 190)

    w = shutil.get_terminal_size().columns
    rule_w = max(0, w - 2)
    print()
    print(f"  {C_TITLE}{BOLD}Review run{RESET}")
    print(f"  {C_DIV}{DIM}{'─' * rule_w}{RESET}")
    print()
    for key, label in _REVIEW_ROWS:
        val = _format_value(key, cfg)
        if not val and key == "dataset_root":
            val = "(empty)"
        print(f"  {C_HINT}{label:<16}{RESET}  {C_NORM}{val}{RESET}")
    print(f"\n  {C_HINT}{DIM}Config file:{RESET} {C_NORM}{CONFIG_PATH}{RESET}")
    print()
    raw = input(f"  {C_HINT}Proceed? [y/N]: {RESET}").strip().lower()
    return raw in ("y", "yes")


def review_and_confirm(cfg: Optional[dict[str, Any]] = None) -> bool:
    """
    Show a full-screen summary of ``cfg`` (or load from ``runtime/run_config.json`` if omitted).

    Returns ``True`` if the user confirms (ready to run), ``False`` if they cancel or there is
    nothing to show.
    """
    if cfg is None:
        cfg = load_config()
    if not cfg:
        return False

    result: dict[str, Any] = {"ok": False}

    def _wrapped(stdscr) -> None:
        _run_confirm_curses(stdscr, cfg, result)

    try:
        os.environ.setdefault("NCURSES_NO_ALTERNATE_SCREEN", "1")
        curses.wrapper(_wrapped)
    except Exception:
        return _run_confirm_stdio(cfg)

    return bool(result.get("ok"))


if __name__ == "__main__":
    c = load_config()
    if c:
        print("confirmed" if review_and_confirm(c) else "cancelled")
    else:
        print("No saved config — run run_config first.")
