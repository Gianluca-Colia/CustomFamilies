"""
CHOP Execute DAT
Prepare manual rename editing from the /ui bookmark button.
"""


def _family_roots():
	roots = []
	for path in ('/Custom_families', '/project1/Custom_families'):
		try:
			root = op(path)
		except Exception:
			root = None
		if root is not None and root not in roots:
			roots.append(root)
	return roots


def _selected_families():
	found = []
	seen = set()
	for root in _family_roots():
		for child in getattr(root, 'children', []):
			try:
				if not getattr(child, 'isCOMP', False):
					continue
			except Exception:
				continue
			try:
				if not hasattr(child.par, 'Selected') or not bool(child.par.Selected.eval()):
					continue
			except Exception:
				continue
			try:
				child_path = str(child.path)
			except Exception:
				child_path = ''
			if not child_path or child_path in seen:
				continue
			seen.add(child_path)
			found.append(child)
	return found


def _bookmark_bar():
	try:
		return op('/ui/panes/panebar/pane1/Local_bar')
	except Exception:
		return None


def _bookmark_button_for_family(family_comp):
	if family_comp is None:
		return None

	bookmark_bar = _bookmark_bar()
	if bookmark_bar is None:
		return None

	try:
		family_path = str(family_comp.path).strip()
	except Exception:
		family_path = ''

	for child in getattr(bookmark_bar, 'children', []):
		try:
			if not str(child.name).startswith('button_'):
				continue
		except Exception:
			continue

		try:
			owner_path = str(child.fetch('cf_owner_path', '') or child.fetch('family_owner_path', '')).strip()
		except Exception:
			owner_path = ''

		if family_path and owner_path == family_path:
			return child

	try:
		return bookmark_bar.op('button_{}'.format(family_comp.name))
	except Exception:
		return None


def _parameter_value(par):
	if par is None:
		return ''
	try:
		return par.eval()
	except Exception:
		try:
			return par.val
		except Exception:
			return ''


def _make_parameter_editable(par):
	if par is None:
		return False
	value = _parameter_value(par)
	updated = False
	for attr_name in ('bindExpr', 'expr'):
		try:
			if getattr(par, attr_name, ''):
				setattr(par, attr_name, '')
				updated = True
		except Exception:
			pass
	try:
		par.val = value
		updated = True
	except Exception:
		try:
			par = value
		except Exception:
			pass
	return updated


def _set_text_edit_mode(text_op):
	if text_op is None or not hasattr(text_op, 'par'):
		return False

	try:
		edit_par = getattr(text_op.par, 'editmode', None)
	except Exception:
		edit_par = None
	if edit_par is None:
		return False

	menu_names = []
	menu_labels = []
	try:
		menu_names = list(edit_par.menuNames or [])
	except Exception:
		menu_names = []
	try:
		menu_labels = list(edit_par.menuLabels or [])
	except Exception:
		menu_labels = []

	candidates = []
	candidates.extend(menu_names)
	candidates.extend(menu_labels)
	candidates.extend(('Click to Edit', 'Clicktoedit', 'Editable', 'edit', 'clicktoedit', 'click'))

	for value in candidates:
		try:
			value_str = str(value).strip().lower()
		except Exception:
			value_str = ''
		if not value_str or value_str == 'locked':
			continue
		if 'edit' not in value_str and 'click' not in value_str:
			continue
		try:
			edit_par.val = value
			return True
		except Exception:
			pass
		try:
			text_op.par.editmode = value
			return True
		except Exception:
			pass

	try:
		if len(menu_names) > 1:
			edit_par.menuIndex = 1
			return True
	except Exception:
		pass

	return False


def _button_custom_par(button, *names):
	if button is None or not hasattr(button, 'par'):
		return None
	for name in names:
		try:
			par = getattr(button.par, name, None)
		except Exception:
			par = None
		if par is not None:
			return par
	return None


def _set_button_custom_value(button, value, *names):
	par = _button_custom_par(button, *names)
	if par is None:
		return False
	for attr_name in ('expr', 'bindExpr'):
		try:
			setattr(par, attr_name, '')
		except Exception:
			pass
	try:
		par.val = value
		return True
	except Exception:
		pass
	for name in names:
		try:
			setattr(button.par, name, value)
			return True
		except Exception:
			pass
	return False


