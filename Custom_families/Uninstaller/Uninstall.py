import os
import shutil

UI_ROOT_PATH = '/ui'
CUSTOM_FAMILIES_PATH = '/ui/Plugins/Custom_families'
WATCHER_PATH = '/ui/Plugins/Watcher_Custom_families'
UNINSTALL_LOADBAR_PATH = '/ui/Plugins/Custom_families/Dialogs/Uninstall_window/Loadbar'
MENU_OP_PATH = '/ui/dialogs/menu_op'
TOP_PANEBAR_PATH = '/ui/panes/panebar/pane1'
TOP_PANEBAR_SKIP_DISPLAY_ON = ('historydrop', 'addbookmark')
TOUCHDESIGNER_LOCAL_PATH = os.path.join(os.environ['LOCALAPPDATA'], 'Derivative', 'TouchDesigner099')
SCRIPTS_DISK_ROOT = os.path.join(TOUCHDESIGNER_LOCAL_PATH, 'Custom families')
CUSTOM_FAMILIES_BUTTON_NAME = 'Custom_families_button'
LOCAL_BAR_NAME = 'Local_bar'
SERVER_BAR_NAME = 'Server_bar'
PAGES_NAME = 'Pages'
PAGE_NUMBER_NAME = 'Page_number'
FAMILYPANEL_NAME = 'familypanel'
EMPTYPANEL_NAME = 'emptypanel'
FAMILIES_NAME = 'families'
NULL3_NAME = 'null3'
NULL4_NAME = 'null4'
TOP_PANE_STORE_KEY = 'cf_top_pane_id'


