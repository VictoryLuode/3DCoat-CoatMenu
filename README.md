# CoatMenu

> Custom pop-up action menus for **3D-Coat** — at the cursor, from a hotkey.

CoatMenu is the 3D-Coat sibling of [Krita **MenuBelt**](https://github.com/VictoryLuode/Krita-Menubelt):
you build your own lists of 3D-Coat commands and scripts, then reach them from a
frameless overlay that appears where your cursor is.

Hold the hotkey, move to the entry you want, release — it runs.
`Esc` cancels. Clicking works too, if you prefer the mouse.

> **Status: early demo.** One hard-coded list built from 3D-Coat's own
> `CustomMenu` entries. Multi-list configuration, the radial pie and the
> drag-and-drop editor are still to come (see *Roadmap*).

## Demo

![CoatMenu overlay](docs/preview-popup.png)

*(preview rendered from real 3D-Coat data — the same list the extension builds
on this machine)*

## Install

**Requirements:** 3D-Coat 2025 (ships its own Python 3.11 + PySide6 — nothing to
install).

1. Clone or unzip this repository.
2. Run the installer:

   ```
   install\install.cmd
   ```

   or, from any Python 3.8+ interpreter:

   ```
   python install\install.py
   ```

   It copies the extension to `Documents\3DCoat\UserPrefs\Scripts\cExtensions\CoatMenu\`,
   writes the menu item to `Scripts\ExtraMenuItems\CoatMenu.xml` and appends one
   line to `Scripts\cExtensions\startup.txt` (the previous file is backed up
   first). Nothing outside 3D-Coat's user folder is touched.
3. Restart 3D-Coat.
4. Open **Scripts ▸ CoatMenu ▸ Show CoatMenu**.
5. Optional: bind a key to that item in **Preferences ▸ Hotkeys**. With a key
   bound, the overlay supports *hold to open, release to run*.

Uninstall:

```
install\install.cmd --uninstall
```

## How it works

* A `cExtension` loaded from `UserPrefs/Scripts/cExtensions/` pumps the Qt event
  loop once per frame — that is what keeps the overlay alive inside 3D-Coat's
  process.
* The overlay is a frameless, always-on-top `Qt.ToolTip` widget, never a normal
  window: no title bar, no taskbar entry, and it never takes focus away from
  3D-Coat.
* Keyboard is read with `GetAsyncKeyState` polling instead of `grabKeyboard()`,
  so 3D-Coat keeps receiving its own keys.
* Entries run through `coat.ui.cmd("$CommandID")`; script entries go through
  `coat.io.executeScript`.
* `Preferences/Options_Hotkeys.xml` is **read only** — CoatMenu never writes to
  it (that file is easy to corrupt).

## Roadmap

| Stage | Content |
|---|---|
| ✔ M1 | extension skeleton, cursor overlay, linear list, click/hold/`Esc`, installer, tests |
| M2 | `data/lists.json` + editor: multiple lists, submenus, separators, drag-and-drop, sources (10 commands, CMD functions, custom-menu entries, scripts) |
| M3 | radial pie renderer (same data, ≤8 entries), dwell submenus, flick mode |
| M4 | conflict detection, live preview, import/export, packaging, README polish |

## Tests

```
bash tests/run_tests.sh
```

Runs offscreen (no 3D-Coat needed) with 3D-Coat's bundled Python. Covers the
catalog/hotkey parsers, the installer (into a throwaway tree — it verifies that
other extensions are left untouched) and the overlay logic (hit testing, hover,
click-to-run, trigger-key release, `Esc`).

`tests/render_preview.py` renders the overlay against the real data on the
machine and writes the PNG used in this README.

## License

GPL-3.0. See [LICENSE](LICENSE).
