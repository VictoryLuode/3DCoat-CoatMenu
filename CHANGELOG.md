# Changelog

All notable changes to CoatMenu. Versions are the git tags.

## v0.7.0 — 2026-09-23

### Added

- **A `.3dcpack` release artifact** (`install/build_pack.py`, built by
  `tools/make_release.py` with the zip). 3D-Coat installs one from *Addons ▸ Install
  Extension*: no archive to unzip, no Python, no unsigned `.cmd` for SmartScreen to
  hold up. A pack is a zip of `UserPrefs/...` paths, so it carries the extension's
  code and nothing else — the launchers, the `ExtraMenuItems` XML (absolute paths can
  only be written on the machine that runs it) and `data/menus.json` are written by
  the extension itself on first load, and `tests/test_pack.py` pins the pack's file
  set to exactly the one an install copies. Two things the format cannot do, both
  now documented instead of guessed at: it cannot append the `startup.txt` line that
  loads an extension (it only adds or replaces files — that is 3D-Coat's own
  Auto-Launch checkbox, once), and it cannot prune what an older version left
  behind. Both routes are in the README, and the on-machine install was verified
  against a renamed copy so the real install was never touched.
- **`tests/sync_defaults.py`** — the release step that keeps the shipped set honest:
  it compares `presets.DEFAULT_LISTS` row by row against the menus the installed
  extension is actually running, prints the differences with the ids this build does
  not define called out, and can print the paste-ready `*_MENU_ROWS` block. It only
  reports: the live copy is not automatically right (its Shade pie had three view
  ids spelled without the underscores 3DCoat uses), so syncing stays a decision.

### Fixed

- **Nothing generated ships any more, and the tests no longer dirty the checkout.**
  `coat_side/actions/menus/` holds launcher scripts built from *this* user's config,
  and both the installer and the release zip copied whatever happened to be sitting
  in that folder — a stray launcher for a menu nobody has went into every install and
  into the archive. The shipped set excludes it now (the folder is written at install
  and at run time) and `tests/test_pack.py` reads the shipped set directly. The
  launchers got in there because opening a menu inside a test ran the config through
  the sync that writes them, and the extension root was always the checkout:
  `paths.extension_root()` takes `COATMENU_EXTENSION_DIR` now, so a test writes to a
  throwaway folder, and the popup test asserts the checkout is untouched afterwards.
- **Two menus whose names slugify alike are two working menus again.** A menu's id
  (launcher file, command id, hotkey id) came from the plain slug, while the
  launcher file alone used the de-duplicated one: the second menu's launcher asked
  for `Cut_Fill-2`, nothing resolved it, and that menu could not be opened at all -
  it showed the index instead. The two also shared one command id, and the key
  lookup saw only one of them. `menus_registry.menu_ids()` is now the single source
  of the id, and `find_menu()` resolves a launcher, an id or a name through it.
- **Renaming a menu says what it does to that menu's key.** A menu's hotkey id is
  built from its name and 3D-Coat keys its bindings by that id, so a rename leaves
  the old binding pointing at nothing. We never write 3D-Coat's hotkey file, so the
  editor names the key that will stop firing instead of losing it quietly.
- **The overlay uses the screen it opens on, not the primary one.** A cursor can sit
  where no screen is (the gap in an L-shaped desktop, a display that just went away)
  and the panel was placed at that raw anchor - off-screen, an invisible menu. It is
  now clamped onto the screen picked for the anchor, and the height cap follows that
  screen too: a second monitor is usually a different height, and a long list sized
  for the primary one hung off the bottom of the shorter one.
- **The editor sizes, centres and clamps itself on the screen the pointer is on** -
  the same primary-screen assumption, for the panel, its preview and the 1240px
  size fit.
- **`*` in the editor title means "differs from the file".** Undoing back to the
  loaded config kept the marker (and made the panel treat the config as edited), so
  the un-saved state now compares against the loaded baseline, which a save resets.
- **A submenu under a parent at the screen edge opened off the screen.** A child
  panel flips to the left of its parent when it does not fit on the right, and the
  flipped position was never clamped - a wide submenu under a parent at the left
  edge landed entirely outside the screen, where its rows cannot be reached. Both
  axes are clamped now.
