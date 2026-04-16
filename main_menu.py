import os
import shutil
import sys
import termios
import tty

RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"


def fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


# Shared with splash / dataset_picker (DESIGN.md)
C_TITLE   = fg(180, 50, 50)   # brand
C_DIVIDER = fg(120, 35, 35)   # rules
C_ICON    = fg(160, 55, 55)   # hotkeys
C_NORMAL  = fg(200, 190, 190)  # primary labels
C_HINT    = fg(110, 95, 95)   # descriptions / subtitles
C_SUCCESS = fg(80, 180, 100)  # confirmation
C_WARN    = fg(200, 160, 60)  # placeholders / cautions

MENU_ITEMS = [
    ("N", "new run",        "configure dataset, model, and start training"),
    ("H", "run history",    "browse past runs and compare metrics"),
    ("P", "predict",        "run inference on an image using a saved model"),
    ("Q", "quit",           "exit sharedcomputing"),
]

VALID_KEYS = {item[0].lower() for item in MENU_ITEMS}


def bump_viewport_top() -> None:
    """Clear the visible terminal and put the cursor at the top-left so the next output fills from the top.

    Uses CSI 2 J and CSI H only (not CSI 3 J), so scrollback is usually kept unlike some ``clear`` implementations.
    """
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def get_last_run_summary():
    db_path = os.path.join("runtime", "results.db")
    if not os.path.exists(db_path):
        return None
    try:
        import sqlite3
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute(
            "SELECT id, val_acc FROM runs ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        con.close()
        if row:
            run_id, val_acc = row
            if val_acc is not None:
                return f"last run: run-{run_id}  ·  val_acc {float(val_acc):.3f}"
            return f"last run: run-{run_id}"
    except Exception:
        pass
    return None


def get_dataset_summary():
    dataset_root = os.environ.get("DATASET_ROOT", os.path.join("data"))
    if not os.path.isdir(dataset_root):
        return "no dataset loaded"
    try:
        classes = [
            d for d in os.listdir(dataset_root)
            if os.path.isdir(os.path.join(dataset_root, d))
            and not d.startswith(".")
        ]
        if not classes:
            return "no dataset loaded"
        total = sum(
            len([
                f for f in os.listdir(os.path.join(dataset_root, c))
                if not f.startswith(".")
            ])
            for c in classes
        )
        return f"{os.path.basename(dataset_root)}  ·  {total:,} images  ·  {len(classes)} classes"
    except Exception:
        return "no dataset loaded"


def _divider_width() -> int:
    """Dash count so `  ───…` spans to the last terminal column (two leading spaces)."""
    w = shutil.get_terminal_size().columns
    return max(0, w - 2)


def draw_divider():
    n = _divider_width()
    line = "─" * n if n else ""
    print(f"  {C_DIVIDER}{DIM}{line}{RESET}")


def draw_menu():
    # Append like normal shell output — no full-screen clear (see DESIGN.md).
    print()
    draw_divider()
    print()

    dataset_info = get_dataset_summary()
    last_run     = get_last_run_summary()

    print(f"  {C_TITLE}{BOLD}SharedComputing{RESET}")
    print(f"  {C_HINT}{DIM}distributed image classifier{RESET}")
    print()
    draw_divider()
    print()

    for key, label, desc in MENU_ITEMS:
        print(
            f"  {C_ICON}{BOLD}{key}{RESET}  "
            f"{C_NORMAL}{label:<18}{RESET}  "
            f"{C_HINT}{desc}{RESET}"
        )

    print()
    draw_divider()
    print()

    print(f"  {C_HINT}{DIM}dataset   {RESET}{C_NORMAL}{dataset_info}{RESET}")

    if last_run:
        print(f"  {C_HINT}{DIM}run       {RESET}{C_NORMAL}{last_run}{RESET}")

    print()
    print(f"  {C_HINT}{DIM}press a key to select{RESET}")
    print()


def run():
    while True:
        draw_menu()

        while True:
            key = getch().lower()
            if key in VALID_KEYS:
                break
            print(f"\n  {C_HINT}{DIM}Unknown key — use n, h, p, or q.{RESET}\n")

        if key == "q":
            print(f"\n  {C_HINT}{DIM}goodbye.{RESET}\n")
            sys.exit(0)

        elif key == "n":
            from dataset_picker import pick_dataset_folder

            chosen = pick_dataset_folder()
            if chosen is not None:
                os.environ["DATASET_ROOT"] = str(chosen)
                print(
                    f"\n  {C_SUCCESS}✓  Dataset root:{RESET} {C_NORMAL}{chosen}{RESET}\n"
                )
                input(f"  {C_HINT}{DIM}Press Enter to return to the menu…{RESET}  ")

        elif key == "h":
            print(f"\n  {C_ICON}{DIM}→ loading run history…{RESET}\n")
            input(f"  {C_WARN}⚠  [run_history.py not connected yet — press enter to return]{RESET}  ")

        elif key == "p":
            print(f"\n  {C_ICON}{DIM}→ launching predict…{RESET}\n")
            input(f"  {C_WARN}⚠  [predict.py not connected yet — press enter to return]{RESET}  ")


if __name__ == "__main__":
    bump_viewport_top()
    run()
