# Changelog

All notable changes to CoatMenu. Versions are the git tags.

## v0.5.1 — 2026-09-20

### Fixed

- **Menu entries were not registered at all.** The previous change routed them
  through a menu-building hook that this 3D-Coat build never calls, and the
  registration function then died on a missing import before doing anything. Between
  the two, every per-menu entry disappeared — so a key bound to it did nothing,
  which is what "the shortcuts I set do not work" turned out to be. Entries are back
  on the runtime path (`coat.ui.insertInMenu`), and a key is applied immediately
  after its own entry. **Do not use v0.5.0** — install this instead.

## v0.5.0 — 2026-09-20

### Changed

- **A *menu* is the unit; `list` and `pie` are only how it opens.** Everything -
  code, UI, the config file (`data/lists.json` → `data/menus.json`) and its key
  (`"lists"` → `"menus"`) - follows that. Older files still load; the first save
  renames them in place.
- Pies are centred on the cursor (the way Blender's are) instead of hanging from
  it, so the pointer sits in the middle ring and every slot is the same distance
  away. Lists still open at the cursor.
- The editor opens in the middle of the screen: it is summoned from a menu entry,
  so there is no cursor to anchor to - and 3DCoat hides the pointer in brush mode.
- Script entries in 3DCoat's Scripts menu are labelled `CoatMenu_<Menu>`; entries
  left behind by older versions are cleaned up on startup.

### Added

- **Global keys on rows** — right-click a row ▸ *Set key…* gives it its own entry in
  3DCoat's Scripts menu, so it runs without opening the menu at all. Opt-in per row:
  a row without a key is not registered anywhere, so the Scripts list stays clean.
- **Menu keys in the editor** — a `Key:` button sets the key that opens a menu.
  3DCoat applies it on the next start, through its own `menu_hotkey` API, so
  `Options_Hotkeys.xml` is still only ever *read*. A key you set by hand in
  Preferences ▸ Hotkeys is never overridden.
- **Tool presets** as a menu source: your saved presets from
  `UserPrefs/Presets/*.xml`, applied with `AppOptions.ActivateToolPreset`.
- **Your tools** as a menu source (the `CustomTools` panel's tools, via their
  `[extension]<Name>` ids).
- **LKS menus** as a menu source: the LKS add-on's radial menus, imported
  read-only and rebuilt as CoatMenu menus.
- **`Common`** - the commands from 3DCoat's own Edit / View / Freeze / Symmetry /
  Hide / Layers menus, with the names 3DCoat shows.
- **Add all** and multi-select in the editor: a whole section lands in one click.
- **Undo/redo** (Ctrl+Z / Ctrl+Shift+Z) in the editor.
- Per-menu **launcher files** (`actions/menus/CoatMenu_<Menu>.py`).
- **Promote**: turn a submenu into a menu of its own, with its own hotkey.
- A row's right-click menu: duplicate, copy/move to another menu, insert below,
  promote, rename, delete.

### Fixed

- Registering a menu entry with `coat.ui.insertInMenu` made 3D-Coat write its own
  `CoatMenu_<id>.xml` next to ours. That file is read at startup too, so an entry
  could be listed twice. They are cleaned up on install and no longer created.
- Switching the editor's source took ~80ms (it re-parsed 3DCoat's 7711-entry
  translation table every time); it is cached now and effectively instant.
- Creating, renaming, reordering or deleting a menu did not mark the config
  dirty - the title never showed `*` and the change was easy to lose.
- The command catalog no longer lists other extensions' internal scripts as if
  they were yours.
- Commands that live in several room scripts (an uncommented copy used to win)
  now get the name 3DCoat shows.

## v0.4.0

- Live preview in the editor, hotkey display per menu, the doctor report, the
  first M4 items.
- Blender-style interaction: entries fire on mouse *release*, right-click
  cancels, `Esc` steps back one level at a time, submenus unfold on dwell.
- Long lists cap their height and scroll; the wheel and `↑`/`↓` drive them.

## v0.3.0

- Radial pie renderer: rounded buttons around a small centre ring, each showing
  its `1..9` shortcut, spacing derived so buttons cannot overlap. Small groups
  stack in place, like Blender's Shading pie.
- Per-menu switch between list and pie.

## v0.2.0

- `data/menus.json`, several menus each with its own hotkey, submenus.
- Built-in editor: command sources, drag-and-drop, import/export, save & apply.
- Generated launcher scripts, one per menu.

## v0.1.0

- First working build: cExtension skeleton, cursor overlay, linear menu,
  click/`Esc` handling, installer, test suite.
