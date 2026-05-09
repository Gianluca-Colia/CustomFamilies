UI_ROOT_PATH = '/ui'
TOP_PANE_STORE_KEY = 'cf_top_pane_id'
# Important: although the toolbar is logically "pane1", the runtime lock must
# work from the top pane id saved by the installer, not from pane.owner. We no
# longer assign /ui/panes/panebar/pane1 as the panel owner because doing so
# makes TouchDesigner render unwanted chrome/timeline in the toolbar area.
LOCK_RATIO = 0.9999
LOCK_TOLERANCE = 0.01


def _get_ui_root():
	ui_root = op(UI_ROOT_PATH)
	if ui_root is None:
		return None

	return ui_root


def _get_saved_pane(store_key):
	ui_root = _get_ui_root()
	if ui_root is None:
		return None

	pane_id = ui_root.fetch(store_key, -1)
	if pane_id == -1:
		return None

	for pane in ui.panes:
		if pane.id == pane_id:
			return pane

	return None


def _get_toolbar_pane():
	# The installer saves the real top pane id right after the known-good split.
	# This is the stable reference for the toolbar strip; relying on pane.owner
	# caused regressions as soon as we stopped showing pane1 directly.
	return _get_saved_pane(TOP_PANE_STORE_KEY)

def _enforce_lock():
	toolbar_pane = _get_toolbar_pane()
	if toolbar_pane is None:
		return

	# TD stores pane.ratio with float noise, so we only rewrite it when the user
	# has actually dragged the divider away from the locked value. The 0.9999
	# value is intentional here: in this top/bottom layout it is the working
	# direction for keeping the toolbar strip collapsed.
	if abs(toolbar_pane.ratio - LOCK_RATIO) > LOCK_TOLERANCE:
		toolbar_pane.ratio = LOCK_RATIO


def onStart():
	return


def onCreate():
	return


def onExit():
	return


def onFrameStart(frame):
	_enforce_lock()


def onFrameEnd(frame):
	return


def onPlayStateChange(state):
	return


def onDeviceChange():
	return


def onProjectPreSave():
	return


def onProjectPostSave():
	return
