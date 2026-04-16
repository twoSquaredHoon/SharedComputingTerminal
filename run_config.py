"""
Training run configuration: full-screen curses UI (same style as dataset_picker),
with a line-oriented fallback if curses is unavailable.

Writes ``runtime/run_config.json`` and returns the config dict.
"""

from __future__ import annotations

import curses
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Reuse curses palette + drawing helpers from dataset_picker (no ANSI in addstr).
from dataset_picker import (
    P_DIVIDER,
    P_HINT,
    P_ICON,
    P_NORMAL,
    P_SELECTED,
    P_SUCCESS,
    P_TITLE,
    P_WARN,
    _cp,
    _fit_width,
    _init_curses_palette,
    addstr,
    divider_line,
    pick_dataset_folder,
)

# ── ANSI (stdio fallback only) ───────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


C_TITLE = fg(180, 50, 50)
C_DIVIDER = fg(120, 35, 35)
C_ICON = fg(160, 55, 55)
C_NORMAL = fg(200, 190, 190)
C_HINT = fg(110, 95, 95)
C_SUCCESS = fg(80, 180, 100)
C_WARN = fg(200, 160, 60)

RUNTIME_DIR = Path("runtime")
CONFIG_PATH = RUNTIME_DIR / "run_config.json"

# Placeholder model IDs until training code maps them to real architectures / weights.
MODEL_CHOICES: tuple[str, ...] = (
    "placeholder_resnet_style",
    "placeholder_vit_style",
    "placeholder_custom_head",
)

DEFAULTS: dict[str, Any] = {
    "model_name": MODEL_CHOICES[0],
    "epochs": 10,
    "batch_size": 32,
    "learning_rate": 0.001,
}


def _divider_width() -> int:
    w = shutil.get_terminal_size().columns
    return max(0, w - 2)


def _draw_divider() -> None:
    n = _divider_width()
    print(f"  {C_DIVIDER}{DIM}{divider_line(n)}{RESET}")


def _bump() -> None:
    import sys

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _dataset_root() -> Optional[Path]:
    raw = os.environ.get("DATASET_ROOT", "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    return p if p.is_dir() else None


def build_config(
    *,
    dataset_root: Optional[Path],
    model_name: str,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    run_name: str,
) -> dict[str, Any]:
    root = str(dataset_root.resolve()) if dataset_root else ""
    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_name": run_name,
        "dataset_root": root,
        "model_name": model_name,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
    }


def save_config(cfg: dict[str, Any]) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return CONFIG_PATH


def load_config() -> Optional[dict[str, Any]]:
    if not CONFIG_PATH.is_file():
        return None
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_line_cancelable(
    stdscr, y: int, x: int, max_len: int, initial: str
) -> Optional[str]:
    """
    Single-line edit without curses echo; **Enter** applies, **Esc** returns ``None``.
    ASCII + backspace only (matches typical curses input).
    """
    buf = list(_fit_width(initial, max_len))
    pos = len(buf)
    curses.curs_set(1)
    curses.noecho()
    try:
        while True:
            stdscr.move(y, x)
            stdscr.clrtoeol()
            s = "".join(buf)
            addstr(stdscr, y, x, _fit_width(s + " ", max_len + 1), _cp(P_NORMAL))
            stdscr.move(y, x + min(pos, len(s)))
            ch = stdscr.getch()
            if ch == 27:  # Esc
                return None
            if ch in (10, 13):
                return "".join(buf)
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if pos > 0:
                    pos -= 1
                    del buf[pos]
            elif ch == curses.KEY_LEFT and pos > 0:
                pos -= 1
            elif ch == curses.KEY_RIGHT and pos < len(buf):
                pos += 1
            elif ch == curses.KEY_HOME:
                pos = 0
            elif ch == curses.KEY_END:
                pos = len(buf)
            elif 32 <= ch < 127 and len(buf) < max_len:
                ch = chr(ch)
                buf.insert(pos, ch)
                pos += 1
    finally:
        curses.curs_set(0)


