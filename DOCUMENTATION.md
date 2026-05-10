# Custom Families — Developer Documentation

This document lists the **public API** exposed by the two components that
make up the plugin and describes what each function does. It is meant for
developers who want to drive Custom Families programmatically (TD textport,
panel callbacks, external scripts) rather than through the UI.

The functions described here are the ones that follow TouchDesigner's
extension naming convention (capitalized name → callable from outside the
component). Internal helpers (leading underscore) are intentionally left out.

---

## 1. `Custom_families` — the container

The container is the COMP installed at `/ui/Plugins/Custom_families`. It
hosts the toolbar, the dialogs, the `Local`/`Server` shelves, and is the
host for any `Custom_fam` you create or import.

It has three extension classes, each attached to a different sub-COMP
(`Installer`, `Uninstaller`, `Updater`).

### 1.1 `Installer` extension — `Custom_families/Installer/Install.py`

| Function | What it does |
|---|---|
| **`Run()`** | Master install entry point. Runs in three phases: (A) realigns the `Install` DAT itself to the LOCALAPPDATA copy and re-enters; (B) realigns every other DAT listed in the `Scripts` table; (C) decides between full install, surgical reinstall of missing pieces, or "already installed" no-op. Drives the Install_window progress bar through all install steps (download, pane split, watcher, toolbar injects, menu_op patches, runtime/Local enable, final script realign). |
| **`RealignScripts(only=None, skip=None)`** | Walks the `Scripts` table inside the Installer COMP and repoints each row's `par.file` to its canonical on-disk script under `LOCALAPPDATA/Derivative/TouchDesigner099/Custom families/...` when the file actually exists there. Returns `True` if at least one `par.file` was changed. `only` restricts the pass to a single op path, `skip` excludes one. |

### 1.2 `Uninstaller` extension — `Custom_families/Uninstaller/Uninstall.py`

| Function | What it does |
|---|---|
| **`Run()`** | Master uninstall entry point. Drives a multi-step deferred sequence (visible in the Uninstall_window progress bar) that: restores panebar visibility, restores the original toolbar styling, restores the menu_op `familypanel`/`families` outputs to their TD defaults, destroys the `Local` and `Server` containers (giving each family watcher time to fire its own cleanup chain), removes the `Local_bar` / `Server_bar` / button / `Pages` / `Page_number` injects, closes the toolbar pane, then destroys the `Custom_families` COMP itself. |

### 1.3 `Updater` extension — `Custom_families/Updater/Update.py`

Currently a stub (default TD extension scaffolding). Reserved for future
update flows; no production functions are exposed yet.

---

## 2. `Custom_fam` — the single family

A `Custom_fam` is one entry inside the container's `Local` (or `Server`)
shelf. It carries its own custom operators, its own toolbar button, its
own menu_op insert, and its own watcher.

It exposes four extension classes, each with a focused responsibility.

### 2.1 `ComponentEXT` — lifecycle and shared state

`Custom_fam/ComponentEXT.py` — the family's "façade" extension. Most
functions delegate to the more specialized installer/uninstaller/rename
bridges; this is where you call from when scripting against a family.

#### Install / uninstall

| Function | What it does |
|---|---|
| **`Install()`** | Installs the family. Resolves the installer bridge, refreshes the global shortcut, sets `par.Install = 1`, then delegates to `InstallerEXT.Install()`. |
| **`Uninstall()`** | Uninstalls the family by delegating to the uninstaller bridge (`RemoveFamily`). |
| **`HandleInstallValue(raw_value, source_label='external')`** | Coerces a value (`'1'`/`'true'`/`'on'`/`'yes'` or `'0'`/`'false'`/`'off'`/`'no'`) and routes it to `Install()` or to the uninstaller's `RemoveFamily()`. Used by callbacks that observe `par.Install`. |
| **`DeleteCleanup()`** | Performs the same teardown as `Uninstall()`. Called on COMP destruction. |

#### Identity / naming

| Function | What it does |
|---|---|
| **`GetFamilyName()`** | Returns the family's canonical name (the sanitized global shortcut). |
| **`GetGlobalShortcut()`** | Returns the sanitized OP shortcut for the family, refreshing it on demand. |
| **`UpdateGlobalShortcut()`** | Reads the current `opshortcut` parameter, sanitizes it, and stores the result in the dependable `Global_op_shortcut` property. Notifies the installer if the name changed. |
| **`SanitizePluginName(name)`** | Strips spaces, removes any character outside `[A-Za-z0-9_]`, prefixes a leading digit with `_`. The single source of truth for what a family name is allowed to look like. |
| **`PromptRenameFamily()`** | Opens the `PopDialog` rename prompt (defaults to current name). On confirm, delegates to `RenameEXT.RenameFamily`. |

#### Family menu / actions

