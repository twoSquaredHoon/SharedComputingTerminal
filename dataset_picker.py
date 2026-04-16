import curses
import os
from pathlib import Path

if os.environ.get("TERM", "") not in ("xterm-256color", "xterm", "screen-256color"):
    os.environ["TERM"] = "xterm-256color"

IMAGE_EXTS   = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"}
SYSTEM_FILES = {".ds_store", "thumbs.db", "desktop.ini"}

# ── ANSI 24-bit foreground helpers ────────────────────────────────────────────
def fg(r, g, b):       return f"\033[38;2;{r};{g};{b}m"
def bold():            return "\033[1m"
def dim():             return "\033[2m"
def reset():           return "\033[0m"

# Palette — foreground only, works on any terminal background
C_TITLE    = fg(180, 50,  50)   # muted dark red — app title
C_DIVIDER  = fg(120, 35,  35)   # darker red — divider lines
C_SELECTED = fg(220, 110, 110)  # soft red-pink — highlighted row
C_NORMAL   = fg(200, 190, 190)  # warm off-white — tree rows
C_HINT     = fg(110, 95,  95)   # muted grey-red — hints / subtitles
C_SUCCESS  = fg(80,  180, 100)  # green — validation passed
C_WARN     = fg(200, 160, 60)   # amber — warnings / errors
C_ICON     = fg(160, 55,  55)   # red — folder icons, arrows

DIVIDER = "─" * 55

# Curses color pairs (after init_curses_palette in pick_dataset_folder)
P_TITLE, P_DIVIDER, P_HINT, P_SELECTED, P_NORMAL, P_ICON, P_SUCCESS, P_WARN = range(1, 9)


def _fit_width(text: str, width: int) -> str:
    """Slice text to at most width chars; width <= 0 yields empty (never negative slice)."""
    return text[: max(0, width)]


