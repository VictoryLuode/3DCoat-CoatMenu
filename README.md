# CoatMenu

> Custom pop-up action menus for **3D-Coat** — at the cursor, from a hotkey.

CoatMenu is inspired by [Krita **MenuBelt**](https://github.com/VictoryLuode/Krita-Menubelt),
the menu plug-in I built for Krita earlier: you build your own menus out of 3D-Coat
commands, tools and scripts, then reach them from a frameless overlay that appears
where your cursor is.

Press the hotkey once: the menu appears and **stays** after you let the key go.
Click an entry to run it — in a pie you can also press its digit — or click
anywhere else / press `Esc` to close.

A **menu** is the thing you build. `List` and `Pie` are only the two forms it can
take.

## Demo

A menu opened as a list, and the same kind of menu as a radial pie — the wheel is
centred on the cursor, so every slot is the same distance away:

![A CoatMenu list and a CoatMenu pie](docs/demo-list-pie.jpg)

![A CoatMenu list opened at the cursor](docs/demo-quicktool.jpg)

The editor — every menu is a row on the left, the command catalog on the right:

![The CoatMenu editor](docs/demo-editor.jpg)

## Highlights

* **At the cursor** — a frameless, always-on-top overlay that never takes focus from
  3D-Coat.
* **Blender-style interaction** — the menu **stays** after you release the key: `↑`/`↓`
  + `Enter` drive it, `1..9` fire the N-th entry, `Esc` steps back one level.
* **Keys are 3D-Coat's business** — each menu is its own entry in `Scripts ▸ CoatMenu`;
  hover it and press `END`. CoatMenu only *reads* the hotkey file.
* **Rows *or* a pie, per menu** — a list hangs from the cursor, a pie is centred on it,
  its buttons round and evenly spaced, slots from straight up, clockwise.
* **`Expand` and `Position` per row** — a group's children stack in the slot or open a
  panel (Auto / Inline / Panel); a pie row can be pinned to a compass point.
* **Multi-step rows** — one row can fire several 3D-Coat commands in order, which is how
  primitives work; the bundled `Add` menu is built from that.
* **Nested submenus** — unfold on hover, with a grace timer (a short dwell in a pie);
  `Promote` turns one into a menu of its own.
* **Three lists on a first run** — `QuickTool`, `Add` and `Shade` (a pie); `+ New ▸
  Built-in lists` adds `Modeling`, `Tools`, `Common` or `Sculpt Ops`.
* **Editor** — rows from 3D-Coat's own commands (**900+**), your `CustomTools` and your
  scripts; drag to reorder, `Add all`, undo/redo, import/export.
* **Nothing ships that does nothing** — every id is checked against the 3D-Coat you are
  running, so a command your build does not have is left out.
* **Independent** — no other extension is required and none of its code ships here:
  `cExtensions` shares one interpreter, so everything keeps its own namespace.
* **Your menus are yours** — an update only adds a menu that is **missing**; nothing in
  your file is renamed, reordered or dropped.
* **Never touches your hotkeys file** — `Options_Hotkeys.xml` is opened read-only; it is
  easy to corrupt and 3D-Coat itself has done it before.
* **Diagnostics built in** — the editor shows each menu's key and flags two sharing one;
  `CoatMenu_Doctor` writes a report to `data/doctor.txt`.

## Install

**Requirements:** 3D-Coat 2025 (it ships its own Python 3.11 + PySide6 — nothing to
install). The installer itself only needs Python 3.8+, and it runs on 3D-Coat's own
interpreter when that can be found.

### Option 1 — the package file (two clicks, nothing to run)

1. Download `CoatMenu-<version>.3dcpack` from Releases.
2. In 3D-Coat: **Addons ▸ Install Extension** (older builds: **File ▸ Install
   extension**) and pick that file. 3D-Coat unpacks it into
   `Documents\3DCoat\UserPrefs\Scripts\cExtensions\CoatMenu\` and adds its own
   debug scaffolding (`.env`, `.vscode/`) the way it does for every extension.
3. **Windows ▸ Panels ▸ Extensions** → find `CoatMenu` → **Start**, or tick
   **Auto-Launch** to have it load with 3D-Coat from then on. A package can only add
   or replace *files*, so it cannot write that load line itself — the checkbox is
   3D-Coat's own switch for it.
4. Restart 3D-Coat once (the `Scripts ▸ CoatMenu` entries come from a menu file the
   extension writes on its first load).
5. Open **Scripts ▸ CoatMenu ▸ Show CoatMenu**.

This is the route with no archive to unzip, no Python and no `.cmd` for SmartScreen
to hold up. It is also the route that leaves everything else to you: no pruning of
what a previous version left behind, and no backup of your lists before an update.
Updating a copy that Option 2 installed? Use Option 2 for that update.

### Option 2 — the release zip and `install.cmd`

1. Download `CoatMenu-v<version>.zip` from Releases and unzip it anywhere.
2. Double-click `install\install.cmd` — it runs on 3D-Coat's own Python (any
   `python-*` folder inside 3D-Coat's data folder, whichever version it is), asks
   Windows where `Documents` is, and only falls back to the `py` launcher or a
   `python` on `PATH` after checking that the candidate actually runs. Nothing
   outside 3D-Coat's user folder is touched.
3. Restart 3D-Coat — or open **Windows ▸ Panels ▸ Extensions** and hit **Start** to
   avoid a restart.
4. Open **Scripts ▸ CoatMenu ▸ Show CoatMenu**.

### Binding a key

**Hover over the menu entry in `Scripts ▸ CoatMenu` and press `END`**, then press
the combination you want. That is 3D-Coat's own way of assigning a hotkey (its
hint text reads *"'END' - Define Hotkey"*) and it writes the binding itself.
CoatMenu only ever *reads* `Options_Hotkeys.xml`, to know which key opened a menu.

### Where 3D-Coat lives does not matter

Nothing here hard-codes a path:

| What | How it is found |
|---|---|
| 3D-Coat's user data | `coat.io.dataPath()` at runtime (checked for a `UserPrefs` folder, never assumed); the installer asks the registry where `Documents` is, then the usual spots (and OneDrive), and takes `--documents DIR` / `COATMENU_DOCUMENTS` |
| 3D-Coat's program folder | `coat.io.installPath()`, falling back to the path in the user folder's `executable.txt` |
| 3D-Coat's own Python | any `python-*` folder in its data folder; every candidate has to run before it is used |
| The extension itself | from its own location (inferred from `paths.py`) |

### Option 3 — from a checkout

1. Clone this repository (or unzip the release archive), then run the installer from
   the unzipped folder:

   ```
   install\install.cmd
   ```

   or, from any Python 3.8+ interpreter:

   ```
   python install\install.py
   ```

   It copies the extension to `Documents\3DCoat\UserPrefs\Scripts\cExtensions\CoatMenu\`,
   writes the menu item to `Scripts\ExtraMenuItems\CoatMenu.xml` and appends one
   line to `Scripts\cExtensions\startup.txt`. Each of those is backed up only when
   its content actually changes (the three most recent copies are kept). Nothing
   outside 3D-Coat's user folder is touched.
3. Restart 3D-Coat.
4. Open **Scripts ▸ CoatMenu ▸ Show CoatMenu** (or **Edit menus** to build yours).
5. Optional: in **Preferences ▸ Hotkeys**, bind a key to `Show CoatMenu` and to any
   `CoatMenu_<Menu>` entry.

Uninstall:

```
install\install.cmd --uninstall
```

Your `data/menus.json` is backed up next to the extension instead of being
deleted.

## How it works

* A `cExtension` loaded from `UserPrefs/Scripts/cExtensions/` pumps the Qt event
  loop once per frame — that is what keeps the overlay alive inside 3D-Coat's
  process.
* The overlay is a frameless, always-on-top `Qt.ToolTip` widget, never a normal
  window: no title bar, no taskbar entry, and it never takes focus away from
  3D-Coat.
* Keyboard is read with `GetAsyncKeyState` polling instead of `grabKeyboard()`, so
  3D-Coat keeps receiving its own keys.
* Entries run through `coat.ui.cmd("$CommandID")`; script entries go through
  `coat.io.executeScript`.
* Every menu gets a **generated launcher script**
  (`actions/menus/CoatMenu_<Menu>.py`), because a 3D-Coat menu item points at a
  file and one file cannot know which menu it belongs to. The three fixed entries
  (Show CoatMenu / Edit menus / Diagnostics) live in
  `Scripts/ExtraMenuItems/CoatMenu.xml`, which 3D-Coat reads at startup; the
  one-per-menu entries are registered at runtime with `coat.ui.insertInMenu`, so a
  menu built in the editor is usable without a restart. Writing them in both places
  would list every menu twice.
* 3D-Coat writes its **own** `ExtraMenuItems/<id>.xml` for every entry it is asked
  to insert, and never removes one - so a menu deleted in the editor used to stay in
  the Scripts list forever. Launching the extension (or running an install) deletes
  the copies whose menu is gone and takes those ids out of the running 3D-Coat; the
  three fixed entries are only ever in `CoatMenu.xml`, never inserted as well.
* Your menus live in `<ext>/data/menus.json`.
* The bundled lists are built from **3D-Coat's own data** at the moment they are
  made — its `cTemplates` menu files, its `English.xml` id table, your
  `CustomTools` — and every id in a curated list is looked up in that id table
  first, so a row is always something this build of 3D-Coat actually has.
* The command catalog is cached for the session, so switching source in the editor
  is instant (3D-Coat's 7711-entry translation table is parsed once).

## Roadmap

| Stage | Content |
|---|---|
| ✔ M1 | extension skeleton, cursor overlay, linear menu, click/hold/`Esc`, installer, tests |
| ✔ M2 | `data/menus.json`, several menus + submenus, editor (sources, drag-and-drop, import/export), generated launchers |
| ✔ M3 | radial pie renderer (same data), dwell submenus, per-menu list/pie switch |
| ✔ M4 | Blender-style interaction, live preview, tools/script sources, conflict detection, doctor report |
| ✔ M5 | packaging and polish: one-command release zip, changelog, README |
| ✔ M6 | per-row `Expand` and `Position`, a bundled `Sculpt Ops` list, independence from other extensions |

A screen-edge menu belt was considered and dropped — the overlay-at-the-cursor
idea covers the same ground with less to hit by accident.

## License

GPL-3.0. See [LICENSE](LICENSE).
