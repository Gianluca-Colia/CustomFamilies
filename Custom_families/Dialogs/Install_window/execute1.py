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
	       - schedule Winopen.pulse on the copy's Install_window
	       - destroy the original (deferred)
	  3. If the host IS already inside /ui/Plugins: open the dialog directly.

	Why we trigger the pulse from this branch instead of relying on the
	copy's own onCreate to fall into branch (3): on macOS TouchDesigner
	doesn't always re-fire onCreate on Execute DATs that were created via
	a parent .copy(). Scheduling the pulse explicitly on the copy makes
	the dialog open reliably on both Windows and macOS.
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

	if host_parent == plugins:
		# Already in /ui/Plugins → open immediately.
		_schedule_dialog_open(target)
		return

	# Outside /ui/Plugins: relocate.
	# If a copy already lives at /ui/Plugins/Custom_families (previous
	# install), don't duplicate — open the existing dialog and drop the
	# stray instance.
	existing = plugins.op('Custom_families')
	if existing is not None:
		existing_window = existing.op('Dialogs/Install_window')
		if existing_window is not None:
			_schedule_dialog_open(existing_window)
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

	# Open the dialog on the copied Install_window. Doing this from here
	# (rather than waiting for the copy's onCreate to re-fire) is what
	# makes the open reliable on macOS.
	if copied is not None:
		copied_window = copied.op('Dialogs/Install_window')
		if copied_window is not None:
			_schedule_dialog_open(copied_window)

	# Destroy the source after the current callstack unwinds; otherwise we
	# would tear down our own DAT mid-execution.
	run("args[0].destroy() if args[0] is not None else None", host, delayFrames=2)


def _schedule_dialog_open(install_window):
	"""Cook the Install_window and pulse Winopen after a short delay so
	any pending COMP cooking settles before the window appears.
	"""
	if install_window is None:
		return
	try:
		install_window.cook(force=True)
	except Exception:
		pass
	# 15 frames is the safe value across Windows and macOS — a tighter
	# delay caused the pulse to arrive before the relocated COMP had
	# settled and the dialog stayed closed on Mac.
	run("args[0].par.Winopen.pulse()", install_window, delayFrames=15)


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
