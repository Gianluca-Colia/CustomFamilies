"""
CHOP Execute DAT
Menu action bridge.
"""

ACTION_NAME = 'Exportfamily'
TRIGGER_COOLDOWN_FRAMES = 2


def _show_message(title, message, buttons=None):
	if buttons:
		return ui.messageBox(title, str(message), buttons=buttons)
	return ui.messageBox(title, str(message))


def _get_family_comp():
	return parent(2)


def _get_component_ext(family_comp):
	if family_comp is None:
		return None

	ext_obj = getattr(family_comp, 'ComponentEXT', None)
	if ext_obj is not None:
		return ext_obj

	ext_ns = getattr(family_comp, 'ext', None)
	if ext_ns is not None:
		ext_obj = getattr(ext_ns, 'ComponentEXT', None)
		if ext_obj is not None:
			return ext_obj

	return None


def _can_trigger_now():
	last_frame = me.fetch('cf_last_trigger_frame', -1000000)
	now_frame = absTime.frame

	if (now_frame - last_frame) < TRIGGER_COOLDOWN_FRAMES:
		return False

	me.store('cf_last_trigger_frame', now_frame)
	return True


def _export_family():
	family_comp = _get_family_comp()
	component_ext = _get_component_ext(family_comp)

	if component_ext is not None and hasattr(component_ext, 'ExportFamily'):
		try:
			return bool(component_ext.ExportFamily())
		except Exception as e:
			_show_message('Export family', 'Export failed: {}'.format(e))
			return False

	_show_message('Export family', 'ComponentEXT.ExportFamily not available.')
	return False


def _dispatch_action(action_name):
	action_name = str(action_name or '').strip()

	if action_name == 'Exportfamily':
		return _export_family()

	_show_message('Menu action', "Unhandled action: '{}'".format(action_name))
	return False


def onOffToOn(channel, sampleIndex, val, prev):
	if not _can_trigger_now():
		return False
	return _dispatch_action(ACTION_NAME)


def whileOn(channel, sampleIndex, val, prev):
	return


def onOnToOff(channel, sampleIndex, val, prev):
	return


def whileOff(channel, sampleIndex, val, prev):
	return


def onValueChange(channel, sampleIndex, val, prev):
	return