| Function | What it does |
|---|---|
| **`OpenFamilyContextMenu(buttonComp=None)`** | Opens the family's `PopMenu` aligned to the given button, with the items: *Rename*, *Edit custom operators*, *Export family*, *Delete*. Each item is wired to the respective method. |
| **`EditCustomOperators()`** | Opens the family's custom-operators root COMP in the current network pane (or in its viewer). |
| **`ExportFamily()`** | Prompts the user with a file picker and saves the family COMP as a `.tox` at the chosen path. |
| **`DeleteFamily()`** | Removes the family by delegating to the uninstaller's `RemoveFamily`. |

#### Update / placement

| Function | What it does |
|---|---|
| **`UpdateAll(showMessage=False)`** | Full sweep: rebuilds the family's toolbar bookmark / button, color, About-page mirroring on installed clones, custom-operator wiring, and any state derived from the COMP. The heavy refresh step. |
| **`ScheduleUpdateAll(showMessage=False)`** | Defers `UpdateAll` by one frame, coalescing repeated requests so multiple triggers in the same tick run the refresh only once. Returns `False` if a refresh is already queued. |
| **`DeferredUpdateAll(showMessage=False)`** | Internal target of the `ScheduleUpdateAll` deferred call. Re-queues itself if a rename or reinstall is in progress so the refresh happens only when the COMP state has settled. |
| **`PlaceNamedCustomOperator(display_name)`** | Drops the named custom operator into the current network pane at the cursor, as if the user had picked it from the OP Create dialog. |
| **`PlaceOp(panelValue, display_name)`** | Lower-level placement entry used by the OP Create panel callback; respects panel value state to avoid double-drops. |
| **`CancelPendingPlacement(clear_pane=False)`** | Cancels any drop-in-flight (e.g. user pressed Esc). If `clear_pane=True` also clears the destination pane preview state. |

#### Color sync

| Function | What it does |
|---|---|
| **`GetColorFromOwner()`** | Reads the family's color from its dedicated parameter on the owner COMP. |
| **`GetColorTargetsOfOwner(maxDepth=...)`** | Returns the list of operators inside the family that should pick up the family color (buttons, bookmark tag, etc.). |
| **`UpdateChildrenColor(maxDepth=...)`** | Pushes the current owner color to every targetable child. |
| **`SyncInstalledColor(maxDepth=...)`** | Same propagation but applied to the *installed clones* of the family living outside the source COMP (toolbar button, menu_op insert, etc.). |

#### About-page mirroring

The About page is the parameter page that custom operators expose with
their family/version info. The following helpers keep it in sync between
the source family and its clones:

| Function | What it does |
|---|---|
| **`FindCustomPage(o, page_name)`** | Returns the named custom page on `o` if it exists, else `None`. |
| **`GetAboutTargetCompsOfOwner(maxDepth=...)`** | Lists every COMP inside the family that should carry the About page. |
| **`GetExternalAboutTargetComps()`** | Same, but for installed clones outside the source. |
| **`ExtractReferenceAboutDefinition(page_name=ABOUT_PAGE_NAME, excluded_par_names=None)`** | Snapshots the canonical About-page parameter definitions from the source COMP. |
| **`CreateCustomPage(target_op, page_name=ABOUT_PAGE_NAME)`** | Creates a new About page on the given operator. |
| **`GetOrCreateCustomPage(target_op, page_name=ABOUT_PAGE_NAME)`** | Returns the About page on `target_op`, creating it if missing. |
| **`ParameterExists(target_op, par_name)`** | Helper: does `target_op` have a parameter named `par_name`. |
| **`AppendParameterFromDefinition(target_page, par_def)`** | Adds a parameter to a custom page from a snapshot definition. |
| **`EnsureParameterExists(target_op, target_page, par_def)`** | Idempotent version: appends only if missing. |
| **`ApplyExtraDefinition(target_op, par_def)`** | Applies extras (range, default, menu items, …) on top of an already-created parameter. |
| **`IsStringLikeStyle(style_name)`** | Returns True for parameter styles that store a string. |
| **`SetTupletValues(target_op, par_def)`** | Writes a tuplet's values onto a target parameter. |
| **`UpdateAboutSpecialValues(target_op)`** | Refreshes the special About-page values (family name, version, …). |
| **`SyncAboutOnComp(target_op, about_defs, page_name=ABOUT_PAGE_NAME)`** | Syncs the About page on a single target COMP against the snapshot. |
| **`RebuildAboutOnAllComps(page_name=ABOUT_PAGE_NAME, maxDepth=...)`** | Sweeps every target COMP and rebuilds its About page from scratch. |

#### Maintenance