def _set_button_edit_mode(button):
	edit_par = _button_custom_par(button, 'Editmode', 'EditMode')
	if edit_par is None:
		return False

	menu_names = []
	menu_labels = []
	try:
		menu_names = list(edit_par.menuNames or [])
	except Exception:
		pass
	try:
		menu_labels = list(edit_par.menuLabels or [])
	except Exception:
		pass

	candidates = list(menu_names) + list(menu_labels) + ['Click to Edit', 'Clicktoedit', 'Editable', 'edit', 'click']
	for value in candidates:
		try:
			value_str = str(value).strip().lower()
		except Exception:
			value_str = ''
		if not value_str or value_str == 'locked':
			continue
		if 'edit' not in value_str and 'click' not in value_str:
			continue
		try:
			edit_par.expr = ''
		except Exception:
			pass
		try:
			edit_par.bindExpr = ''
		except Exception:
			pass
		try:
			edit_par.val = value
			return True
		except Exception:
			pass

	try:
		if len(menu_names) > 1:
			edit_par.menuIndex = 1
			return True
	except Exception:
		pass
	return False


def _make_button_editable(button):
	if button is None:
		return False
	updated = False

	text_op = None
	try:
		text_op = button.op('text')
	except Exception:
		text_op = None

	if text_op is not None and hasattr(text_op, 'par'):
		try:
			if hasattr(text_op.par, 'text') and _make_parameter_editable(text_op.par.text):
				updated = True
		except Exception:
			pass
		try:
			text_op.selected = True
		except Exception:
			pass
		try:
			text_op.current = True
		except Exception:
			pass

	try:
		button.selected = True
	except Exception:
		pass
	try:
		if _set_button_edit_mode(button):
			updated = True
	except Exception:
		pass
	if _set_button_custom_value(button, 0, 'Clickthrough', 'ClickThrough'):
		updated = True
	if _set_button_custom_value(button, 2, 'Cursor'):
		updated = True

	# Mark this button as being in rename mode so chopexec1/panelexec1 can guard
	try:
		button.store('cf_rename_mode', True)
	except Exception:
		pass

	return updated


def _select_bookmark_buttons(buttons):
	bookmark_bar = _bookmark_bar()
	if bookmark_bar is None:
		return False

	selected_any = False
	target_paths = []
	for button in buttons:
		if button is None:
			continue
		try:
			target_paths.append(str(button.path))
		except Exception:
			pass

	for child in getattr(bookmark_bar, 'children', []):
		try:
			child.selected = str(child.path) in target_paths
		except Exception:
			pass

	for button in buttons:
		if button is None:
			continue
		_make_button_editable(button)
		try:
			button.current = True
		except Exception:
			pass
		selected_any = True

	return selected_any


def _clear_selected_state(families, buttons):
	updated = False

	for family_comp in families or []:
		if family_comp is None:
			continue
		try:
			if hasattr(family_comp.par, 'Selected'):
				family_comp.par.Selected = 0
				updated = True
		except Exception:
			pass

	for button in buttons or []:
		if button is None:
			continue
		if _set_button_custom_value(button, 0, 'Selected'):
			updated = True
		try:
			if hasattr(button.par, 'value0'):
				button.par.value0 = 0
				updated = True
		except Exception:
			pass

	return updated


def onOffToOn(channel, sampleIndex, val, prev):
	try:
		parent(2).par.Selected = 0
	except Exception:
		pass

	selected = _selected_families()
	button_paths = []
	buttons = []

	if not selected:
		try:
			selected = [parent(2)]
		except Exception:
			selected = []

	family_paths = [str(comp.path) for comp in selected if comp is not None]

	for family_comp in selected:
		button = _bookmark_button_for_family(family_comp)
		if button is None:
			continue
		buttons.append(button)
		try:
			button_paths.append(str(button.path))
		except Exception:
			pass

	_clear_selected_state(selected, buttons)

	for target in (me, parent()):
		try:
			target.store('cf_rename_paths', list(family_paths))
		except Exception:
			pass
		try:
			target.store('cf_rename_button_paths', list(button_paths))
		except Exception:
			pass

	return _select_bookmark_buttons(buttons)


def whileOn(channel, sampleIndex, val, prev):
	return


def onOnToOff(channel, sampleIndex, val, prev):
	return


def whileOff(channel, sampleIndex, val, prev):
	return


def onValueChange(channel, sampleIndex, val, prev):
	return
