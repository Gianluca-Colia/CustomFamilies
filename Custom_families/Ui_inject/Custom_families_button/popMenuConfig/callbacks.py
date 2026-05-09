"""
PopMenu callbacks

Callbacks always take a single argument, which is a dictionary
of values relevant to the callback. Print this dictionary to see what is
being passed. The keys explain what each item is.

PopMenu info keys:
	'index': either item index or -1 for none
	'item': the item label in the menu list
	'row': the row from the wired dat input, if applicable
	'details': details provided by object that caused menu to open
"""

Uninstall_window = '/ui/Plugins/Custom_families/Dialogs/Uninstall_window'

def onSelect(info):
	"""
	User selects a menu option
	"""
	if info['item'] == 'Uninstall':
		window = op(Uninstall_window)
		if window is None:
			return
		# Force-cook the dialog and every descendant before pulsing Winopen.
		# The dialog has been dormant since install, so its panel children
		# (including the Cancel button) haven't generated render output and
		# would appear black for one frame after open. Cooking the subtree
		# now + deferring the pulse 15 frames mirrors the fix used in
		# Install_window/execute1.onCreate.
		try:
			window.cook(force=True)
		except Exception:
			pass
		try:
			for child in window.findChildren(depth=None):
				try:
					child.cook(force=True)
				except Exception:
					pass
		except Exception:
			pass
		run("args[0].par.Winopen.pulse()", window, delayFrames=15)

def onRollover(info):
	"""
	Mouse rolled over an item
	"""

def onOpen(info):
	"""
	Menu opened
	"""

def onClose(info):
	"""
	Menu closed
	"""

def onMouseDown(info):
	"""
	Item pressed
	"""

def onMouseUp(info):
	"""
	Item released
	"""

def onClick(info):
	"""
	Item pressed and released
	"""

def onLostFocus(info):
	"""
	Menu lost focus
	"""