_FIELD_HINTS: dict[str, str] = {
    "dataset": "Absolute path to dataset root (folder with one subfolder per class). Leave empty if unset.",
    "epochs": "Integer ≥ 1.",
    "batch_size": "Integer ≥ 1.",
    "learning_rate": "Positive floating-point number.",
    "run_name": "Label for this run (logs / checkpoints).",
}


def _validate_and_normalize_field(key_name: str, raw: str) -> tuple[bool, str, str]:
    """Returns (ok, normalized_value_string, error_message)."""
    s = raw.strip()
    if key_name == "dataset":
        if not s:
            return True, "", ""
        p = Path(s).expanduser().resolve()
        if not p.is_dir():
            return False, "", "Path is not an existing directory."
        return True, str(p), ""
    if key_name == "model_name":
        if s not in MODEL_CHOICES:
            return False, "", "Choose one of the listed models."
        return True, s, ""
    if key_name == "epochs":
        try:
            v = int(s)
        except ValueError:
            return False, "", "Must be an integer."
        if v < 1:
            return False, "", "Must be ≥ 1."
        return True, str(v), ""
    if key_name == "batch_size":
        try:
            v = int(s)
        except ValueError:
            return False, "", "Must be an integer."
        if v < 1:
            return False, "", "Must be ≥ 1."
        return True, str(v), ""
    if key_name == "learning_rate":
        try:
            v = float(s)
        except ValueError:
            return False, "", "Must be a number."
        if v <= 0:
            return False, "", "Must be > 0."
        return True, str(v), ""
    if key_name == "run_name":
        if not s:
            return False, "", "Run name cannot be empty."
        return True, s, ""
    return True, s, ""


