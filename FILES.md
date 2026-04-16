# SharedComputingTerminal — file guide

Short reference for what each source file in this repository is for. For **colors, typography, and UI patterns** used in the terminal UI, see [`DESIGN.md`](DESIGN.md).

---

## `splash.py` — intro / splash screen

**Role:** Terminal welcome screen: boxed banner, title, version, tagline, and credits.

**What it does**

- Sizes a rounded **Unicode box** (`╭╮╰╯`, `─`, `│`) to the current terminal width (`shutil.get_terminal_size()`).
- Pads each inner row so vertical bars align (ANSI sequences stripped when measuring visible width).
- Uses **24-bit ANSI** red for the frame and title, **dim** for secondary lines (version, tagline, credits).
- When run as main (`python splash.py`), shows the splash then waits for **Enter** before exiting.

**Main API:** `draw_splash()` — call from a launcher to show the intro without blocking (unless you add your own `input()`).

---

## `dataset_picker.py` — dataset folder picker

**Role:** Interactive selection of a **dataset root directory** where each **class** is a subfolder containing images.

**What it does**

- **`pick_dataset_folder()`** — Full-screen **curses** tree starting at the user’s home: expand/collapse with arrows, move with vim-style or arrow keys, **Enter** to confirm, **q** to cancel. Returns a `Path` to the chosen folder, or `None` if cancelled.
- **`validate_dataset(path)`** — Returns whether the folder meets rules: at least one subfolder; every subfolder must contain at least one image (extensions: jpg, jpeg, png, bmp, gif, tiff, webp). Also returns class names, counts, error text, and optional warnings (e.g. imbalance, low count).
- **Colors in curses** use `init_color` / `init_pair` (not raw ANSI inside `addstr`) so the grid stays aligned with the terminal.
- If curses fails, **falls back** to typed path + ANSI-colored `print` / `input` until a valid dataset path is entered or the user aborts.

**Run alone:** `python dataset_picker.py` prints the final selection or cancellation.

---

## `main_menu.py` — main menu (optional)

**Role:** Text menu with raw key input for actions such as new run, history, predict, quit. Present in the repo as a separate entry point; wire it to `splash` / `dataset_picker` in your own `main` script if needed.

---

## Generated / not source

| Path | Meaning |
|------|--------|
| `__pycache__/` | Python bytecode cache. Safe to delete; recreated on import/run. |

---

## Typical flow

1. **`splash.draw_splash()`** — show intro (optionally wait for the user).
2. **`dataset_picker.pick_dataset_folder()`** — choose and validate a dataset root for training or tooling.
