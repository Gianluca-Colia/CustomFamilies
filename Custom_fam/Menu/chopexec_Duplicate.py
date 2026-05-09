"""
CHOP Execute DAT
Bridge tra menu e componente famiglia.

Duplicate esegue solo il copy nativo di TD — il rename automatico
di TD innesca RenameEXT → InstallerEXT che gestisce il resto.
"""

ACTION_NAME = 'Duplicate'


def _get_owner_comp():
	try:
		return parent(2)
	except Exception:
		return None


def _duplicate_owner_comp(owner_comp):
	if owner_comp is None:
		return False

	try:
		target_parent = owner_comp.parent()
	except Exception:
		return False

	if target_parent is None:
		return False

	try:
		duplicate = target_parent.copy(owner_comp)
	except Exception:
		return False

	if duplicate is None:
		return False

	try:
		duplicate.nodeX = owner_comp.nodeX + 150
	except Exception:
		pass

	try:
		duplicate.nodeY = owner_comp.nodeY
	except Exception:
		pass

	# The copy inherits Selected=1 from the original — reset both to avoid
	# multiple families appearing selected simultaneously.
	for comp in (owner_comp, duplicate):
		try:
			if hasattr(comp.par, 'Selected'):
				comp.par.Selected = 0
		except Exception:
			pass

	return True


def _dispatch_action(action_name):
	if action_name == 'Duplicate':
		return _duplicate_owner_comp(_get_owner_comp())
	return True


def onOffToOn(channel, sampleIndex, val, prev):
	return _dispatch_action(ACTION_NAME)


def whileOn(channel, sampleIndex, val, prev):
	return


def onOnToOff(channel, sampleIndex, val, prev):
	return


def whileOff(channel, sampleIndex, val, prev):
	return


def onValueChange(channel, sampleIndex, val, prev):
	return