def _run_model_pick(stdscr, state: dict[str, str]) -> None:
    """Full-screen list to choose one of ``MODEL_CHOICES``. Esc restores the previous value."""
    old = state["model_name"]
    try:
        pick = MODEL_CHOICES.index(old.strip())
    except ValueError:
        pick = 0
    n = len(MODEL_CHOICES)
    need_h = 10 + n

    while True:
        h, w = stdscr.getmaxyx()
        if h < need_h:
            stdscr.erase()
            addstr(
                stdscr,
                0,
                0,
                _fit_width(f"Terminal too short (need height ≥ {need_h}). Press any key.", max(0, w - 1)),
                _cp(P_WARN),
            )
            stdscr.getch()
            state["model_name"] = old
            return

        stdscr.erase()
        addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            1,
            0,
            "  " + divider_line(max(0, w - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )
        addstr(stdscr, 2, 0, "  Choose model", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            3,
            0,
            "  "
            + _fit_width(
                "Placeholder options — replace IDs when real models are wired up.",
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
        row0 = 6
        for i, name in enumerate(MODEL_CHOICES):
            y = row0 + i
            if y >= h - 3:
                break
            sel = i == pick
            attr = (_cp(P_SELECTED) | curses.A_BOLD) if sel else _cp(P_NORMAL)
            mark = "▶ " if sel else "  "
            addstr(stdscr, y, 4, mark, _cp(P_ICON))
            addstr(stdscr, y, 8, _fit_width(name, max(0, w - 10)), attr)

        addstr(
            stdscr,
            h - 2,
            2,
            _fit_width(
                "↑↓ j/k move   Enter: choose   Esc: cancel",
                max(0, w - 4),
            ),
            _cp(P_HINT) | curses.A_DIM,
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            pick = max(0, pick - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            pick = min(n - 1, pick + 1)
        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            state["model_name"] = MODEL_CHOICES[pick]
            return
        elif key in (ord("q"), 27):
            state["model_name"] = old
            return


def _run_field_popup(
    stdscr,
    label: str,
    key_name: str,
    state: dict[str, str],
) -> None:
    """Full-screen sub-view for editing one field; Esc discards, Enter applies after validation."""
    old = state[key_name]
    hint = _FIELD_HINTS.get(key_name, "")
    h, w = stdscr.getmaxyx()
    if h < 14:
        return

    edit_y = min(h - 5, 14)
    max_w = max(8, w - 8)
    err_msg = ""

    while True:
        stdscr.erase()
        hh, ww = stdscr.getmaxyx()
        addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            1,
            0,
            "  " + divider_line(max(0, ww - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )
        title = f"Edit · {label}"
        addstr(stdscr, 2, 0, "  " + _fit_width(title, max(0, ww - 4)), _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            3,
            0,
            "  " + _fit_width(hint, max(0, ww - 4)),
            _cp(P_HINT) | curses.A_DIM,
        )
        addstr(
            stdscr,
            4,
            0,
            "  " + divider_line(max(0, ww - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )
        addstr(stdscr, 5, 2, "Previous value", _cp(P_HINT) | curses.A_DIM)
        prev_disp = old.replace("\n", " ") if old else "(empty)"
        addstr(stdscr, 6, 4, _fit_width(prev_disp, max(0, ww - 8)), _cp(P_NORMAL))

        addstr(stdscr, 8, 2, "New value", _cp(P_ICON) | curses.A_BOLD)
        if err_msg:
            addstr(
                stdscr,
                9,
                4,
                _fit_width(err_msg, max(0, ww - 8)),
                _cp(P_WARN),
            )
            edit_row = 11
        else:
            edit_row = 10
        if edit_row + 2 >= hh:
            edit_row = hh - 6

        addstr(
            stdscr,
            hh - 2,
            2,
            _fit_width("Enter: apply   Esc: cancel and keep previous value", max(0, ww - 4)),
            _cp(P_HINT) | curses.A_DIM,
        )

        stdscr.refresh()
        raw = _read_line_cancelable(stdscr, edit_row, 4, max_w, state[key_name])
        if raw is None:
            state[key_name] = old
            return

        ok, normalized, err = _validate_and_normalize_field(key_name, raw)
        if ok:
            state[key_name] = normalized
            return
        err_msg = err
        # keep state[key_name] unchanged for next edit pass; show typed attempt in field
        state[key_name] = raw


def _run_dataset_picker_and_resume():
    """Suspend configure UI, run dataset tree picker, return a fresh stdscr and chosen path."""
    curses.endwin()
    chosen = pick_dataset_folder()
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    try:
        stdscr.keypad(True)
    except curses.error:
        pass
    curses.use_default_colors()
    curses.start_color()
    _init_curses_palette()
    return stdscr, chosen


def _run_config_curses(stdscr, result: dict[str, Any]) -> None:
    curses.curs_set(0)
    curses.use_default_colors()
    curses.start_color()
    _init_curses_palette()

    ds = _dataset_root()
    default_run = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    # field_id -> string value (parse ints/float on save)
    state = {
        "dataset": str(ds) if ds else "",
        "model_name": str(DEFAULTS["model_name"]),
        "epochs": str(int(DEFAULTS["epochs"])),
        "batch_size": str(int(DEFAULTS["batch_size"])),
        "learning_rate": str(float(DEFAULTS["learning_rate"])),
        "run_name": default_run,
    }

    labels = [
        ("Dataset root", "dataset", True),
        ("Model", "model_name", False),
        ("Epochs", "epochs", False),
        ("Batch size", "batch_size", False),
        ("Learning rate", "learning_rate", False),
        ("Run name", "run_name", False),
    ]
    n_fields = len(labels)
    cursor = 0
    msg = ""
    msg_warn = False

    def draw() -> None:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            1,
            0,
            "  " + divider_line(max(0, w - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )
        addstr(stdscr, 2, 0, "  Configure run", _cp(P_TITLE) | curses.A_BOLD)
        addstr(
            stdscr,
            3,
            0,
            "  ↑↓ navigate   Enter (dataset→folder tree)   s save   q cancel",
            _cp(P_HINT) | curses.A_DIM,
        )
        addstr(
            stdscr,
            4,
            0,
            "  " + divider_line(max(0, w - 2)),
            _cp(P_DIVIDER) | curses.A_DIM,
        )

        row = 5
        for i, (lab, key, _ro) in enumerate(labels):
            sel = cursor == i
            attr = (_cp(P_SELECTED) | curses.A_BOLD) if sel else _cp(P_NORMAL)
            val = state[key]
            disp = _fit_width(val, max(0, w - 26))
            line = f"  {lab:<18}  {disp}"
            addstr(stdscr, row, 0, _fit_width(line, w), attr)
            row += 1

        hint_y = h - 3
        if 0 <= hint_y < h:
            addstr(
                stdscr,
                hint_y,
                0,
                "  "
                + _fit_width(
                    "Enter: full-screen editor (dataset row opens folder tree)",
                    max(0, w - 4),
                ),
                _cp(P_HINT) | curses.A_DIM,
            )
        if msg and h - 2 >= 0:
            ma = _cp(P_WARN) if msg_warn else _cp(P_HINT)
            addstr(stdscr, h - 2, 2, _fit_width(msg, max(0, w - 4)), ma)

        stdscr.refresh()

    while True:
        h, w = stdscr.getmaxyx()
        if h < 16:
            stdscr.erase()
            addstr(
                stdscr,
                0,
                0,
                _fit_width("Terminal too small (need height ≥ 16). Press any key.", max(0, w - 1)),
                _cp(P_WARN),
            )
            stdscr.getch()
            result["cfg"] = None
            return

        draw()
        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            cursor = max(0, cursor - 1)
            msg = ""
        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(n_fields - 1, cursor + 1)
            msg = ""
        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            lab, key_name, _ = labels[cursor]
            if key_name == "model_name":
                _run_model_pick(stdscr, state)
            elif key_name == "dataset":
                stdscr, p = _run_dataset_picker_and_resume()
                if p is not None:
                    state["dataset"] = str(p.resolve())
                    os.environ["DATASET_ROOT"] = str(p.resolve())
            else:
                _run_field_popup(stdscr, lab, key_name, state)
            msg = ""
        elif key in (ord("q"), 27):
            result["cfg"] = None
            return
        elif key in (ord("s"), ord("S")):
            # validate + save
            ds_path: Optional[Path] = None
            dr = state["dataset"].strip()
            if dr:
                p = Path(dr).expanduser().resolve()
                if p.is_dir():
                    ds_path = p
                else:
                    msg, msg_warn = "Dataset path is not a directory.", True
                    continue
            try:
                ep = int(state["epochs"].strip())
                bs = int(state["batch_size"].strip())
                lr = float(state["learning_rate"].strip())
            except ValueError:
                msg, msg_warn = "Epochs / batch / learning rate must be numbers.", True
                continue
            if ep < 1 or bs < 1:
                msg, msg_warn = "Epochs and batch size must be ≥ 1.", True
                continue
            if lr <= 0:
                msg, msg_warn = "Learning rate must be > 0.", True
                continue
            rn = state["run_name"].strip() or default_run
            mn = state["model_name"].strip()
            if mn not in MODEL_CHOICES:
                msg, msg_warn = "Choose a model from the list (Enter on Model).", True
                continue
            cfg = build_config(
                dataset_root=ds_path,
                model_name=mn,
                epochs=ep,
                batch_size=bs,
                learning_rate=lr,
                run_name=rn,
            )
            save_config(cfg)
            result["cfg"] = cfg
            stdscr.erase()
            _, w2 = stdscr.getmaxyx()
            addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
            addstr(
                stdscr,
                1,
                0,
                "  " + divider_line(max(0, w2 - 2)),
                _cp(P_DIVIDER) | curses.A_DIM,
            )
            addstr(stdscr, 2, 2, f"✓  Saved  {CONFIG_PATH}", _cp(P_SUCCESS) | curses.A_BOLD)
            addstr(stdscr, 4, 2, f"Run: {rn}", _cp(P_NORMAL))
            stdscr.refresh()
            curses.napms(1800)
            return


def _prompt_model_choice_stdio() -> Optional[str]:
    """Numbered list for non-curses fallback; ``q`` cancels."""
    print(f"\n  {C_TITLE}{BOLD}Model{RESET}  {C_HINT}{DIM}(placeholders){RESET}\n")
    for i, m in enumerate(MODEL_CHOICES, 1):
        print(f"  {C_ICON}{i}{RESET}  {C_NORMAL}{m}{RESET}")
    raw = input(
        f"  {C_ICON}▸{RESET} {C_NORMAL}Choice 1-{len(MODEL_CHOICES)} "
        f"{C_HINT}{DIM}(or q cancel){RESET}{C_TITLE}› {RESET}"
    ).strip().lower()
    if raw == "q":
        return None
    if raw.isdigit():
        j = int(raw)
        if 1 <= j <= len(MODEL_CHOICES):
            return MODEL_CHOICES[j - 1]
    for m in MODEL_CHOICES:
        if raw == m.lower():
            return m
    print(f"  {C_WARN}⚠  Unknown choice — using {MODEL_CHOICES[0]}.{RESET}")
    return MODEL_CHOICES[0]


def _run_interactive_stdio(*, bump_first: bool = True) -> Optional[dict[str, Any]]:
    if bump_first:
        _bump()

    print(f"\n  {C_TITLE}{BOLD}Configure run{RESET}")
    _draw_divider()
    print()

    ds = _dataset_root()
    if ds:
        print(f"  {C_HINT}{DIM}dataset{RESET}  {C_NORMAL}{ds}{RESET}")
    else:
        print(f"  {C_WARN}⚠  DATASET_ROOT not set — pick a dataset from the menu first.{RESET}")
        print(f"  {C_HINT}{DIM}Continuing anyway; you can paste a path when asked.{RESET}")

    print(f"\n  {C_HINT}{DIM}Type q at the first field to cancel without saving.{RESET}\n")

    dataset_path = ds
    if dataset_path is None:
        print(f"\n  {C_HINT}{DIM}Opening dataset folder picker…{RESET}\n")
        chosen = pick_dataset_folder()
        if chosen is None:
            print(f"\n  {C_HINT}Cancelled.{RESET}\n")
            return None
        dataset_path = chosen
        os.environ["DATASET_ROOT"] = str(chosen.resolve())

    model = _prompt_model_choice_stdio()
    if model is None:
        print(f"\n  {C_HINT}Cancelled.{RESET}\n")
        return None

    epochs = _prompt_int("Epochs", int(DEFAULTS["epochs"]))
    batch = _prompt_int("Batch size", int(DEFAULTS["batch_size"]))
    lr = _prompt_float("Learning rate", float(DEFAULTS["learning_rate"]))

    default_name = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_name = _prompt_str("Run name", default_name)

    cfg = build_config(
        dataset_root=dataset_path,
        model_name=model,
        epochs=epochs,
        batch_size=batch,
        learning_rate=lr,
        run_name=run_name,
    )

    path = save_config(cfg)
    print()
    print(f"  {C_SUCCESS}✓  Saved{RESET} {C_NORMAL}{path}{RESET}")
    print(f"  {C_HINT}{DIM}Preview:{RESET}")
    for k, v in cfg.items():
        print(f"    {C_HINT}{k}{RESET}  {C_NORMAL}{v}{RESET}")
    print()
    return cfg


def _prompt_str(label: str, default: str) -> str:
    tail = f"{C_HINT}{DIM} [{default}]{RESET}" if default else ""
    raw = input(f"  {C_ICON}▸{RESET} {C_NORMAL}{label}{RESET} {tail}{C_TITLE}› {RESET}").strip()
    return raw if raw else default


def _prompt_int(label: str, default: int) -> int:
    s = _prompt_str(label, str(default))
    try:
        return int(s)
    except ValueError:
        print(f"  {C_WARN}⚠  Not an integer — using {default}.{RESET}")
        return default


def _prompt_float(label: str, default: float) -> float:
    s = _prompt_str(label, str(default))
    try:
        return float(s)
    except ValueError:
        print(f"  {C_WARN}⚠  Not a number — using {default}.{RESET}")
        return default


def run_interactive(*, bump_first: bool = True) -> Optional[dict[str, Any]]:
    """
    Full-screen curses UI (like ``dataset_picker``); falls back to stdin/print if curses fails.

    ``bump_first`` applies only to the stdio fallback (clears visible screen before prompts).
    """
    result: dict[str, Any] = {"cfg": None}

    def _wrapped(stdscr) -> None:
        _run_config_curses(stdscr, result)

    try:
        os.environ.setdefault("NCURSES_NO_ALTERNATE_SCREEN", "1")
        curses.wrapper(_wrapped)
    except Exception:
        return _run_interactive_stdio(bump_first=bump_first)

    return result["cfg"]


if __name__ == "__main__":
    run_interactive()
