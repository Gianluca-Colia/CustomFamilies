"""
Execute DAT — Install_window bootstrap.

Embedded-assets workflow: Font/ and Images/ used by the install dialog
live inside the .tox itself, so we no longer prefetch them from GitHub
before opening the window. The full plugin install (Install.Run) handles
the on-disk download separately.
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

	# Branch (3): already in /ui/Plugins → open the dialog directly.
	# Font/ and Images/ are embedded inside the .tox, so no prefetch needed.
	try:
		target.cook(force=True)
	except Exception:
		pass
	# 15 frames is the safe value across Windows and macOS — on Mac the
	# pulse arriving too early caused the dialog to never open.
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