def _init_curses_palette() -> None:
    """Map RGB-ish colors to curses pairs. ANSI in addstr() breaks ncurses cell accounting."""
    specs = [
        (P_TITLE, 16, (180, 50, 50)),
        (P_DIVIDER, 17, (120, 35, 35)),
        (P_HINT, 18, (110, 95, 95)),
        (P_SELECTED, 19, (220, 110, 110)),
        (P_NORMAL, 20, (200, 190, 190)),
        (P_ICON, 21, (160, 55, 55)),
        (P_SUCCESS, 22, (80, 180, 100)),
        (P_WARN, 23, (200, 160, 60)),
    ]
    fallback = [
        (P_TITLE, curses.COLOR_RED),
        (P_DIVIDER, curses.COLOR_RED),
        (P_HINT, curses.COLOR_WHITE),
        (P_SELECTED, curses.COLOR_MAGENTA),
        (P_NORMAL, curses.COLOR_WHITE),
        (P_ICON, curses.COLOR_RED),
        (P_SUCCESS, curses.COLOR_GREEN),
        (P_WARN, curses.COLOR_YELLOW),
    ]
    try:
        if curses.can_change_color():
            for pair, cid, rgb in specs:
                r, g, b = rgb
                curses.init_color(cid, r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
                curses.init_pair(pair, cid, -1)
            return
    except curses.error:
        pass
    for pair, c in fallback:
        try:
            curses.init_pair(pair, c, -1)
        except curses.error:
            pass


def _cp(pair: int) -> int:
    return curses.color_pair(pair)


# ── curses addstr (no ANSI — use attrs / color_pair only) ──────────────────
def addstr(stdscr, y, x, text, attr=0):
    """Write text at (y, x). Silently clips if out of bounds."""
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def _put(stdscr, y, x, text, attr, max_x: int) -> int:
    """Draw text starting at x; clip to max_x (exclusive). Returns next x."""
    if x >= max_x or not text:
        return x
    clipped = _fit_width(text, max_x - x)
    if clipped:
        addstr(stdscr, y, x, clipped, attr)
        return x + len(clipped)
    return x


class FolderNode:
    def __init__(self, path: Path, depth: int = 0):
        self.path     = path
        self.depth    = depth
        self.expanded = False
        self.children = None

    def load_children(self):
        if self.children is not None:
            return
        try:
            dirs = sorted(
                [p for p in self.path.iterdir() if p.is_dir() and not p.name.startswith(".")],
                key=lambda p: p.name.lower(),
            )
            self.children = [FolderNode(d, self.depth + 1) for d in dirs]
        except PermissionError:
            self.children = []

    def has_children(self):
        self.load_children()
        return len(self.children) > 0


def flatten(node: FolderNode, result: list):
    result.append(node)
    if node.expanded and node.children:
        for child in node.children:
            flatten(child, result)


def validate_dataset(path: Path):
    """
    Returns (valid, classes, total_images, error_msg, warnings)

    Hard rules — blocks selection:
      - At least 1 subfolder
      - Every subfolder must contain at least 1 image

    Soft warnings — shown but don't block:
      - Class imbalance (one class has 10x another)
      - Very low total image count (< 20)
    """
    try:
        subdirs = sorted(
            [p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")],
            key=lambda p: p.name.lower(),
        )

        if not subdirs:
            return False, [], 0, "No subfolders found — each class needs its own subfolder.", []

        classes    = []
        counts     = {}
        empty_dirs = []

        for d in subdirs:
            imgs = [
                f for f in d.iterdir()
                if f.is_file()
                and f.suffix.lower() in IMAGE_EXTS
                and f.name.lower() not in SYSTEM_FILES
            ]
            if not imgs:
                empty_dirs.append(d.name)
            else:
                classes.append(d.name)
                counts[d.name] = len(imgs)

        if empty_dirs:
            return False, [], 0, (
                f"Empty class folder(s): {', '.join(empty_dirs)}\n"
                f"   Every subfolder must contain at least one image."
            ), []

        total    = sum(counts.values())
        warnings = []

        if total < 20:
            warnings.append(f"Only {total} images total — model may not train well.")

        if len(classes) > 1:
            mn = min(counts.values())
            mx = max(counts.values())
            if mx >= mn * 10:
                lo = min(counts, key=counts.get)
                hi = max(counts, key=counts.get)
                warnings.append(
                    f"Class imbalance: '{hi}' ({counts[hi]} imgs) vs '{lo}' ({counts[lo]} imgs)."
                )

        return True, classes, total, None, warnings

    except PermissionError:
        return False, [], 0, "Permission denied — cannot read this folder.", []
    except Exception as e:
        return False, [], 0, str(e), []


def pick_dataset_folder() -> Path:
    root_path = Path.home()
    root_node = FolderNode(root_path, depth=0)
    root_node.load_children()
    root_node.expanded = True

    result = {"path": None}

    def _tree(stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        curses.start_color()
        _init_curses_palette()

        cursor    = 0
        scroll    = 0
        message   = ""
        msg_ok    = True   # True = success color, False = warn color

        while True:
            stdscr.erase()
            h, w = stdscr.getmaxyx()

            # ── Header ────────────────────────────────────────────────────────
            addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
            addstr(
                stdscr, 1, 0,
                "  " + _fit_width(DIVIDER, max(0, w - 4)),
                _cp(P_DIVIDER) | curses.A_DIM,
            )
            addstr(stdscr, 2, 0, "  Select dataset folder", _cp(P_TITLE))
            addstr(
                stdscr, 3, 0,
                "  ↑↓ navigate   → expand   ← collapse   Enter select   q quit",
                _cp(P_HINT) | curses.A_DIM,
            )
            addstr(
                stdscr, 4, 0,
                "  " + _fit_width(DIVIDER, max(0, w - 4)),
                _cp(P_DIVIDER) | curses.A_DIM,
            )

            # ── Tree ──────────────────────────────────────────────────────────
            visible = []
            flatten(root_node, visible)

            cursor    = max(0, min(cursor, len(visible) - 1))
            list_rows = h - 8
            if cursor < scroll:
                scroll = cursor
            elif cursor >= scroll + list_rows:
                scroll = cursor - list_rows + 1

            for screen_row, i in enumerate(range(scroll, min(scroll + list_rows, len(visible)))):
                node = visible[i]
                y    = screen_row + 5

                indent   = "    " * node.depth
                has_kids = node.has_children()

                name = str(node.path) if node.depth == 0 else node.path.name
                x = 0
                if i == cursor:
                    sel = _cp(P_SELECTED) | curses.A_BOLD
                    x = _put(stdscr, y, x, "  ", sel, w)
                    x = _put(stdscr, y, x, indent, sel, w)
                    if node.expanded and has_kids:
                        x = _put(stdscr, y, x, "▼", _cp(P_ICON), w)
                        x = _put(stdscr, y, x, " ", sel, w)
                    elif has_kids:
                        x = _put(stdscr, y, x, "▶", _cp(P_ICON), w)
                        x = _put(stdscr, y, x, " ", sel, w)
                    else:
                        x = _put(stdscr, y, x, "  ", sel, w)
                    x = _put(stdscr, y, x, "📁 ", sel, w)
                    _put(stdscr, y, x, name, sel, w)
                else:
                    norm = _cp(P_NORMAL)
                    x = _put(stdscr, y, x, "  ", norm, w)
                    x = _put(stdscr, y, x, indent, norm, w)
                    if node.expanded and has_kids:
                        x = _put(stdscr, y, x, "▼", _cp(P_ICON), w)
                        x = _put(stdscr, y, x, " ", norm, w)
                    elif has_kids:
                        x = _put(stdscr, y, x, "▶", _cp(P_ICON), w)
                        x = _put(stdscr, y, x, " ", norm, w)
                    else:
                        x = _put(stdscr, y, x, "  ", norm, w)
                    x = _put(stdscr, y, x, "📁 ", _cp(P_HINT), w)
                    _put(stdscr, y, x, name, norm, w)

            # ── Bottom divider + message ───────────────────────────────────────
            div_y = h - 3
            if div_y > 5:
                addstr(
                    stdscr, div_y, 0,
                    "  " + _fit_width(DIVIDER, max(0, w - 4)),
                    _cp(P_DIVIDER) | curses.A_DIM,
                )

            if message:
                msg_attr = _cp(P_SUCCESS) if msg_ok else _cp(P_WARN)
                msg_y = h - 2
                for line in message.split("\n"):
                    if 0 <= msg_y < h:
                        addstr(stdscr, msg_y, 2, _fit_width(line, max(0, w - 4)), msg_attr)
                        msg_y += 1

            stdscr.refresh()

            # ── Input ─────────────────────────────────────────────────────────
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord("k")):
                cursor  = max(0, cursor - 1)
                message = ""

            elif key in (curses.KEY_DOWN, ord("j")):
                cursor  = min(len(visible) - 1, cursor + 1)
                message = ""

            elif key in (curses.KEY_RIGHT, ord("l")):
                node = visible[cursor]
                node.load_children()
                if node.children:
                    node.expanded = True
                message = ""

            elif key in (curses.KEY_LEFT, ord("h")):
                node = visible[cursor]
                if node.expanded:
                    node.expanded = False
                else:
                    target_depth = node.depth - 1
                    for j in range(cursor - 1, -1, -1):
                        if visible[j].depth == target_depth:
                            cursor = j
                            break
                message = ""

            elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
                node = visible[cursor]
                valid, classes, total, err, warnings = validate_dataset(node.path)
                if valid:
                    result["path"] = node.path
                    stdscr.erase()
                    _, w2 = stdscr.getmaxyx()
                    addstr(stdscr, 0, 0, "  SHAREDCOMPUTING", _cp(P_TITLE) | curses.A_BOLD)
                    addstr(
                        stdscr, 1, 0,
                        "  " + _fit_width(DIVIDER, max(0, w2 - 4)),
                        _cp(P_DIVIDER) | curses.A_DIM,
                    )
                    row = 2
                    addstr(stdscr, row, 2, f"✓  {node.path}", _cp(P_SUCCESS) | curses.A_BOLD)
                    row += 1
                    addstr(
                        stdscr, row, 2,
                        f"   Found {total} images across {len(classes)} class(es)",
                        _cp(P_SUCCESS),
                    )
                    row += 1
                    addstr(stdscr, row, 2, f"   {', '.join(classes)}", _cp(P_HINT))
                    row += 1
                    for warn in warnings:
                        row += 1
                        addstr(stdscr, row, 2, f"⚠  {warn}", _cp(P_WARN))
                        row += 1
                    stdscr.refresh()
                    curses.napms(2200)
                    return
                else:
                    message = f"⚠  {err}"
                    msg_ok  = False
                    node.load_children()
                    if node.children:
                        node.expanded = True

            elif key in (ord("q"), 27):
                result["path"] = None
                return

    try:
        curses.wrapper(_tree)
    except Exception as e:
        # Fallback: plain text with ANSI color
        print(f"\n{C_WARN}  (Tree picker unavailable: {e}){reset()}")
        while True:
            raw = input(f"\n{C_TITLE}  Dataset folder path:{reset()} ").strip()
            p   = Path(raw).expanduser().resolve()
            if not p.exists():
                print(f"{C_WARN}  ⚠  Path not found: {p}{reset()}")
                continue
            valid, classes, total, err, warnings = validate_dataset(p)
            if valid:
                print(f"{C_SUCCESS}  ✓  Found {total} images across {len(classes)} class(es){reset()}")
                print(f"{C_HINT}     {', '.join(classes)}{reset()}")
                for warn in warnings:
                    print(f"{C_WARN}  ⚠  {warn}{reset()}")
                result["path"] = p
                break
            else:
                print(f"{C_WARN}  ⚠  {err}{reset()}")

    return result["path"]


if __name__ == "__main__":
    chosen = pick_dataset_folder()
    if chosen:
        print(f"\n{C_SUCCESS}  Selected: {chosen}{reset()}")
    else:
        print(f"\n{C_HINT}  Cancelled.{reset()}")
