# SharedComputingTerminal — file guide

Short reference for what each source file in this repository is for. For **colors, typography, and UI patterns** used in the terminal UI, see [`DESIGN.md`](DESIGN.md).

---

## `main.py` — single entry (recommended)

**Role:** One command runs the full CLI flow in order.

**What it does**

1. Sets **`TERM`** for curses (same idea as `dataset_picker`) if needed.  
2. **`_load_pipeline()`** — imports **`confirm`**, **`dataset_picker`**, **`results`**, **`run_config`**, **`training_monitor`** so a bad install fails before the splash.  
3. **`splash.draw_splash()`** — boxed intro.  
4. **`main_menu.run()`** — menu (**N** → … → **`training_monitor.run_training_monitor()`**; **H** → **`results.show_results()`**; **Q** quits).

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

**Role:** Scroll-friendly text menu (raw key input): new run, results, predict, quit. **`N`** picks a dataset → **run config** → **confirm** → **training monitor**; **`H`** opens **`results.show_results()`**; **`Q`** exits.

**Run alone:** `python3 main_menu.py` (skips splash).

---

## `run_config.py` — training run settings

**Role:** After a dataset is chosen, collects **architecture** (one of `MODEL_CHOICES`, trained **from scratch** — not fine-tuning), **epochs**, **batch size**, **learning rate**, and **run name**. Curses UI matches `dataset_picker` styling; stdio fallback uses numbered choices.

**What it does**

- Saved JSON uses **`version`: 2** and **`training_mode`: `"from_scratch"`** so training code can rely on random init instead of pretrained weights.
- Reads **`DATASET_ROOT`** from the environment when set; otherwise asks for a folder path (or **`q`** to cancel).
- **`run_interactive(bump_first=True)`** — full-screen **curses** UI (same style as `dataset_picker`: color pairs, header + dividers); **`s`** save, **`q`** cancel, **Enter** edits the highlighted row. Falls back to line prompts if curses fails. Writes **`runtime/run_config.json`** and returns the config dict (or `None` if cancelled).
- **`load_config()`** / **`save_config()`** — helpers for other modules.

**Run alone:** `python3 run_config.py`

---

## `confirm.py` — review before run

**Role:** Read-only full-screen summary of the saved run (dataset, training mode, architecture, hyperparameters, paths) so the user can **confirm or cancel** before training is started later.

**What it does**

- **`review_and_confirm(cfg=None)`** — if ``cfg`` is omitted, loads **`runtime/run_config.json`**. Curses UI matches other screens; **`y`** / **Enter** confirm, **`n`** / **q** / **Esc** cancel. Stdio fallback if curses fails.
- Returns **`True`** if confirmed, **`False`** if cancelled or no config.

**Run alone:** `python3 confirm.py` (loads saved config if present).

---

## `training_monitor.py` — live training dashboard

**Role:** Full-screen **curses** view (stdio fallback) showing run name, architecture, epoch progress placeholder, loss / val metrics (stubbed until a trainer feeds updates), and status. Opens after the user confirms a run from **`confirm`**.

**What it does**

- **`run_training_monitor(cfg=None)`** — loads **`runtime/run_config.json`** if ``cfg`` is omitted. **q** / **Esc** leaves the screen (curses); stdio fallback asks for **Enter** after the summary.

**Run alone:** `python3 training_monitor.py` (requires an existing saved config).

---

## `results.py` — run history / metrics

**Role:** Browse rows from **`runtime/results.db`** table **`runs`** (same DB the menu footer uses for “last run”). Full-screen **curses** list with scroll; stdio fallback prints a numbered list.

**What it does**

- **`show_results()`** — loads recent runs (newest first). **↑↓** / **j** / **k** move selection when the list is long; **q** / **Esc** exits. If the DB is missing or empty, shows an empty state message.
- Column names are not fixed: any columns present are read; display prefers **`id`**, **`run_name`** / **`name`**, **`model_name`**, **`val_acc`**, **`created_at`** for the summary line.

**Run alone:** `python3 results.py`

---

## Generated / not source

| Path | Meaning |
|------|--------|
| `__pycache__/` | Python bytecode cache. Safe to delete; recreated on import/run. |

---

## Typical flow

1. **`python3 main.py`** — splash → menu → pickers as above.  
2. Or call **`splash.draw_splash()`**, then **`main_menu.run()`**, or **`dataset_picker.pick_dataset_folder()`** only from your own script.
