# SharedComputingTerminal — file guide

Short reference for what each source file in this repository is for. For **colors, typography, and UI patterns** used in the terminal UI, see [`DESIGN.md`](DESIGN.md).

---

## `main.py` — single entry (recommended)

**Role:** One command runs the full CLI flow in order.

**What it does**

1. Sets **`TERM`** for curses (same idea as `dataset_picker`) if needed.  
2. **`splash.draw_splash()`** — boxed intro.  
3. **`main_menu.run()`** — menu (**N** → **`dataset_picker.pick_dataset_folder`** → **`run_config.run_interactive()`** → **`confirm.review_and_confirm()`**; **Q** quits).

**Run:** `python3 main.py`

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

## `main_menu.py` — main menu

**Role:** Scroll-friendly text menu (raw key input): new run, history, predict, quit. **`N`** picks a dataset → **run config** → **confirm** review screen; **`Q`** exits.

**Run alone:** `python3 main_menu.py` (skips splash).

---

## `run_config.py` — training run settings

**Role:** After a dataset is chosen, collects **model** (multiple-choice placeholders in `MODEL_CHOICES`), **epochs**, **batch size**, **learning rate**, and **run name**. Curses UI matches `dataset_picker` styling; stdio fallback uses numbered choices.

**What it does**

- Reads **`DATASET_ROOT`** from the environment when set; otherwise asks for a folder path (or **`q`** to cancel).
- **`run_interactive(bump_first=True)`** — full-screen **curses** UI (same style as `dataset_picker`: color pairs, header + dividers); **`s`** save, **`q`** cancel, **Enter** edits the highlighted row. Falls back to line prompts if curses fails. Writes **`runtime/run_config.json`** and returns the config dict (or `None` if cancelled).
- **`load_config()`** / **`save_config()`** — helpers for other modules.

**Run alone:** `python3 run_config.py`

---

## `confirm.py` — review before run

**Role:** Read-only full-screen summary of the saved run (dataset, model, hyperparameters, paths) so the user can **confirm or cancel** before training is started later.

**What it does**

- **`review_and_confirm(cfg=None)`** — if ``cfg`` is omitted, loads **`runtime/run_config.json`**. Curses UI matches other screens; **`y`** / **Enter** confirm, **`n`** / **q** / **Esc** cancel. Stdio fallback if curses fails.
- Returns **`True`** if confirmed, **`False`** if cancelled or no config.

**Run alone:** `python3 confirm.py` (loads saved config if present).

---

## Generated / not source

| Path | Meaning |
|------|--------|
| `__pycache__/` | Python bytecode cache. Safe to delete; recreated on import/run. |

---

## Typical flow

1. **`python3 main.py`** — splash → menu → pickers as above.  
2. Or call **`splash.draw_splash()`**, then **`main_menu.run()`**, or **`dataset_picker.pick_dataset_folder()`** only from your own script.
