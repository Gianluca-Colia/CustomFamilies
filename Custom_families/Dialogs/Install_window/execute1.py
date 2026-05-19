"""
Execute DAT — Install_window onCreate hook.

Relocates the host Custom_families COMP under /ui/Plugins on first
insertion, then opens the install dialog. Font/Images assets used by
the dialog are now embedded directly inside the .tox itself, so no
network prefetch is required — the window opens instantly.

Make sure the corresponding toggle is enabled in the Execute DAT.
"""


def onStart():
	return


def onCreate():
	"""
	Flow:
	  1. Resolve the host (Custom_families root = parent(3)).
	  2. If the host is NOT yet inside /ui/Plugins:
	       - get or create /ui/Plugins as a base COMP under /ui
	       - copy the host into it
	       - destroy the original (deferred, so this script completes safely)
	     The copy's own Install_window/execute1.onCreate will fire from the
	     new location and fall into branch (3) below.
	  3. If the host IS inside /ui/Plugins: cook + pulse Winopen to open dialog.
	"""
	target = parent()       # Install_window
	host = parent(3)        # Custom_families root
	if host is None:
		return

	ui_root = op('/ui')
	if ui_root is None:
		return

	plugins = ui_root.op('Plugins')
	if plugins is None:
		plugins = ui_root.create(baseCOMP, 'Plugins')
	if plugins is None:
		return

	try:
		host_parent = host.parent()
	except Exception:
		host_parent = None

	if host_parent != plugins:
		# Host is outside /ui/Plugins: relocate.
		# If a copy already lives at /ui/Plugins/Custom_families (previous install),
		# don't duplicate — just destroy this stray instance.
		existing = plugins.op('Custom_families')
		if existing is not None:
			run("args[0].destroy() if args[0] is not None else None", host, delayFrames=2)
			return
		try:
			copied = plugins.copy(host, name='Custom_families')
			if copied is not None:
				copied.nodeX = host.nodeX
				copied.nodeY = host.nodeY
		except Exception as e:
			debug('[Install_window.onCreate] copy to /ui/Plugins failed:', e)
			return
		# Destroy source after the current callstack unwinds; otherwise we
		# would tear down our own DAT mid-execution.
		run("args[0].destroy() if args[0] is not None else None", host, delayFrames=2)
		return

	# Branch (3): already in /ui/Plugins → open the dialog.
	# Font/Images are baked into the .tox at this point, so we can open
	# the dialog immediately without any network fetch.
	try:
		target.cook(force=True)
	except Exception:
		pass
	try:
		for child in target.findChildren(depth=None):
			try:
				child.cook(force=True)
			except Exception:
				pass
	except Exception:
		pass
	run("args[0].par.Winopen.pulse()", target, delayFrames=15)
	return


def onExit():
	return


def onFrameStart(frame: int):
	return


def onFrameEnd(frame: int):
	return


def onPlayStateChange(state: bool):
	return


def onDeviceChange():
	return


def onProjectPreSave():
	return


def onProjectPostSave():
	return