class Uninstall:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self.ui_root = op(UI_ROOT_PATH)
		self.menu_op = op(MENU_OP_PATH)
		self.top_panebar = op(TOP_PANEBAR_PATH)

	# ------------------------------------------------------------------
	# Public entrypoint — full uninstall, family-aware.
	#
	# Order matters: families inside Custom_families/Local and /Server have
	# their own watchers in Local_bar/Server_bar. Each family watcher cleans
	# up its menu_op injects when the family is destroyed (with a ~2 frame
	# deferred chain). If we destroyed Local_bar first, the family watchers
	# would die before they could schedule their cleanup, leaving menu_op
	# injects (insert_*, panel_execute_*, inject_*) orphaned.
	#
	# Sequence (relative frames):
	#   0  sync      visual restore — safe, no destroys
	#   +1           destroy Custom_families/Local  → family watchers fire
	#                family watchers schedule menu_op cleanup at +3
	#   +2           destroy Custom_families/Server → server-family watchers
	#                schedule cleanup at +4
	#   +5           destroy Local_bar / Server_bar / button / Pages /
	#                Page_number  (after all family watcher deferreds done)
	#   +6           close top pane
	#   +7           destroy Custom_families root
	# ------------------------------------------------------------------
	def Run(self):
		self._progress(1, 'Preparing uninstall')
		self._progress(2, 'Restoring panebar visibility')
		self._restore_top_panebar_children()
		self._progress(3, 'Restoring toolbar styling')
		self._set_toolbar_styling(False)
		self._progress(4, 'Restoring family panel')
		self._restore_familypanel()
		self._progress(5, 'Restoring families outputs')
		self._restore_families_outputs()
		self._progress(6, 'Removing Local container')
		self._schedule('_destroy_local_step', delay=1)

	def _destroy_local_step(self):
		# Destroying Local triggers each Local-installed family's watcher
		# (in /ui/panes/panebar/pane1/Local_bar/watcher_*) to fire onDestroy.
		# The family watcher synchronously schedules its own deferred run()
		# at delayFrames=2 to clean its menu_op injects. That deferred queue
		# survives even after the watcher itself is destroyed later.
		self._destroy_custom_families_child('Local')
		self._progress(7, 'Local families notified')
		self._progress(8, 'Removing Server container')
		self._schedule('_destroy_server_step', delay=1)

	def _destroy_server_step(self):
		self._destroy_custom_families_child('Server')
		self._progress(9, 'Server families notified')
		self._progress(10, 'Waiting for family menu_op cleanup')
		# Wait for family watchers' deferred menu_op cleanup (max +4 from
		# now, since the Server destroy fires watchers that schedule at +2)
		# before tearing down the toolbars they live in. We split the wait
		# into two progress checkpoints so the bar visibly advances.
		self._schedule('_wait_step_1', delay=1)

	def _wait_step_1(self):
		self._progress(11, 'Family menu_op cleanup in progress')
		self._schedule('_wait_step_2', delay=1)

	def _wait_step_2(self):
		self._progress(12, 'Family menu_op cleanup completing')
		self._schedule('_destroy_panebar_residues_step', delay=1)

	def _destroy_panebar_residues_step(self):
		self._progress(13, 'Removing Local toolbar')
		self._destroy_toolbar_child(LOCAL_BAR_NAME)
		self._progress(14, 'Removing Server toolbar')
		self._destroy_toolbar_child(SERVER_BAR_NAME)
		self._progress(15, 'Removing toolbar button')
		self._destroy_toolbar_child(CUSTOM_FAMILIES_BUTTON_NAME)
		self._progress(16, 'Removing Pages dialog')
		self._destroy_menu_child(PAGES_NAME)
		self._progress(17, 'Removing Page_number dialog')
		self._destroy_menu_child(PAGE_NUMBER_NAME)
		self._progress(18, 'Closing top pane')
		self._schedule('_close_top_pane_step', delay=1)

	def _close_top_pane_step(self):
		self._close_top_pane()
		self._progress(19, 'Top pane closed')
		self._progress(20, 'Removing Custom_families root')
		self._schedule('_destroy_custom_families_step', delay=1)

	def _destroy_custom_families_step(self):
		# Set progress to 21 BEFORE destroying anything — once the COMP is
		# gone the Loadbar (inside Uninstall_window inside Custom_families)
		# goes with it, so any later progress call is a no-op.
		self._progress(21, 'Uninstall complete')

		# Order matters: do every cleanup that touches state OUTSIDE
		# Custom_families (the watcher COMP, the on-disk LOCALAPPDATA copy)
		# BEFORE destroying the Custom_families root. Once we destroy the
		# root, the Uninstall DAT we're executing from goes with it and TD
		# can interrupt the current frame, leaving the watcher orphaned and
		# the disk folder still on disk.

		# 1. Watcher COMP — lives at /ui/Plugins/Watcher_Custom_families,
		#    a sibling of Custom_families, so it does NOT die automatically
		#    when the root is destroyed. Don't rely on its chopexec OnToOff
		#    chain either — if its Select CHOP lost its target inside
		#    Custom_families it can error instead of dropping cleanly to 0,
		#    and the transition never fires.
		watcher = op(WATCHER_PATH)
		if watcher is not None:
			try:
				watcher.destroy()
			except Exception as exc:
				debug('[Custom_families uninstall] watcher destroy failed: {}'.format(exc))

		# 2. On-disk install at LOCALAPPDATA. Non-fatal — if a file inside
		#    is locked we log and move on so the in-memory uninstall isn't
		#    blocked by disk state.
		self._remove_disk_folder()

		# 3. Custom_families root last (this DAT goes with it).
		target = op(CUSTOM_FAMILIES_PATH)
		if target is not None:
			target.destroy()

	def _remove_disk_folder(self):
		"""rmtree the LOCALAPPDATA install. Logs every per-file failure so
		a leftover folder doesn't fail silently — typical cause is a file
		still mapped by Sync to File on a DAT that hasn't been destroyed
		yet, which Windows refuses to delete with PermissionError.
		"""
		if not os.path.isdir(SCRIPTS_DISK_ROOT):
			return

		failures = []

		def _on_error(func, path, exc_info):
			failures.append((path, exc_info[1]))

		try:
			shutil.rmtree(SCRIPTS_DISK_ROOT, onerror=_on_error)
		except Exception as exc:
			debug('[Custom_families uninstall] rmtree raised: {}'.format(exc))
			return

		if failures:
			debug('[Custom_families uninstall] rmtree: {} item(s) could not be removed'.format(len(failures)))
			for path, err in failures[:5]:
				debug('  - {}: {}'.format(path, err))
		elif os.path.isdir(SCRIPTS_DISK_ROOT):
			debug('[Custom_families uninstall] rmtree completed but folder still present: {}'.format(SCRIPTS_DISK_ROOT))

	def _progress(self, step, label):
		"""Update the Uninstall_window Loadbar (Actualstep + Operation).

		Silent no-op if the Loadbar isn't reachable (dialog closed early or
		Custom_families already destroyed).
		"""
		bar = op(UNINSTALL_LOADBAR_PATH)
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

	def _destroy_custom_families_child(self, child_name):
		root = op(CUSTOM_FAMILIES_PATH)
		if root is None:
			return
		child = root.op(child_name)
		if child is None:
			return
		child.destroy()

	def _schedule(self, method_name, delay=1):
		"""Schedule the named extension method to run on a future frame.

		Mirrors Cleanup.py's `run("op({!r}).module._step()", ...)` chain, but
		dispatches through the class extension instead of the DAT module —
		each method is a regular `Uninstall` method, not a free function.
		"""
		run(
			"target = op(args[0]); "
			"method = getattr(target.ext.Uninstall, args[1], None) if target is not None else None; "
			"method() if method is not None else None",
			self.ownerComp.path,
			method_name,
			delayFrames=delay
		)

	def _close_top_pane(self):
		"""Close only the toolbar pane stored at install time (mirrors Cleanup)."""
		if self.ui_root is None:
			return
		pane_id = self.ui_root.fetch(TOP_PANE_STORE_KEY, -1)
		for pane in ui.panes:
			if pane.id != pane_id:
				continue
			pane.close()
			break
		self.ui_root.store(TOP_PANE_STORE_KEY, -1)

	def _destroy_menu_child(self, child_name):
		if self.menu_op is None:
			return

		child = self.menu_op.op(child_name)
		if child is None:
			return

		child.destroy()

	def _destroy_toolbar_child(self, child_name):
		if self.top_panebar is None:
			return

		child = self.top_panebar.op(child_name)
		if child is None:
			return

		child.destroy()

	def _restore_top_panebar_children(self):
		if self.top_panebar is None:
			return

		for child in self.top_panebar.children:
			self._restore_display(child)

		for child in self.top_panebar.findChildren(depth=99):
			self._restore_display(child)

	def _restore_display(self, child):
		if not child.isCOMP:
			return
		if child.name in TOP_PANEBAR_SKIP_DISPLAY_ON:
			return
		display_par = child.pars('display')
		if not display_par:
			return
		display_par[0].val = 1

	def _set_toolbar_styling(self, enabled):
		"""Mirror of Install._set_toolbar_styling — single toggle for pane1
		background + border outline + chop() expressions driving the border.

		enabled=True  → Custom_families look (bg alpha=1, dark gray bg,
		    chop refs on borderar/ag/ab, border sources = Border A)
		enabled=False → TD default (transparent black, expressions cleared,
		    border sources = Off)
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

		set_par('bgalpha', bg_alpha)
		set_par('bgcolorr', bg_rgb[0])
		set_par('bgcolorg', bg_rgb[1])
		set_par('bgcolorb', bg_rgb[2])
		for par_name, expr_value in border_exprs.items():
			set_expr(par_name, expr_value)
		for par_name in ('leftborder', 'rightborder', 'bottomborder', 'topborder'):
			set_par(par_name, border_source)

	def _restore_familypanel(self):
		if self.menu_op is None:
			return

		familypanel = self.menu_op.op(FAMILYPANEL_NAME)
		emptypanel = self.menu_op.op(EMPTYPANEL_NAME)
		if familypanel is None or emptypanel is None:
			return

		familypanel.allowCooking = True
		familypanel.inputCOMPConnectors[0].connect(emptypanel)

	def _restore_families_outputs(self):
		if self.menu_op is None:
			return

		families = self.menu_op.op(FAMILIES_NAME)
		null3 = self.menu_op.op(NULL3_NAME)
		null4 = self.menu_op.op(NULL4_NAME)
		if families is None or null3 is None or null4 is None:
			return

		null4.inputConnectors[0].connect(families.op('out1'))
		null3.inputConnectors[0].connect(families.op('out2'))
