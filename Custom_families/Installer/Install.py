import os
import ssl
import urllib.request
import zipfile
import shutil

UI_ROOT_PATH = '/ui'

REPO_ZIP_URL = 'https://github.com/Gianluca-Colia/CustomFamilies/archive/refs/heads/main.zip'
EXTRACTED_FOLDER_NAME = 'CustomFamilies-main'   # GitHub default name when extracting a branch zip
DOWNLOAD_DEST_FOLDER_NAME = 'Custom families'    # final folder name (with space) under TD AppData
PLUGINS_ROOT_NAME = 'Plugins'
PLUGINS_ROOT_PATH = '/ui/Plugins'
CUSTOM_FAMILIES_NAME = 'Custom_families'
CUSTOM_FAMILIES_PATH = '/ui/Plugins/Custom_families'
LOADBAR_PATH = '/ui/Plugins/Custom_families/Dialogs/Install_window/Loadbar'
INSTALL_WINDOW_PATH = '/ui/Plugins/Custom_families/Dialogs/Install_window'
# app.preferencesFolder resolves to the TD prefs folder cross-platform:
#   Windows: %LOCALAPPDATA%/Derivative/TouchDesigner099
#   macOS:   ~/Library/Application Support/Derivative/TouchDesigner099
TOUCHDESIGNER_LOCAL_PATH = app.preferencesFolder
SCRIPTS_DISK_ROOT = os.path.join(TOUCHDESIGNER_LOCAL_PATH, 'Custom families')
UI_BACKUP_FOLDER_PATH = os.path.join(SCRIPTS_DISK_ROOT, 'ui backup')
UI_BACKUP_FILE_PATH = os.path.join(UI_BACKUP_FOLDER_PATH, 'ui.tox')
SCRIPTS_TABLE_NAME = 'Scripts'
PLUGINS_PREFIX = '/ui/Plugins/'
INSTALL_DAT_NAME = 'Install'
RUNTIME_NAME = 'Runtime'
LOCAL_NAME = 'Local'
# Important: in this layout the visible toolbar is produced by shrinking the
# top pane by writing the split ratio on the bottom pane. This looks inverted,
# but it is the stable behavior we observed in TD for this top/bottom split.
BOTTOM_PANE_LOCK_RATIO = 0.0001
BOTTOM_NETWORK_OWNER_PATH = '/project1'
WATCHER_NAME = 'Watcher_Custom_families'
WATCHER_SOURCE_PATH = 'Ui_inject/Watcher_Custom_families'
# pane1 is the logical toolbar anchor, but we do NOT assign it as the panel
# owner of the top pane anymore. Doing so makes TD render unwanted built-in UI
# such as the timeline inside the toolbar area.
TOP_PANEBAR_PATH = '/ui/panes/panebar/pane1'
TOP_PANEBAR_KEEP_NAMES = ('local', 'emptypanel')
CUSTOM_FAMILIES_BUTTON_NAME = 'Custom_families_button'
CUSTOM_FAMILIES_BUTTON_SOURCE_PATH = 'Ui_inject/Custom_families_button'
LOCAL_BAR_NAME = 'Local_bar'
LOCAL_BAR_SOURCE_PATH = 'Ui_inject/Local_bar'
SERVER_BAR_NAME = 'Server_bar'
SERVER_BAR_SOURCE_PATH = 'Ui_inject/Server_bar'
MENU_OP_PATH = '/ui/dialogs/menu_op'
PAGES_NAME = 'Pages'
PAGE_NUMBER_NAME = 'Page_number'
PAGES_SOURCE_PATH = 'Ui_inject/Pages'
PAGE_NUMBER_SOURCE_PATH = 'Ui_inject/Page_number'
SEARCHPANEL_NAME = 'searchpanel'
LABEL_PATH = '/ui/dialogs/menu_op/label'
EMPTYPANEL_NAME = 'emptypanel'
FAMILYPANEL_NAME = 'familypanel'
SELECT_AVAILABLE_NAME = 'select_available'
NULL3_NAME = 'null3'
NULL4_NAME = 'null4'
PAGES_OUT1_PATH = 'out1'
PAGES_OUT2_PATH = 'out2'
TOP_PANE_STORE_KEY = 'cf_top_pane_id'
BOTTOM_PANE_STORE_KEY = 'cf_bottom_pane_id'
INSTALL_COMPLETE_KEY = 'cf_install_complete'