- **Escape steps back out one level per press.** It closed the whole chain below
  the root at once, the opposite of what that method's own docstring promised.
- **Picking an entry inside a submenu closes the whole menu.** Running a nested
  entry dismissed only the panel the entry sat in, leaving the parent panels up with
  nothing left to pick. A mouse click did close everything; Enter and the number
  keys did not.
- **Installing again brings back the lists an uninstall saved.** An uninstall parks
  the user's `menus.json` next to the data folder ("your lists were backed up to
  ..."), but a later install ignored it and started over from the built-in set. It
  is restored when no config exists - never over one that does.

### Removed

- **Another extension's code is gone.** CoatMenu used to ship a 430-file,
  ~39k-line copy of the sculpt actions that came with an older radial-menu
  extension, under `ported/`, and that tree was most of the release archive. It is
  deleted outright: no `ported/`, no `ported.*` imports, no action scripts calling
  into it. An install cleans the old tree out of an existing copy, whole folder and
  all (pruning alone would have left its icons and `.env` stubs behind).
- The extension's tests, docs and comments no longer name that extension either.

### Changed

- **The shipped set is three lists, and they are the author's own working set**:
  `QuickTool`, `Add`, `Shade` (a pie). A first run is not a showcase of everything
  the extension can build - a fresh install used to arrive with seven menus.
  `Modeling`, `Tools`, `Common` and `Sculpt Ops` are still built on request
  (`+ New ▸ Built-in lists`), but nothing but those three is installed for you.
  `Sculpt` is gone as a name: it was the same rows as `QuickTool`, which is what it
  is called now.
- The `Shade` pie's three view rows are spelled the way 3D-Coat spells them
  (`$VIEW_GLOSS_ONLY`, `$VIEW_SPECULAR_COLOR_ONLY`, `$VIEW_WIREFRAME`); without the
  underscores they are not ids 3D-Coat defines at all, so those rows did nothing.
- **`Sculpt Ops` is ours now** and contains no script of anyone else's: 71 of
  **3D-Coat's own object commands** (the ones on the VoxTree right-click menu,
  where decimate / resample / the live booleans / merge / ghosting live) in seven
  groups. Every id is looked up in 3D-Coat's own menu definitions when the list is
  built, so a command this build does not define is left out instead of shipped as
  a row that does nothing - and the names on the rows are 3D-Coat's own. Nothing
  carried over from the old list that only a script could do (density matching,
  keeping parts through a remesh, ID colours, scale-and-restore export).
- `Add` (the renamed `Prims`) stays 3D-Coat's own command ids in the order 3D-Coat
  needs them, and now drops the two shapes **3D-Coat 2025 does not define**
  (`prm_TorusPrim`, `prm_ImagePrim`) instead of shipping them as rows that do
  nothing. The Mesh Prims group is gone with them: it pointed at
  `UserPrefs/Models/SculptModels/*.obj`, which no 3D-Coat install has - the five
  rows could never have worked. The idea of picking primitives from a radial menu
  came from the extensions that came before this one - the implementation is ours.
- **Every curated row is now checked against 3D-Coat's own id table**
  (`data/Languages/<lang>.xml`). A list still builds when the table cannot be read,
  but when it can, an id this build does not define never reaches the menu.

### Fixed

- **A path containing `&` no longer breaks the menu file.** `ExtraMenuItems/CoatMenu.xml`
  was written without XML escaping, so an account or folder named `Ben & Jerry` or
  `R&D` produced a file 3D-Coat refuses to parse - and the three `Scripts ▸ CoatMenu`
  entries simply never appeared. Ids and script paths are escaped now, and a
  regression test parses the file from a path with `&` in it.
- **Two menus whose names are not ASCII no longer collide.** `slugify()` dropped
  every non-ASCII character, so `雕刻` and `建模` both became `menu`: one launcher
  file, one hotkey id, one entry in `Scripts ▸ CoatMenu`, and the second menu
  overwrote the first. Names outside ASCII now get a short hash of the original
  name appended (`menu_<hash>`), which keeps them unique and stable; a plain ASCII
  name is untouched, so existing launchers, hotkey bindings and menu ids keep
  working.