| Function | What it does |
|---|---|
| **`RepairManagedScriptSyncs()`** | Walks the family's managed scripts and repoints each one's `par.file` to the canonical on-disk path (relative to the family's root folder). Returns the number of scripts repointed. The family-side counterpart of the container's `RealignScripts`. |
| **`ScheduleInstallStateWatch()`** | Schedules a one-frame deferred poll of `par.Install` so external value changes get observed and routed through `HandleInstallValue`. |

---

### 2.2 `InstallerEXT` — install pipeline

`Custom_fam/InstallerEXT.py` (class `GenericInstallerEXT`, aliased as
`InstallerEXT`).

| Function | What it does |
|---|---|
| **`Install(family_name=None, color=None, compatible_types=None, show_message=False, is_update=None, reset_trace=True)`** | Main install routine. Sanitizes the family name, makes sure the family COMP is hosted inside `Custom_families/Local` (queues a relocation if not), replaces any existing family with the same name, runs the full install pipeline: retag children, delete-execute watcher, install toggle, install watcher, install menu_op insert (`familypanel`), update colors / compatible-types / eval tables, install panel-execute hooks, patch `create_node` and `search_exec`. Records the installed family for later cleanup. |
| **`Uninstall(family_name=None, reset_trace=True)`** | Master uninstall counterpart. Tears down all the inserts/patches that `Install` produced (toggle, watcher, menu_op insert, panel-execute, create_node and search_exec patches, color/compat/eval table entries, recorded-installed-family marker). |
| **`SchedulePostInitSetup()`** | Schedules the deferred post-`__init__` setup: bridges to the host (`Custom_families`), wires runtime hooks, refreshes the install state. Used so the extension can finish loading before touching the wider TD UI. |
| **`SuppressContextMenuToggle(frame_window=3)`** | Suppresses the family's right-click toggle for a small frame window so a cascade of UI events doesn't reopen the menu while a user action is being processed. |
| **`ScheduleInstallStateWatch()`** | Same intent as the ComponentEXT method but on the installer side: defers the install-state poll one frame. |
| **`NormalizeCustomOperatorRuntimeExecutes()`** | Normalizes the per-operator runtime execute DATs across the family so each custom operator has the same name/role for its runtime hook. |
| **`PrepareCustomOperatorRuntimeLink(operator_comp)`** | Wires a single custom-operator COMP to the family's runtime hook so it picks up family-level events (color sync, About sync, placement). |
| **`RefreshCustomOperatorTemplate(operator_comp)`** | Re-applies the family's template to a custom-operator COMP — refreshes its tags, About page, color, and runtime hook in one pass. |
| **`RebuildInstalledClones(previous_family=None, new_family=None)`** | Rebuilds every installed clone of the family (toolbar button, menu_op insert, custom-operator copies). When the family is being renamed, `previous_family`/`new_family` let the rebuild rename the clones in place. |
| **`DeleteCleanup(family_name=None, reset_trace=True)`** | Compatibility entry that maps to the uninstall path; called on COMP destruction. |
| **`HandleInstallValue(raw_value, source_label='external')`** | Installer-side mirror of the ComponentEXT method (same coercion rules), so the toggle change can be routed even when only the installer extension is reachable. |
| **`HandleInstallFromOwnerState(source_label='external')`** | Reads the current value of `par.Install` on the owner and routes it through `HandleInstallValue`. Used as a one-shot reconciler. |

---

### 2.3 `UninstallerEXT` — uninstall pipeline

`Custom_fam/UninstallerEXT.py` (class `GenericUninstallerEXT`, aliased as
`UninstallerEXT`).

| Function | What it does |
|---|---|
| **`RemoveFamily(family_name=None)`** | Full uninstall. Destroys the toolbar button first (so a stale button can never survive a deeper failure), then delegates to the installer's destroy chain (UI clones, menu_op, external delete helpers), clears the recorded-installed-family marker, sets `par.Install = 0`. Falls back to a self-contained cleanup path if the installer bridge isn't reachable. |
| **`RemoveInstalledUi(family_name=None)`** | Like `RemoveFamily` but keeps the install toggle alive — used when you want to refresh the family's installed UI without flipping the install state (e.g. during a rename). |
| **`Uninstall(family_name=None)`** | Alias for `RemoveFamily` for symmetry with `InstallerEXT.Install`. |
| **`DeleteCleanup(family_name=None)`** | Alias for `RemoveFamily`, called on COMP destruction. |

---

### 2.4 `RenameEXT` — rename pipeline

`Custom_fam/RenameEXT.py` (class `GenericRenameEXT`, aliased as `RenameEXT`).

| Function | What it does |
|---|---|
| **`RenameFamily(new_name, show_message=False, previous_name=None)`** | Atomic rename. Sanitizes the new name, captures the install state, destroys the old button, runs `RemoveFamily(old_name)` if the family was installed, renames the owner COMP, updates `opshortcut` and `Global_op_shortcut`, then reinstalls under the new name. Stores a `cf_reinstall_in_progress` flag and a `_renameInProgress` guard so the deferred `UpdateAll` does not rebuild the new UI before the old one has been removed. Skips the destructive cleanup if a sibling COMP still owns `old_name` (typical when a copy-paste triggers an automatic rename on the duplicate). |
| **`HandleObservedNameChange(previous_name, new_name, show_message=False)`** | Wrapper called by the watcher that observes COMP renames. Sanitizes both names and forwards to `RenameFamily`. |
| **`PromptRenameFamily()`** | Opens the rename `PopDialog`. Mirrors `ComponentEXT.PromptRenameFamily` but lives on the rename extension itself; used as a fallback when called from contexts where `ComponentEXT` is not reachable. |

---

## License

[MIT](LICENSE) © 2026 Gianluca Colia
