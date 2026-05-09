import os
import shutil

UI_ROOT_PATH = '/ui'
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


def Run():
	_restore_top_panebar_children()
	_set_toolbar_styling(False)
	_restore_familypanel()
	_restore_families_outputs()
	_destroy_toolbar_child(LOCAL_BAR_NAME)
	_destroy_toolbar_child(SERVER_BAR_NAME)
	_destroy_toolbar_child(CUSTOM_FAMILIES_BUTTON_NAME)
	_destroy_menu_child(PAGES_NAME)
	_destroy_menu_child(PAGE_NUMBER_NAME)
	run("op({!r}).module._close_top_pane_step()".format(me.path), delayFrames=1)


def _close_top_pane_step():
	_close_top_pane()
	run("op({!r}).module._finish_step()".format(me.path), delayFrames=1)


def _finish_step():
	run("op({!r}).module._destroy_watcher_step()".format(me.path), delayFrames=1)


def _destroy_watcher_step():
	# Manual-delete fallback path: clear the on-disk install before this
	# DAT goes away with its parent. Idempotent — Uninstall.Run also
	# rmtrees this folder, so on the official uninstall path this is a
	# no-op. Errors are swallowed so a locked file can't block the COMP
	# destruction below.
	try:
		if os.path.isdir(SCRIPTS_DISK_ROOT):
			shutil.rmtree(SCRIPTS_DISK_ROOT, ignore_errors=True)
	except Exception:
		pass
	parent().destroy()


def _close_top_pane():
	ui_root = op(UI_ROOT_PATH)
	pane_id = ui_root.fetch(TOP_PANE_STORE_KEY, -1)
	for pane in ui.panes:
		if pane.id != pane_id:
			continue
		pane.close()
		break

	ui_root.store(TOP_PANE_STORE_KEY, -1)


def _destroy_menu_child(child_name):
	menu_op = op(MENU_OP_PATH)
	if menu_op is None:
		return

	child = menu_op.op(child_name)
	if child is None:
		return

	child.destroy()


def _destroy_toolbar_child(child_name):
	top_panebar = op(TOP_PANEBAR_PATH)
	if top_panebar is None:
		return

	child = top_panebar.op(child_name)
	if child is None:
		return

	child.destroy()


def _restore_top_panebar_children():
	top_panebar = op(TOP_PANEBAR_PATH)
	if top_panebar is None:
		return

	for child in top_panebar.children:
		_restore_display(child)

	for child in top_panebar.findChildren(depth=99):
		_restore_display(child)


def _restore_display(child):
	if not child.isCOMP:
		return
	if child.name in TOP_PANEBAR_SKIP_DISPLAY_ON:
		return
	display_par = child.pars('display')
	if not display_par:
		return
	display_par[0].val = 1


def _set_toolbar_styling(enabled):
	"""Module-style mirror of Install._set_toolbar_styling — single toggle
	for pane1 background + border outline + chop() expressions on the
	border channels."""
	pane = op(TOP_PANEBAR_PATH)
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


def _restore_familypanel():
	menu_op = op(MENU_OP_PATH)
	if menu_op is None:
		return

	familypanel = menu_op.op(FAMILYPANEL_NAME)
	emptypanel = menu_op.op(EMPTYPANEL_NAME)
	if familypanel is None or emptypanel is None:
		return

	familypanel.allowCooking = True
	familypanel.inputCOMPConnectors[0].connect(emptypanel)


def _restore_families_outputs():
	menu_op = op(MENU_OP_PATH)
	if menu_op is None:
		return

	families = menu_op.op(FAMILIES_NAME)
	null3 = menu_op.op(NULL3_NAME)
	null4 = menu_op.op(NULL4_NAME)
	if families is None or null3 is None or null4 is None:
		return

	null4.inputConnectors[0].connect(families.op('out1'))
	null3.inputConnectors[0].connect(families.op('out2'))