class Install:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.ui_root = op(UI_ROOT_PATH)
		self.plugins_root = op(PLUGINS_ROOT_PATH)
		self.menu_op = op(MENU_OP_PATH)
		self.top_panebar = op(TOP_PANEBAR_PATH)

	# ------------------------------------------------------------------
	# Inject inventory — used by Run() to decide between full install,
	# surgical reinstall of missing pieces, and "already installed" no-op.
	# Each entry: (label, canonical path of the injected op).
	# ------------------------------------------------------------------
	def _inject_targets(self):
		return [
			('Watcher',                '/ui/Plugins/' + WATCHER_NAME),
			('Local_bar',              TOP_PANEBAR_PATH + '/' + LOCAL_BAR_NAME),
			('Server_bar',             TOP_PANEBAR_PATH + '/' + SERVER_BAR_NAME),
			('Custom_families_button', TOP_PANEBAR_PATH + '/' + CUSTOM_FAMILIES_BUTTON_NAME),
			('Pages',                  MENU_OP_PATH + '/' + PAGES_NAME),
			('Page_number',            MENU_OP_PATH + '/' + PAGE_NUMBER_NAME),
		]

	def _check_install_status(self):
		"""Walk the inject inventory and split into (present, missing) labels."""
		present, missing = [], []
		for label, path in self._inject_targets():
			if op(path) is not None:
				present.append(label)
			else:
				missing.append(label)
		return present, missing

	def _run_partial_install(self, comp, missing_labels):
		"""Re-run only the install steps for the given missing inject labels.

		Skips structural setup (pane split, runtime cook, etc.) on purpose:
		those have already been performed and redoing them on a working
		install would tear down state. We only redo the missing injects and
		their wiring.
		"""
		for label in missing_labels:
			try:
				if label == 'Watcher':
					self._install_watcher(comp)
				elif label == 'Local_bar':
					self._install_toolbar_inject(comp, LOCAL_BAR_SOURCE_PATH, LOCAL_BAR_NAME)
					self._wire_toolbar_inject(LOCAL_BAR_NAME)
				elif label == 'Server_bar':
					self._install_toolbar_inject(comp, SERVER_BAR_SOURCE_PATH, SERVER_BAR_NAME)
					self._wire_toolbar_inject(SERVER_BAR_NAME)
				elif label == 'Custom_families_button':
					self._install_toolbar_button(comp)
					self._wire_toolbar_button()
				elif label == 'Pages':
					self._install_dialog_inject(comp, PAGES_SOURCE_PATH, PAGES_NAME)
					self._wire_pages()
				elif label == 'Page_number':
					self._install_dialog_inject(comp, PAGE_NUMBER_SOURCE_PATH, PAGE_NUMBER_NAME)
					self._set_menu_label_width()
					self._wire_page_number()
			except Exception as exc:
				debug('[Custom_families partial install] {} failed: {}'.format(label, exc))
		self.RealignScripts()

	def Run(self):
		# Phase A: align the Install DAT itself to its canonical on-disk
		# copy first. If repointed, defer 2 frames so Sync to File can swap
		# the extension to fresh code, then re-enter Run.
		install_dat = self.ownerComp.op(INSTALL_DAT_NAME)
		install_path = install_dat.path if install_dat is not None else None
		if install_path and self.RealignScripts(only=install_path):
			self._defer_rerun(delay_frames=2)
			return

		# Phase B: align every other DAT listed in the Scripts table. If
		# any par.file changed, defer 1 frame so the new file content has
		# settled before the rest of the install starts touching ops.
		# Missing on-disk targets are silently skipped (expected on the very
		# first install, before the zip has been downloaded/unpacked).
		if self.RealignScripts(skip=install_path):
			self._defer_rerun(delay_frames=1)
			return

		parent_comp = self.ownerComp.parent()
		if parent_comp is None:
			return

		is_inside_plugins_container = self._is_inside_plugins_container(parent_comp)

		if is_inside_plugins_container:
			# Duplicate at canonical path → destroy this stray copy and bail.
			if parent_comp.path != CUSTOM_FAMILIES_PATH and op(CUSTOM_FAMILIES_PATH) is not None:
				parent_comp.destroy()
				self._show_message('Custom families plugin Already exist')
				return

			# Inject-based install state. We trust the actual UI tree, not the
			# cf_install_complete flag — the flag can lie if injects were
			# manually removed or a previous install failed mid-way.
			present, missing = self._check_install_status()

			if not missing:
				# Fully installed.
				self._show_message('Custom families plugin already installed')
				return

			if present:
				# Partial install: tell the user what's coming back and patch.
				labels = ', '.join(missing)
				self._show_message('Missing components reinstalled: {}'.format(labels))
				self._run_partial_install(parent_comp, missing)
				parent_comp.store(INSTALL_COMPLETE_KEY, True)
				return

			# No injects at all → fresh install, silent (no messagebox).
			self._run_ui_install(parent_comp)
			return

		self._move_or_remove(parent_comp)

	# ------------------------------------------------------------------
	# Script realignment — read the `Scripts` table inside this Installer
	# COMP (3 columns, no header: name | file_path | dat_path) and for
	# every listed DAT repoint par.file at the canonical on-disk copy
	# under LOCALAPPDATA/Derivative/TouchDesigner099/Custom families/...
	# when the file actually exists there. Missing files → silent skip
	# (expected on the very first install, before the zip is downloaded).
	# Run() drives this in two phases (self first, then the rest) so the
	# freshly synced extension code is the one running the install logic.
	# ------------------------------------------------------------------
	def RealignScripts(self, only=None, skip=None):
		"""Walk the Scripts table and align each row's par.file to its
		canonical disk path. Returns True if at least one par.file was
		changed (caller should defer one or more frames before continuing).

		`only`: TD op path. When set, align only that operator. Used by
		    Run() to update the Install DAT itself first.
		`skip`: TD op path to leave untouched in this pass. Used to avoid
		    realigning the Install DAT after Phase A has already done so.
		"""
		table = self.ownerComp.op(SCRIPTS_TABLE_NAME)
		if table is None or table.numRows == 0:
			return False

		changed = False
		for row in range(table.numRows):
			try:
				dat_path = table[row, 2].val.strip()
			except Exception:
				continue
			if not dat_path:
				continue
			if only is not None and dat_path != only:
				continue
			if skip is not None and dat_path == skip:
				continue
			if self._realign_one(dat_path):
				changed = True
		return changed

	def _realign_one(self, dat_path):
		"""Install a self-healing expression on the DAT's par.file.

		Pattern:
		    app.preferencesFolder + '/Custom families/<rel>.py'
		    if __import__('os').path.isfile(<same path>) else ''

		The expression resolves to the canonical on-disk path when the file
		exists at LOCALAPPDATA, otherwise to an empty string — so par.file is
		never left pointing at a stale absolute path that no longer exists.
		"""
		target = op(dat_path)
		if target is None or not target.pars('file'):
			return False
		if not dat_path.startswith(PLUGINS_PREFIX):
			return False
		rel = dat_path[len(PLUGINS_PREFIX):]
		if not rel:
			return False

		rel_disk = '/Custom families/' + rel + '.py'
		path_expr = 'app.preferencesFolder + ' + repr(rel_disk)
		new_expr = (
			path_expr + " if __import__('os').path.isfile(" + path_expr + ") else ''"
		)

		par = target.par.file
		try:
			current_expr = par.expr or ''
		except Exception:
			current_expr = ''
		try:
			current_mode = par.mode
		except Exception:
			current_mode = None

		if current_expr == new_expr and current_mode == ParMode.EXPRESSION:
			return False

		try:
			par.expr = new_expr
			par.mode = ParMode.EXPRESSION
		except Exception:
			return False
		return True

	def _canonical_disk_path(self, dat_path):
		"""Map a TD op path to its on-disk script under LOCALAPPDATA.

		`/ui/Plugins/Custom_families/Installer/chopexec1`
		    → `<SCRIPTS_DISK_ROOT>/Custom_families/Installer/chopexec1.py`

		Returns None for paths outside the /ui/Plugins/ branch — those rows
		are external to our managed layout and we leave them alone.
		"""
		if not dat_path.startswith(PLUGINS_PREFIX):
			return None
		rel = dat_path[len(PLUGINS_PREFIX):]
		if not rel:
			return None
		return os.path.join(SCRIPTS_DISK_ROOT, rel + '.py').replace('\\', '/')

	def _defer_rerun(self, delay_frames=1):
		run(
			"target = op(args[0]); "
			"target.ext.Install.Run() if target is not None else None",
			self.ownerComp.path,
			delayFrames=delay_frames
		)

	def _is_inside_plugins_container(self, comp):
		parent_comp = comp.parent()
		if parent_comp is None:
			return False

		return parent_comp.path == PLUGINS_ROOT_PATH

	def _move_or_remove(self, parent_comp):
		existing = op(CUSTOM_FAMILIES_PATH)
		if existing is not None:
			parent_comp.destroy()
			self._show_message('Custom families plugin Already exist')
			return

		self._backup_ui_to_disk()
		plugins_root = self._get_or_create_plugins_root()
		if plugins_root is None:
			return

		parent_comp.store(INSTALL_COMPLETE_KEY, False)
		copied_comp = plugins_root.copy(parent_comp)
		copied_comp.name = CUSTOM_FAMILIES_NAME
		copied_comp.nodeX = parent_comp.nodeX
		copied_comp.nodeY = parent_comp.nodeY
		parent_comp.destroy()

	def _backup_ui_to_disk(self):
		if self.ui_root is None:
			return

		os.makedirs(UI_BACKUP_FOLDER_PATH, exist_ok=True)
		self.ui_root.save(UI_BACKUP_FILE_PATH)

	def _progress(self, step, label):
		"""Update the Install_window Loadbar (Actualstep + Operation).

		Silent no-op if the Loadbar isn't reachable (e.g., dialog closed early
		or running an install path that doesn't expose the dialog).
		"""
		bar = op(LOADBAR_PATH)
		if bar is None:
			return
		try:
			bar.par.Actualstep = step
		except Exception:
			pass
		try:
			bar.par.Operation = label
		except Exception:
			pass

	def _set_install_window_state(self, value):
		"""Switch the Install_window's State parameter (e.g. State=2 = installed)."""
		window = op(INSTALL_WINDOW_PATH)
		if window is None:
			return
		try:
			window.par.State = value
		except Exception:
			pass

	def _install_steps(self):
		"""Ordered (label, callable) tuples for the 20 install checkpoints.

		Each callable takes the Custom_families root COMP. We rebuild this list
		fresh on every deferred dispatch so it survives extension-instance
		regeneration between frames.
		"""
		return [
			('Downloading from GitHub',    lambda c: self._download_repo_to_appdata()),
			('Disable runtime',            lambda c: self._disable_runtime_cook(c)),
			('Normalize panes',            lambda c: self._normalize_to_pane1()),
			('Initialize toolbar',         lambda c: self._initialize_toolbar()),
			('Style toolbar',              lambda c: self._set_toolbar_styling(True, outline=False)),
			('Install watcher',            lambda c: self._install_watcher(c)),
			('Hide panebar children',      lambda c: self._hide_top_panebar_children()),
			('Install Local bar',          lambda c: self._install_toolbar_inject(c, LOCAL_BAR_SOURCE_PATH, LOCAL_BAR_NAME)),
			('Wire Local bar',             lambda c: self._wire_toolbar_inject(LOCAL_BAR_NAME)),
			('Install Server bar',         lambda c: self._install_toolbar_inject(c, SERVER_BAR_SOURCE_PATH, SERVER_BAR_NAME)),
			('Wire Server bar',            lambda c: self._wire_toolbar_inject(SERVER_BAR_NAME)),
			('Install toolbar button',     lambda c: self._install_toolbar_button(c)),
			('Wire toolbar button',        lambda c: self._wire_toolbar_button()),
			('Install Pages',              lambda c: self._install_dialog_inject(c, PAGES_SOURCE_PATH, PAGES_NAME)),
			('Wire Pages',                 lambda c: self._wire_pages()),
			('Install Page_number',        lambda c: self._install_dialog_inject(c, PAGE_NUMBER_SOURCE_PATH, PAGE_NUMBER_NAME)),
			('Set menu label width',       lambda c: self._set_menu_label_width()),
			('Wire Page_number',           lambda c: self._wire_page_number()),
			('Enable runtime',             lambda c: self._enable_runtime_cook(c)),
			('Enable Local',               lambda c: self._enable_local_cook(c)),
			('Realign scripts',            lambda c: self.RealignScripts()),
		]

	def _run_ui_install(self, custom_families_comp):
		# Drive the install as a deferred chain (one step per frame). This makes
		# the Loadbar visibly advance one tick at a time instead of jumping from
		# 0 to 100% in a single frame.
		# INSTALL_COMPLETE_KEY is set only at the very end. If a step raises,
		# the flag stays False so the next Run() can retry the install instead
		# of being blocked by the guard in Run().
		self._run_install_step(0, custom_families_comp.path)

	def _run_install_step(self, index, target_path):
		target = op(target_path)
		if target is None:
			return

		steps = self._install_steps()
		if index >= len(steps):
			# All steps complete.
			try:
				target.store(INSTALL_COMPLETE_KEY, True)
			except Exception:
				pass
			self._set_install_window_state(2)
			return

		label, fn = steps[index]
		self._progress(index + 1, label)
		try:
			fn(target)
		except Exception as exc:
			try:
				target.store(INSTALL_COMPLETE_KEY, False)
			except Exception:
				pass
			debug('[Custom_families install] step {} ({}) failed: {}'.format(
				index + 1, label, exc))
			return

		self._schedule_install_step(index + 1, target_path)

	def _schedule_install_step(self, index, target_path):
		run(
			"owner = op(args[0]); "
			"owner.ext.Install._run_install_step(args[1], args[2]) if owner is not None else None",
			self.ownerComp.path,
			index,
			target_path,
			delayFrames=1
		)

	def _download_repo_to_appdata(self):
		"""Fetch the GitHub repo zip, extract into the TD AppData folder,
		rename the extracted folder to 'Custom families', remove the zip.

		Final layout:
		    {LOCALAPPDATA}/Derivative/TouchDesigner099/Custom families/
		        ├── Custom_families/
		        │   └── Local/Custom_fam/   (default family template)
		        ├── Font/  Images/  ui backup/
		        ├── .tox/  docs/  README.md  LICENSE  .gitignore

		Skip behavior — when the destination folder already exists AND the
		Custom_families root's `Force Download` parameter is off, we don't
		re-download. This protects local edits during development; users
		who want to refresh either flip Force Download on or remove the
		folder manually.

		On failure (typically: user offline, DNS issue, GitHub unreachable)
		shows a messagebox and destroys the in-memory Custom_families COMP
		so the partial install state is cleared.
		"""
		td_root = TOUCHDESIGNER_LOCAL_PATH
		final_path = os.path.join(td_root, DOWNLOAD_DEST_FOLDER_NAME)

		# Skip only when the install actually exists. The prefetch step in
		# Install_window/execute1.py creates `Custom families/` with just
		# Font/ and Images/ inside — checking only `isdir(final_path)` made
		# us skip the full download in that case, leaving the plugin code
		# unextracted. We probe a canonical install file instead.
		install_marker = os.path.join(
			final_path, 'Custom_families', 'Installer', 'Install.py'
		)
		if os.path.isfile(install_marker) and not self._force_download_enabled():
			return

		try:
			if not os.path.isdir(td_root):
				os.makedirs(td_root, exist_ok=True)
		except Exception:
			self._handle_offline_failure()
			raise

		zip_path = os.path.join(td_root, 'CustomFamilies-main.zip')

		# Download — urlretrieve is brittle on TD's embedded Python (no CA
		# bundle configured by default → SSL verify fails on github.com,
		# missing User-Agent → some redirects 403). Use urlopen with an
		# explicit Request, write in chunks, and fall back to an unverified
		# SSL context if the verified one fails. Surface the real exception
		# via debug() so we don't mask the root cause behind a generic
		# "offline" messagebox.
		try:
			self._download_zip(REPO_ZIP_URL, zip_path)
		except Exception as exc:
			debug('[Custom_families download] failed: {}: {}'.format(
				type(exc).__name__, exc))
			self._handle_offline_failure()
			raise

		# Extract
		try:
			with zipfile.ZipFile(zip_path, 'r') as archive:
				archive.extractall(td_root)
		except Exception:
			try:
				os.remove(zip_path)
			except Exception:
				pass
			self._handle_offline_failure()
			raise

		# Rename CustomFamilies-main → Custom families. If the destination
		# already exists, drop it first (the just-downloaded copy is the
		# authoritative one).
		extracted_path = os.path.join(td_root, EXTRACTED_FOLDER_NAME)
		final_path = os.path.join(td_root, DOWNLOAD_DEST_FOLDER_NAME)
		try:
			if os.path.isdir(final_path):
				shutil.rmtree(final_path)
			os.rename(extracted_path, final_path)
		except Exception:
			self._handle_offline_failure()
			raise

		# Rename the default family folder Custom_fam -> Custom so that the
		# on-disk layout matches the in-TD path /ui/Plugins/Custom_families/
		# Local/Custom and par.file expressions resolve cleanly.
		try:
			fam_src = os.path.join(final_path, 'Custom_families', 'Local', 'Custom_fam')
			fam_dst = os.path.join(final_path, 'Custom_families', 'Local', 'Custom')
			if os.path.isdir(fam_src) and not os.path.isdir(fam_dst):
				os.rename(fam_src, fam_dst)
		except Exception as exc:
			debug('[Custom_families download] Custom_fam rename skipped: {}'.format(exc))

		# Cleanup zip
		try:
			os.remove(zip_path)
		except Exception:
			pass

	def _download_zip(self, url, dest_path):
		"""Stream a URL to disk via urlopen + chunked write.

		Tries the default (verified) SSL context first. On any SSL error
		(typical on TD's embedded Python with no CA bundle) retries with
		an unverified context. Sends a User-Agent so GitHub doesn't 403
		the request as "unknown client".
		"""
		req = urllib.request.Request(
			url,
			headers={'User-Agent': 'Custom_families-installer'}
		)
		try:
			response = urllib.request.urlopen(req, timeout=30)
		except (ssl.SSLError, urllib.error.URLError) as ssl_exc:
			# Retry with unverified SSL only if the failure is SSL-related.
			if not isinstance(ssl_exc, ssl.SSLError) and not (
				isinstance(ssl_exc, urllib.error.URLError)
				and isinstance(ssl_exc.reason, ssl.SSLError)
			):
				raise
			debug('[Custom_families download] SSL verification failed, '
			      'retrying with unverified context: {}'.format(ssl_exc))
			ctx = ssl._create_unverified_context()
			response = urllib.request.urlopen(req, timeout=30, context=ctx)

		with response, open(dest_path, 'wb') as out:
			while True:
				chunk = response.read(64 * 1024)
				if not chunk:
					break
				out.write(chunk)

	def _force_download_enabled(self):
		"""Read the `Force Download` toggle on the Custom_families root.

		Lives one level above the Installer COMP. Returns False when the
		parent or parameter is unreachable so dev safety (skip download
		if folder exists) is the default in any error case.
		"""
		try:
			root = self.ownerComp.parent()
			if root is None:
				return False
			par = getattr(root.par, 'Forcedownload', None)
			if par is None:
				return False
			return bool(par.eval())
		except Exception:
			return False

	def _handle_offline_failure(self):
		"""Show offline messagebox and schedule destroy of Custom_families.

		Both deferred via run() so the current install-step callstack
		unwinds cleanly before the COMP disappears.
		"""
		run(
			"ui.messageBox('Custom families', "
			"'Connessione assente: impossibile scaricare il framework da GitHub. "
			"Il componente verra rimosso.')",
			delayFrames=1
		)
		run(
			"target = op(args[0]); target.destroy() if target is not None else None",
			CUSTOM_FAMILIES_PATH,
			delayFrames=2
		)

	def _initialize_toolbar(self):
		"""Run split + top-pane type change + height minimize in a single frame.

		Splitting across deferred steps causes a visible flicker (you'd see
		the split happen first, then a frame later the type change, then the
		height collapse). Bundling them keeps the transition atomic from the
		user's perspective.
		"""
		self._split_top_bottom()
		self._set_top_pane_panel()
		self._minimize_top_pane()

	def _set_toolbar_styling(self, enabled, outline=True):
		"""Single toggle for the pane1 visual styling — background +
		(optionally) border outline + the chop() expressions that drive the
		border colors.

		enabled=True  → Custom_families look (bgalpha=1, bgcolor=
		    (0.1843, 0.1882, 0.2), and if outline=True borderar/ag/ab driven
		    by chop refs and the 4 border sources set to Border A)
		enabled=False → TD default (bgalpha=0, bgcolor=(0,0,0), and if
		    outline=True border expressions cleared and sources Off)

		outline=False leaves the border parameters untouched. Useful when
		you want to apply only the background portion of the styling.

		The chop() expressions reference Custom_families_button which is
		installed at a later step; they momentarily error until that COMP
		exists, then resolve automatically — TD doesn't lock expressions at
		set-time.
		"""
		pane = self.top_panebar
		if pane is None:
			return

		if enabled:
			bg_alpha = 1
			bg_rgb = (0.0093, 0, 0.025)
			border_exprs = {
				'borderar': "chop('./Custom_families_button/Arrow/Color/null1/r')",
				'borderag': "chop('./Custom_families_button/Arrow/Color/null1/g')",
				'borderab': "chop('./Custom_families_button/Arrow/Color/null1/b')",
			}
			border_source = 1
		else:
			bg_alpha = 0
			bg_rgb = (0, 0, 0)
			border_exprs = {'borderar': '', 'borderag': '', 'borderab': ''}
			border_source = 0

		def set_par(par_name, value):
			par = getattr(pane.par, par_name, None)
			if par is None:
				return
			try:
				par.val = value
			except Exception:
				pass

		def set_expr(par_name, expr_value):
			par = getattr(pane.par, par_name, None)
			if par is None:
				return
			try:
				par.expr = expr_value
			except Exception:
				pass

		# Background (always applied with `enabled` value)
		set_par('bgalpha', bg_alpha)
		set_par('bgcolorr', bg_rgb[0])
		set_par('bgcolorg', bg_rgb[1])
		set_par('bgcolorb', bg_rgb[2])
		if not outline:
			return
		# Border channel expressions + source dropdowns
		for par_name, expr_value in border_exprs.items():
			set_expr(par_name, expr_value)
		for par_name in ('leftborder', 'rightborder', 'bottomborder', 'topborder'):
			set_par(par_name, border_source)

	def _normalize_to_pane1(self):
		# TD's splitBottom() puts the *currently active* pane on top. After an
		# uninstall, the surviving pane may be named 'pane2' (or another), and
		# splitting from there would place the toolbar Panel on that pane while
		# the new pane (with the freed 'pane1' slot) would land at the bottom —
		# causing the alternating-install bug. To make every install start from
		# the same deterministic state we must end this normalization with a
		# single pane named 'pane1' as the active pane.

		# First pass: close every pane whose name is not 'pane1'.
		self._close_panes_not_named('pane1')

		pane1 = self._find_pane_by_name('pane1')
		if pane1 is not None:
			pane1.changeType(PaneType.NETWORKEDITOR)
			return

		# No 'pane1' currently exists. Force TD to allocate the 'pane1' slot by
		# splitting the survivor. The new pane will take the lowest free name
		# (typically 'pane1'). Then close every non-pane1 pane.
		survivor = self._get_base_pane()
		if survivor is None:
			return

		survivor.splitBottom()
		self._close_panes_not_named('pane1')

		pane1 = self._find_pane_by_name('pane1')
		if pane1 is not None:
			pane1.changeType(PaneType.NETWORKEDITOR)

	def _close_panes_not_named(self, target_name):
		# ui.panes mutates while we close, so refresh the lookup each iteration.
		# The range guard prevents infinite loops if a pane refuses to close.
		for _ in range(20):
			target = None
			for pane in ui.panes:
				if pane.name != target_name:
					target = pane
					break
			if target is None:
				return
			target.close()

	def _find_pane_by_name(self, target_name):
		for pane in ui.panes:
			if pane.name == target_name:
				return pane
		return None

	def _split_top_bottom(self):
		# Look up pane1 by name with a fresh iteration. Do NOT use
		# ui.panes.current: after _normalize_to_pane1 closes panes, it can
		# still return a stale reference to a now-closed pane (its cached
		# `.type` still reads NETWORKEDITOR), which then raises
		# "Invalid Pane object" on splitBottom.
		pane1 = self._find_pane_by_name('pane1')
		if pane1 is None:
			return

		# _normalize_to_pane1 guarantees pane1 is the only pane, NETWORKEDITOR
		# type, and active. splitBottom() therefore reliably keeps pane1 on
		# top and creates the workspace below.
		new_pane = pane1.splitBottom()
		self.ui_root.store(TOP_PANE_STORE_KEY, pane1.id)
		self.ui_root.store(BOTTOM_PANE_STORE_KEY, new_pane.id)

	def _minimize_top_pane(self):
		bottom_pane = self._get_bottom_pane()
		if bottom_pane is None:
			return

		# Counter-intuitive but intentional: writing the ratio on the bottom pane
		# is what collapses the toolbar area above in this layout.
		bottom_pane.ratio = BOTTOM_PANE_LOCK_RATIO

	def _set_top_pane_panel(self):
		top_pane = self._get_top_pane()
		if top_pane is None:
			return

		# We only change the pane type here. We do NOT set top_pane.owner to
		# /ui/panes/panebar/pane1 because that makes TD draw unwanted built-in UI
		# (for example the mini timeline) inside the toolbar strip. pane1 stays
		# the logical toolbar target, but not the visible panel owner.
		top_pane = top_pane.changeType(PaneType.PANEL)
		self.ui_root.store(TOP_PANE_STORE_KEY, top_pane.id)
		self._set_bottom_pane_network_owner()

	def _enable_runtime_cook(self, custom_families_comp):
		runtime_comp = custom_families_comp.op(RUNTIME_NAME)
		if runtime_comp is None:
			return
		if runtime_comp.allowCooking:
			return

		runtime_comp.allowCooking = True

	def _enable_local_cook(self, custom_families_comp):
		local_comp = custom_families_comp.op(LOCAL_NAME)
		if local_comp is None:
			return
		if local_comp.allowCooking:
			return

		local_comp.allowCooking = True

	def _set_bottom_pane_network_owner(self):
		bottom_pane = self._get_bottom_pane()
		if bottom_pane is None:
			return

		# The lower pane must stay a normal project network editor with the native
		# path bar and widgets, so we force it back to /project1 explicitly.
		bottom_owner = op(BOTTOM_NETWORK_OWNER_PATH)
		if bottom_owner is None:
			return

		bottom_pane.owner = bottom_owner

	def _disable_runtime_cook(self, custom_families_comp):
		runtime_comp = custom_families_comp.op(RUNTIME_NAME)
		if runtime_comp is None:
			return

		runtime_comp.allowCooking = False

	def _install_watcher(self, custom_families_comp):
		watcher_source = custom_families_comp.op(WATCHER_SOURCE_PATH)
		if watcher_source is None:
			return

		plugins_root = self._get_or_create_plugins_root()
		if plugins_root is None:
			return

		watcher_copy = self._replace_child(plugins_root, watcher_source, WATCHER_NAME)
		if watcher_copy is not None:
			watcher_copy.allowCooking = True

	def _hide_top_panebar_children(self):
		if self.top_panebar is None:
			return

		for child in self.top_panebar.children:
			if child.name in TOP_PANEBAR_KEEP_NAMES:
				continue
			if hasattr(child.par, 'display'):
				child.par.display = 0

	def _install_toolbar_button(self, custom_families_comp):
		self._install_toolbar_inject(custom_families_comp, CUSTOM_FAMILIES_BUTTON_SOURCE_PATH, CUSTOM_FAMILIES_BUTTON_NAME)

	def _wire_toolbar_button(self):
		self._wire_toolbar_inject(CUSTOM_FAMILIES_BUTTON_NAME)

	def _install_toolbar_inject(self, custom_families_comp, source_path, target_name):
		if self.top_panebar is None:
			return

		source_comp = custom_families_comp.op(source_path)
		if source_comp is None:
			return

		self._replace_child(self.top_panebar, source_comp, target_name)

	def _wire_toolbar_inject(self, target_name):
		if self.top_panebar is None:
			return

		toolbar_comp = self.top_panebar.op(target_name)
		emptypanel = self.top_panebar.op(EMPTYPANEL_NAME)
		if toolbar_comp is None or emptypanel is None:
			return

		toolbar_comp.inputCOMPConnectors[0].connect(emptypanel)

	def _wire_pages(self):
		if self.menu_op is None:
			return

		pages = self.menu_op.op(PAGES_NAME)
		if pages is None:
			return

		familypanel = self.menu_op.op(FAMILYPANEL_NAME)
		emptypanel = self.menu_op.op(EMPTYPANEL_NAME)
		select_available = self.menu_op.op(SELECT_AVAILABLE_NAME)
		null3 = self.menu_op.op(NULL3_NAME)
		null4 = self.menu_op.op(NULL4_NAME)
		if familypanel is not None:
			familypanel.allowCooking = False
			for con in familypanel.inputCOMPConnectors:
				con.disconnect()

		if select_available is not None:
			pages.inputConnectors[0].connect(select_available)

		if emptypanel is not None and pages.inputCOMPConnectors:
			pages.inputCOMPConnectors[0].connect(emptypanel)

		if null4 is not None:
			null4.inputConnectors[0].connect(pages.op(PAGES_OUT1_PATH))

		if null3 is not None:
			null3.inputConnectors[0].connect(pages.op(PAGES_OUT2_PATH))

	def _wire_page_number(self):
		if self.menu_op is None:
			return

		page_number = self.menu_op.op(PAGE_NUMBER_NAME)
		searchpanel = self.menu_op.op(SEARCHPANEL_NAME)
		if page_number is None or searchpanel is None:
			return

		page_number.inputCOMPConnectors[0].connect(searchpanel)

	def _set_menu_label_width(self):
		label = op(LABEL_PATH)
		if label is None:
			return

		label.par.w = 578

	def _install_dialog_inject(self, custom_families_comp, source_path, target_name):
		if self.menu_op is None:
			return

		source_comp = custom_families_comp.op(source_path)
		if source_comp is None:
			return

		self._replace_child(self.menu_op, source_comp, target_name)

	def _replace_child(self, target_parent, source_comp, target_name):
		existing = target_parent.op(target_name)
		if existing is not None:
			existing.destroy()

		copied_comp = target_parent.copy(source_comp)
		copied_comp.name = target_name
		return copied_comp

	def _get_or_create_plugins_root(self):
		if self.plugins_root is not None:
			return self.plugins_root

		if self.ui_root is None:
			return None

		self.plugins_root = self.ui_root.op(PLUGINS_ROOT_NAME)
		if self.plugins_root is None:
			self.plugins_root = self.ui_root.create(baseCOMP, PLUGINS_ROOT_NAME)

		return self.plugins_root

	def _get_base_pane(self):
		if len(ui.panes) == 0:
			return None

		return ui.panes[0]

	def _get_top_pane(self):
		pane_id = self.ui_root.fetch(TOP_PANE_STORE_KEY, -1)
		for pane in ui.panes:
			if pane.id == pane_id:
				return pane

		return None

	def _get_bottom_pane(self):
		pane_id = self.ui_root.fetch(BOTTOM_PANE_STORE_KEY, -1)
		for pane in ui.panes:
			if pane.id == pane_id:
				return pane

		return None

	def _show_message(self, text):
		run("ui.messageBox('Custom families', {!r})".format(text), delayFrames=1)