- **The installer no longer depends on where Windows keeps `Documents`.**
  `install.cmd` looked for 3D-Coat's Python in three hard-coded spots and in a
  `python-<version>` folder whose name changes with every release; `install.py`
  assumed `Documents\3DCoat` and never asked. Both now ask the registry where
  `Documents` (and therefore 3D-Coat's data folder) is, accept any `python-*`
  folder, and take `--documents DIR` when all else fails. A shortcut to the
  Microsoft Store's stub `python.exe` can no longer be picked up by accident:
  every candidate has to run before it is used.
- The extension no longer assumes `Documents\3DCoat` exists: the data folder is
  `coat.io.dataPath()` when 3D-Coat can say, and is *checked* for a `UserPrefs`
  folder rather than assumed - a user who moved it (or runs a portable copy) gets
  a warning instead of a silent install into a folder 3D-Coat never reads.
- **A menu deleted in the editor is gone for good.** 3D-Coat writes its own
  `ExtraMenuItems/<id>.xml` for every entry it is asked to insert and never removes
  one, so the entry was read back at every start - the deleted menu stayed in the
  Scripts list for good, and the three fixed entries were listed **twice** (they are
  in `CoatMenu.xml` as well). An install and the extension's startup now delete the
  copies whose menu is gone, take those ids out of the *running* 3D-Coat (no restart
  needed), and the three fixed entries are no longer inserted at runtime at all. An
  uninstall removes its leftovers too. The doctor report lists what is left.
- **Deleting a built-in menu now sticks.** `install_presets` works by finding what
  is *missing*, so a shipped list deleted on purpose was added straight back by the
  next update - his deletion, undone by an install. The config remembers it (a
  `removed` list, keyed by preset family, or by name for a list that has no marker),
  and an install leaves those alone.
- **The editor can put a built-in list back.** `+ New` is one button with a menu:
  an empty menu, or any shipped list - built fresh against the 3D-Coat that is
  running, and no longer the only way to get back something Delete removed. A list
  already in the config is shown as such and cannot be added twice. The doctor
  report names the deleted built-ins.

## v0.6.1 — 2026-09-20

### Removed

- **Tool presets.** They could not be activated from a menu item on this build: the
  entry point `coat.pyi` documents (`coat.AppOptions.ActivateToolPreset`) does not
  exist in the live module, and a runtime scan of `coat` found nothing offering it.
  Rather than ship a source in the editor that produces rows which cannot work, it is
  gone: the `Presets` source, the generated `Presets` menu, and the reader behind
  them. A config written by an older build keeps working - preset rows are skipped
  on load instead of turning into commands that could never resolve.

## v0.6.0 — 2026-09-20

### Added

- **`Expand` column** — every group row can now say how it unfolds, instead of
  leaving it to the child count: **Auto** (the old behaviour: a pie shows up to
  three children in the slot, more opens a panel), **Inline** (always draw the
  children in the slot), **Panel** (always open a separate panel). Set per row in
  the editor; `auto` is not written to the config, so nothing changes for existing
  menus.
- **`Position` column** — pin a row to a compass point in a pie
  (`Top` / `Top right` / `Right` … `Top left`) so your hand can learn the layout.
  The column appears only for pie menus and hides itself for lists. `Auto` rows
  spread evenly, **first one straight up**.
- **`Sculpt Ops`, a bundled menu** — the sculpt actions that shipped with an older
  radial-menu extension, ported into CoatMenu so they keep working after that
  extension was removed. 93 entries in six groups (Object, Scene, Autopo, Brush,
  Export, Other), each a script with a readable name taken from its own docstring.
- Editor: hover a row to see its command id or script path; the menu dropdown now
  marks pie menus (`Wheel (4)  pie`) and follows programmatic selection.
- Installer: a backup is taken **only when a file actually changes**, and older
  backups are pruned to three. The old behaviour copied on every run and left 88
  `.bak-*` files behind after a day of reinstalling.

### Changed

- **A pie's slots now start straight up.** The old layout offset every slot by half
  a step, so four slots landed on the four *corners* — no slot was ever on a plain
  direction. Four slots are now up / right / down / left, eight are a clean compass.
- The editor's tree gained the two control columns above; the `Row` column stretches
  to fill the panel instead of leaving a band of dead space.

### Fixed

- **A row holding children is a group, whatever its original kind.** Dragging a
  command onto another one made it a submenu, but saving wrote it back as a plain
  command and silently dropped the children.
- The editor's `Menu` dropdown could disagree with the menu actually shown when the
  selection was made by name rather than by clicking the dropdown.

### Removed

- **Every dependency on other extensions.** The ported scripts used generic
  top-level names (`utils`, `ops`, `lks_utils`); inside `cExtensions` those collide
  with any other add-on, so the whole tree now lives under `ported.*`. The modules
  that existed only to drive the old extension (`import LKS`) are gone, and the one
  runtime hook they provided — development-time hot reload — is now optional.
- The old extension's own actions and radial-menu launchers, its menu source in the
  editor, and its remaining traces in our files.

## v0.5.5 — 2026-09-20

### Removed

- **The plugin has nothing to do with hotkeys any more.** The editor's `Key:`
  button, the row `Set key…` / `Clear key` items, the per-row shortcut launchers and
  the `coat.menu_hotkey` call are all gone. Measured on this build: a key only
  attaches to an entry added through `coat.menu_item` inside 3D-Coat's menu pass,
  and entries inserted at runtime never reach the hotkey system — so it could not
  work, and worse, 3D-Coat rewrote those entries with an empty `<Code>`, silently
  removing bindings set by hand.
- Binding is simply 3D-Coat's own: **hover the entry in `Scripts ▸ CoatMenu` and
  press `END`**, then the combination. CoatMenu reads `Options_Hotkeys.xml` only to
  know which key opened a menu, exactly as it always did.

### Fixed

- The installer removes the now-unused `actions/shortcuts/` folder.

## v0.5.4 — 2026-09-20

### Fixed

- **A key set in the editor can actually take effect now.** It never could before:
  3D-Coat only honours a key on an entry added through `coat.menu_item`, and ours
  were added with `coat.ui.insertInMenu`, which the hotkey system ignores (and then
  rewrites with an empty `<Code>`). `onExtendMenu` — which the log proves this build
  does call — now registers every entry through the API and attaches the key
  immediately after its own entry. `onStartup` still inserts them as well, so they
  stay visible in the Scripts menu.
- Switching source in the editor no longer costs 80 ms, and the editor opens centred.
- A key you set by hand in Preferences ▸ Hotkeys is still never proposed over.
- (`END` over a menu entry remains 3D-Coat's own way of binding, and the fastest.)

## v0.5.3 — 2026-09-20

### Changed

- **The `.3dcpack` route is gone.** It landed the files fine, but the extension then
  still had to be ticked in Windows ▸ Panels ▸ Extensions — more steps than the
  plain zip, not fewer. Releases ship the zip again.
- **Key binding is documented the way 3D-Coat does it**: hover the entry in
  `Scripts ▸ CoatMenu`, press `END`, then the combination. That is its own hint text
  (*"'END' - Define Hotkey"*), and it writes the binding itself. The editor's `Key:`
  button now says so instead of implying it can bind anything.

### Fixed

- **Nothing assumes where 3D-Coat lives any more.** The installer looks for the user
  data folder (Documents, OneDrive-redirected Documents, `USERPROFILE`) and checks
  each for a `3DCoat` folder rather than hard-coding `~/Documents`; it warns loudly
  instead of installing somewhere 3D-Coat never reads, and accepts `--documents DIR`
  / `COATMENU_DOCUMENTS`. `install.cmd` searches the same spots for 3D-Coat's own
  Python. At runtime nothing was ever path-dependent: the folders come from
  `coat.io.documents()` / `coat.io.installPath()`.

## v0.5.2 — 2026-09-20

### Fixed

- **`coat.menu_hotkey` is gone.** Measured on this build: for an entry added at
  runtime (``coat.ui.insertInMenu``) the call is ignored, and 3D-Coat then rewrites
  that entry with an empty ``<Code>`` — silently wiping two bindings that had been
  set by hand (`CoatMenu_Sculpt`, `CoatMenu_Shade`). A key is now a note in the
  editor plus the id to paste into Preferences ▸ Hotkeys; nothing is written from
  our side.

### Changed

- Both menu hooks log every time they run. ``onExtendMenu`` does fire on this build
  — the earlier conclusion that it does not was wrong, because the code that ran at
  the time was older than the hook.

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
