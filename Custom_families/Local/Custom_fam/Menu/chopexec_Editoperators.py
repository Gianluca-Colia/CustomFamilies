"""
CHOP Execute DAT
Menu action bridge.
"""

ACTION_NAME = 'Editoperators'


def _get_family_comp():
	return parent(2)


def _find_custom_operators(family_comp):
	if family_comp is None:
		return None
	try:
		target = family_comp.op('Custom_operators')
		if target is not None:
			return target
	except Exception:
		pass
	try:
		results = family_comp.findChildren(name='Custom_operators', maxDepth=4)
		if results:
			return results[0]
	except Exception:
		pass
	return None


def _get_active_pane():
	try:
		pane = ui.panes.current
		if pane is not None and getattr(pane, 'type', None) == PaneType.NETWORKEDITOR:
			return pane
	except Exception:
		pass
	try:
		for pane in ui.panes:
			if getattr(pane, 'type', None) == PaneType.NETWORKEDITOR:
				return pane
	except Exception:
		pass
	return None


def _set_pane_owner(pane, owner_comp):
	if pane is None or owner_comp is None:
		return False
	try:
		pane.owner = owner_comp
		return True
	except Exception:
		return False


def _stored_custom_ops_pane():
	try:
		candidate = me.fetch('cf_editcustom_right_pane', None)
	except Exception:
		candidate = None
	if candidate is None:
		return None
	try:
		if getattr(candidate, 'type', None) != PaneType.NETWORKEDITOR:
			return None
	except Exception:
		return None
	return candidate


def _store_custom_ops_pane(pane):
	if pane is None:
		return
	try:
		me.store('cf_editcustom_right_pane', pane)
	except Exception:
		pass


def _has_workspace_split():
	count = 0
	try:
		for pane in ui.panes:
			if getattr(pane, 'type', None) == PaneType.NETWORKEDITOR:
				count += 1
				if count >= 2:
					return True
	except Exception:
		return False
	return False


def _edit_custom_operators():
	family_comp = _get_family_comp()

	custom_ops = _find_custom_operators(family_comp)
	if custom_ops is None:
		return False

	active_pane = _get_active_pane()
	if active_pane is None:
		return False

	target_pane = _stored_custom_ops_pane() if _has_workspace_split() else None
	if target_pane is not None:
		return _set_pane_owner(target_pane, custom_ops)

	try:
		target_pane = active_pane.splitRight()
	except Exception:
		return False

	if not _set_pane_owner(target_pane, custom_ops):
		return False

	_store_custom_ops_pane(target_pane)

	return True


def _dispatch_action(action_name):
	action_name = str(action_name or '').strip()

	if action_name == 'Editoperators':
		return _edit_custom_operators()
	return False


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
