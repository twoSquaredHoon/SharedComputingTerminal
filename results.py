"""
Past run metrics: full-screen curses table (stdio fallback) over ``runtime/results.db``.

Expects a ``runs`` table (created by your training pipeline). Unknown columns are ignored;
**↑↓** / **j** / **k** scroll when the list is long. **q** / **Esc** exits.
"""

from __future__ import annotations

import curses
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from dataset_picker import (
    P_DIVIDER,
    P_HINT,
    P_ICON,
    P_NORMAL,
    P_SELECTED,
    P_TITLE,
    P_WARN,
    _cp,
    _fit_width,
    _init_curses_palette,
    addstr,
    divider_line,
)

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RESULTS_DB = Path("runtime") / "results.db"


def fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


C_TITLE = fg(180, 50, 50)
C_DIVIDER = fg(120, 35, 35)
C_HINT = fg(110, 95, 95)
C_NORMAL = fg(200, 190, 190)
C_WARN = fg(200, 160, 60)


def _bump_stdio() -> None:
    import sys

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _fetch_runs(limit: int = 200) -> list[dict[str, Any]]:
    """Load rows from ``runs`` as dicts, newest first. Returns ``[]`` if missing or error."""
    if not RESULTS_DB.is_file():
        return []
    try:
        con = sqlite3.connect(RESULTS_DB)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
        )
        if cur.fetchone() is None:
            con.close()
            return []
        cur.execute("PRAGMA table_info(runs)")
        cols = [r[1] for r in cur.fetchall()]
        order = "created_at DESC" if "created_at" in cols else "id DESC"
        cur.execute(f"SELECT * FROM runs ORDER BY {order} LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        con.close()
        return rows
    except (sqlite3.Error, OSError):
        return []


def _format_cell(key: str, val: Any) -> str:
    if val is None:
        return "—"
    if isinstance(val, float):
        if key in ("val_acc", "train_acc", "accuracy") or "acc" in key.lower():
            return f"{val:.4f}".rstrip("0").rstrip(".")
        return f"{val:.6f}".rstrip("0").rstrip(".")
    return str(val)


def _row_summary(d: dict[str, Any]) -> str:
    """One-line summary for a run dict for list display."""
    rid = d.get("id", "—")
    parts: list[str] = [f"run-{rid}"]
    for k in ("run_name", "name", "model_name", "architecture"):
        if k in d and d[k] and str(d[k]).strip():
            parts.append(str(d[k])[:40])
            break
    if "val_acc" in d and d["val_acc"] is not None:
        parts.append(f"val_acc {_format_cell('val_acc', d['val_acc'])}")
    elif "created_at" in d and d["created_at"] is not None:
        parts.append(str(d["created_at"])[:32])
    return "  ·  ".join(parts) if len(parts) > 1 else str(parts[0])


def _run_results_curses(stdscr, runs: list[dict[str, Any]], result: dict[str, Any]) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.start_color()
    _init_curses_palette()

    scroll = 0
    cursor = 0
    n = len(runs)

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 16:
            addstr(
                stdscr,
                0,
                0,
                _fit_width("Terminal too short (need height ≥ 16). Press any key.", max(0, w - 1)),
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
        addstr(stdscr, 2, 0, "  Results", _cp(P_TITLE) | curses.A_BOLD)
        hint = (
            "Past runs from runtime/results.db. ↑↓ j/k scroll · q / Esc: leave."
            if n
            else f"No runs table or no rows — expected {RESULTS_DB} with a runs table."
        )
        addstr(
            stdscr,
            3,
            0,
            "  " + _fit_width(hint, max(0, w - 4)),
            _cp(P_HINT) | curses.A_DIM,
        )
        addstr(
            stdscr,
            4,
            0,
            "  " + divider_line(max(0, w - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )

        list_top = 6
        list_rows = max(0, h - list_top - 2)

        if n == 0:
            addstr(
                stdscr,
                list_top,
                2,
                _fit_width("No runs to show.", max(0, w - 4)),
                _cp(P_HINT) | curses.A_DIM,
            )
        else:
            cursor = max(0, min(cursor, n - 1))
            if cursor < scroll:
                scroll = cursor
            elif cursor >= scroll + list_rows:
                scroll = cursor - list_rows + 1

            for i in range(list_rows):
                idx = scroll + i
                if idx >= n:
                    break
                y = list_top + i
                sel = idx == cursor
                attr = (_cp(P_SELECTED) | curses.A_BOLD) if sel else _cp(P_NORMAL)
                line = _row_summary(runs[idx])
                mark = "▶ " if sel else "  "
                addstr(stdscr, y, 2, mark, _cp(P_ICON))
                addstr(stdscr, y, 6, _fit_width(line, max(0, w - 8)), attr)

        addstr(
            stdscr,
            h - 2,
            2,
            _fit_width(
                f"↑↓ j/k move   {len(runs)} run(s)" if n else "",
                max(0, w - 4),
            ),
            _cp(P_HINT) | curses.A_DIM,
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27):
            result["ok"] = True
            return
        if n == 0:
            continue
        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(n - 1, cursor + 1)


def _run_results_stdio(runs: list[dict[str, Any]]) -> None:
    _bump_stdio()
    tw = max(0, shutil.get_terminal_size().columns - 2)
    print()
    print(f"  {C_TITLE}{BOLD}Results{RESET}")
    print(f"  {C_DIVIDER}{DIM}{divider_line(tw)}{RESET}")
    print()
    if not runs:
        print(f"  {C_WARN}No runs in {RESULTS_DB} (missing DB, empty table, or error).{RESET}")
        print()
        return
    for i, row in enumerate(runs):
        line = _row_summary(row)
        print(f"  {C_HINT}{i + 1:>3}.{RESET} {C_NORMAL}{line}{RESET}")
    print(f"\n  {C_HINT}{DIM}({len(runs)} run(s)){RESET}\n")


def show_results() -> None:
    """
    Show the results browser. Blocks until **q** or **Esc** (curses) or **Enter** (stdio).
    """
    runs = _fetch_runs()
    result: dict[str, Any] = {"ok": False}

    def _wrapped(stdscr) -> None:
        _run_results_curses(stdscr, runs, result)

    try:
        os.environ.setdefault("NCURSES_NO_ALTERNATE_SCREEN", "1")
        curses.wrapper(_wrapped)
    except Exception:
        _run_results_stdio(runs)
        input(f"  {C_HINT}Press Enter to continue…{RESET}  ")


if __name__ == "__main__":
    show_results()
