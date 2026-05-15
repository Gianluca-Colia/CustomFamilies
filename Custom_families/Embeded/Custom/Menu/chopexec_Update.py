"""
CHOP Execute DAT
Menu action bridge.
"""

ACTION_NAME = 'Update'


def _show_message(title, message, buttons=None):
	if buttons:
		return ui.messageBox(title, str(message), buttons=buttons)
	return ui.messageBox(title, str(message))


def _get_family_comp():
	return parent(2)


def _choose_tox_path():
	start_folder = project.folder or '/'
	path = ui.chooseFile(
		load=True,
		start=start_folder,
		title='Select family TOX',
		fileTypes=['tox']
	)

	if not path:
		return ''

	return str(path).strip()


def _import_family_for_update(family_comp, tox_path):
	if family_comp is None or not tox_path:
		return None

	try:
		parent_comp = family_comp.parent()
	except Exception:
		parent_comp = None

	if parent_comp is None:
		return None

	try:
		new_comp = parent_comp.loadTox(tox_path)
	except Exception as e:
		_show_message('Update', 'Import failed:\n{}'.format(e))
		return None

	if new_comp is None:
		return None

	try:
		new_comp.nodeX = family_comp.nodeX + 200
		new_comp.nodeY = family_comp.nodeY
	except Exception:
		pass

	try:
		if hasattr(new_comp.par, 'Install'):
			new_comp.par.Install = 1
	except Exception:
		pass

	return new_comp


def _manual_update():
	family_comp = _get_family_comp()
	tox_path = _choose_tox_path()

	if not tox_path:
		return False

	new_comp = _import_family_for_update(family_comp, tox_path)
	return new_comp is not None


def _dispatch_action(action_name):
	action_name = str(action_name or '').strip()

	if action_name == 'Update':
		return _manual_update()

	_show_message('Menu action', 'Unhandled action: {}'.format(action_name))
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
