"""
CHOP Execute DAT
Menu action bridge.
"""

ACTION_NAME = 'Delete'


def _show_message(title, message, buttons=None):
	if buttons:
		return ui.messageBox(title, str(message), buttons=buttons)
	return ui.messageBox(title, str(message))


def _get_family_comp():
	# Strada principale: family/Menu/.../this_dat
	return parent(2)


def _get_component_ext(family_comp):
	ext_obj = getattr(family_comp, 'ComponentEXT', None)
	if ext_obj is not None:
		return ext_obj

	ext_ns = getattr(family_comp, 'ext', None)
	if ext_ns is not None:
		ext_obj = getattr(ext_ns, 'ComponentEXT', None)
		if ext_obj is not None:
			return ext_obj

	return None


def _destroy_comp_next_frame(comp):
	run(
		"target = op(args[0]); target.destroy() if target is not None else None",
		comp.path,
		delayFrames=1
	)
	return True


def _delete_family():
	family_comp = _get_family_comp()
	component_ext = _get_component_ext(family_comp)

	if component_ext is not None:
		component_ext.DeleteCleanup()

	_destroy_comp_next_frame(family_comp)
	return True


def _dispatch_action(action_name):
	action_name = str(action_name or '').strip()

	if action_name == 'Delete':
		return _delete_family()

	_show_message('Menu action', "Unhandled action: '{}'".format(action_name))
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
