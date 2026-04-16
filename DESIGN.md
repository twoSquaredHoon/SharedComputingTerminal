# Terminal UI design — SharedComputing

This document describes the **color theme** and **visual style** used in `splash.py` (intro) and `dataset_picker.py` (folder picker). Both use **foreground-only** colors so they work on any terminal **background**.

---

## Color theme

Palette is built around a **muted red brand anchor**, **warm grey-red** neutrals, and **semantic** green / amber for status. `splash.py` uses the brand red plus dim text; `dataset_picker.py` uses the full table below (ANSI constants `C_*` for print fallback; the same RGBs map to curses pairs in the interactive UI).

### Brand and structure

| Role | RGB | Usage |
|------|-----|--------|
| **Title / brand** | `(180, 50, 50)` | App name, primary headings (`splash`: frame + “SharedComputing”; picker: “SHAREDCOMPUTING”, “Select dataset folder”). |
| **Divider** | `(120, 35, 35)` | Horizontal rules (`─`), section separation — darker than title. |
| **Icon / controls** | `(160, 55, 55)` | Tree arrows (`▶` / `▼`) and small UI glyphs. |

### Content hierarchy

| Role | RGB | Usage |
|------|-----|--------|
| **Selected row** | `(220, 110, 110)` | Highlighted tree line (with **bold** in curses). |
| **Normal body** | `(200, 190, 190)` | Non-selected folder names — warm off-white. |
| **Hint / secondary** | `(110, 95, 95)` | Help line, folder icon on normal rows, subtitles. |

### Semantic (status)

| Role | RGB | Usage |
|------|-----|--------|
| **Success** | `(80, 180, 100)` | Validation passed, success screen after selection. |
| **Warning** | `(200, 160, 60)` | Validation errors, warnings — amber. |

### Implementation notes

- **`splash.py`:** Single brand red `RED = "\033[38;2;180;50;50m"` for frame and title; `DIM` for secondary lines.
- **`dataset_picker.py`:** Curses UI uses **`color_pair` + `A_BOLD` / `A_DIM`** only (no raw ANSI in `addstr`). Fallback path uses the **`C_*`** ANSI helpers with `fg(r,g,b)`.

---

## Consistent design style

### Typography

- **Bold** — Brand title (“SharedComputing”, “SHAREDCOMPUTING”), **screen subtitles** on full-screen curses flows (“Configure run”, “Select dataset folder”, “Choose model”, field-editor title, “Review run”) — same `P_TITLE` + `A_BOLD` as the brand line so color stays stable across nested pickers — selected row, success headline, splash frame bars.
- **Dim** — Dividers, shortcut hint line, secondary copy (version, tagline on splash).

### Geometry and symbols

- **Horizontal rules:** Unicode **`─`** (U+2500). Build them with **`divider_line(width)`** in `dataset_picker.py` so every screen uses the same character and length logic:
  - **Full-screen curses** (picker, configure run, model list, field editor, review): two leading spaces, then `divider_line(max(0, w - 2))` so the rule fills the row (terminal width `w`).
  - **Scrollable stdio** (menu, configure / confirm fallbacks): two leading spaces, then `divider_line(max(0, columns - 2))` — same width math as curses.
- **Splash:** Rounded box **`╭` `╮` `╰` `╯`** with **`│`** sides; inner horizontal segments sized to terminal width.
- **Picker / config:** Two-space left margin before titles and rules; tree indent uses four spaces per depth level.

### Iconography

- **Emoji:** `📁` for folders, `✓` / `⚠` on status and messages — used sparingly.

### Layout principles

- **Width-aware** — Avoid negative string slices when clipping (`_fit_width`); narrow terminals stay safe.
- **No forced background** — Styling is **foreground color + weight** only.

---

## Quick reference (approximate hex)

| Role | RGB | ~Hex |
|------|-----|------|
| Title / brand | 180, 50, 50 | `#B43232` |
| Divider | 120, 35, 35 | `#782323` |
| Icon | 160, 55, 55 | `#A03737` |
| Selected | 220, 110, 110 | `#DC6E6E` |
| Normal | 200, 190, 190 | `#C8BEBE` |
| Hint | 110, 95, 95 | `#6E5F5F` |
| Success | 80, 180, 100 | `#50B464` |
| Warning | 200, 160, 60 | `#C8A03C` |

Use these when adding new screens so the CLI stays visually consistent.
