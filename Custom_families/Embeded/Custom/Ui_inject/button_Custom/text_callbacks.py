# Text Component callbacks

from typing import Dict


def _button_comp(comp: textCOMP):
	try:
		return comp.parent()
	except Exception:
		return None


def _owner_from_button(button):
	if button is None:
		return None

	for fetch_key in ('cf_owner_path', 'family_owner_path'):
		try:
			owner_path = str(button.fetch(fetch_key, '')).strip()
		except Exception:
			owner_path = ''
		if owner_path:
			try:
				owner = op(owner_path)
			except Exception:
				owner = None
			if owner is not None:
				return owner

	try:
		name = str(button.name)
	except Exception:
		name = ''
	if name.startswith('button_'):
		family_name = name[len('button_'):]
		for path in (
			'/Custom_families/{}'.format(family_name),
			'/project1/Custom_families/{}'.format(family_name),
		):
			try:
				owner = op(path)
			except Exception:
				owner = None
			if owner is not None:
				return owner

	return None


def _editable_mode_value(edit_par):
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

	for value in list(menu_names) + list(menu_labels):
		try:
			value_str = str(value).strip().lower()
		except Exception:
			value_str = ''
		if not value_str or value_str == 'locked':
			continue
		if 'edit' in value_str or 'click' in value_str:
			return value

	if len(menu_names) > 1:
		return menu_names[1]
	return 1


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


def _set_par_expression(par, expr):
	if par is None:
		return False
	for attr_name in ('bindExpr', 'expr'):
		try:
			setattr(par, attr_name, '')
		except Exception:
			pass
	try:
		par.expr = expr
		return True
	except Exception:
		return False


def _owner_name_expr(owner):
	if owner is None:
		return repr('')
	try:
		owner_path = str(owner.path)
	except Exception:
		owner_path = ''
	fallback = ''
	try:
		fallback = str(owner.name)
	except Exception:
		fallback = ''
	return "(op({path!r}).name if op({path!r}) is not None else {fallback!r})".format(
		path=owner_path,
		fallback=fallback,
	)


def _owner_selected_expr(owner):
	if owner is None:
		return '0'
	try:
		owner_path = str(owner.path)
	except Exception:
		owner_path = ''
	return "(int(bool(op({path!r}).par.Selected.eval())) if op({path!r}) is not None and hasattr(op({path!r}).par, 'Selected') else 0)".format(
		path=owner_path,
	)


def _rebind_button_owner_pars(button, owner):
	if button is None or owner is None or not hasattr(button, 'par'):
		return False

	updated = False
	label_expr = _owner_name_expr(owner)
	selected_expr = _owner_selected_expr(owner)

	try:
		if _set_par_expression(getattr(button.par, 'label', None), label_expr):
			updated = True
	except Exception:
		pass

	for selected_name in ('Selected', 'selected'):
		try:
			if _set_par_expression(getattr(button.par, selected_name, None), selected_expr):
				updated = True
				break
		except Exception:
			pass

	for text_path in ('text', 'text1', 'button/text', 'button/text1'):
		try:
			text_op = button.op(text_path)
		except Exception:
			text_op = None
		if text_op is None or not hasattr(text_op, 'par'):
			continue
		try:
			if _set_par_expression(getattr(text_op.par, 'text', None), label_expr):
				updated = True
		except Exception:
			pass

	return updated


def _set_text_locked(comp: textCOMP):
	if comp is None or not hasattr(comp, 'par'):
		return False

	updated = False
	button = _button_comp(comp)

	# Clear rename mode flag so chopexec1/panelexec1 resume normal selection
	try:
		if button is not None:
			button.store('cf_rename_mode', False)
	except Exception:
		pass
	edit_par = _button_custom_par(button, 'Editmode', 'EditMode')
	if edit_par is None:
		try:
			edit_par = getattr(comp.par, 'editmode', None)
		except Exception:
			edit_par = None
	if edit_par is not None:
		for attr_name in ('expr', 'bindExpr'):
			try:
				setattr(edit_par, attr_name, '')
			except Exception:
				pass
		try:
			edit_par.val = 0
			updated = True
		except Exception:
			pass
	if not _set_button_custom_value(button, 1, 'Clickthrough', 'ClickThrough'):
		try:
			click_par = getattr(comp.par, 'clickthrough', None)
		except Exception:
			click_par = None
		if click_par is not None:
			for attr_name in ('expr', 'bindExpr'):
				try:
					setattr(click_par, attr_name, '')
				except Exception:
					pass
			try:
				comp.par.clickthrough = 1
				updated = True
			except Exception:
				pass
	else:
		updated = True

	if not _set_button_custom_value(button, 0, 'Cursor'):
		try:
			cursor_par = getattr(comp.par, 'cursor', None)
		except Exception:
			cursor_par = None
		if cursor_par is not None:
			for attr_name in ('expr', 'bindExpr'):
				try:
					setattr(cursor_par, attr_name, '')
				except Exception:
					pass
			try:
				comp.par.cursor = 0
				updated = True
			except Exception:
				pass
	else:
		updated = True

	return updated


def _update_button_metadata(button, owner, text_value):
	if button is None or owner is None:
		return False

	try:
		button.store('cf_owner_path', owner.path)
		button.store('family_owner_path', owner.path)
		button.store('cf_family_name', str(owner.name))
	except Exception:
		pass

	try:
		desired_name = 'button_{}'.format(owner.name)
		if str(button.name) != desired_name:
			button.name = desired_name
	except Exception:
		pass

	try:
		if hasattr(button.par, 'label'):
			for attr_name in ('expr', 'bindExpr'):
				try:
					setattr(button.par.label, attr_name, '')
				except Exception:
					pass
			button.par.label = text_value
	except Exception:
		pass

	_rebind_button_owner_pars(button, owner)

	return True


def _rename_owner_from_text(comp: textCOMP, value: str):
	button = _button_comp(comp)
	owner = _owner_from_button(button)
	if owner is None:
		return False

	new_name = str(value or '').strip()
	if not new_name:
		return False

	try:
		owner.name = new_name
	except Exception:
		return False

	_update_button_metadata(button, owner, new_name)

	try:
		if hasattr(comp.par, 'text'):
			comp.par.text = str(owner.name)
	except Exception:
		pass

	return True

def onValueChange(comp: textCOMP, value: str, prevValue: str):
	"""
	Called whenever the text component's value parameter changes for any reason
	including typing in the text window or changing the parameter directly. The
	callback is equivalent to the onValueChange in the parameter exectute DAT.
	
	Args:
		comp: the text component
		value: the new value
		prevValue: the previous value
	"""
	#debug('\nonValueChange comp:', comp.path, '- new value: ', value,
	#	  ', prev value: ', prevValue )
	return
	
def onFocus(comp: textCOMP):
	"""
	Called when one of the text components viewers gets keyboard focus. 
	
	Args:
		comp: the text component
	"""
	#debug('\nonFocus comp:', comp.path)
	return

def onFocusEnd(comp: textCOMP, info: Dict[str, str]):
	"""
	Called when one of the text component's viewers loses keyboard focus. In
	regular editing mode this is right after the contents are saved back to the
	value parameter. This function is called everytime the viewer loses focus,
	even if the text does not change.
	
	Args:
		comp: the text component
		info: a dictionary containing information about the event including:
			reason: a string indicating what caused the viewer to lose focus
				e.g. 'enter', 'escape', 'tab', 'unknown'
	
	"""
	_set_text_locked(comp)
	return
	
def onTextEdit(comp: textCOMP):
	"""
	Called each time the contents of the text component viewer change i.e. when
	typing a character, deleting text, cutting or pasting. 
	
	Args:
		comp: the text component
	"""
	#debug('\nonTextEdit comp:', comp.path, '- text: ', comp.editText)
	return
	
def onTextEditEnd(comp: textCOMP, value: str, prevValue: str):
	"""
	Called when the user finishes editing and the value has been changed. Not
	called in 'Continuous Edit' mode. Use onTextEdit and onFocusEnd when using
	continuous editing.

	Note: Any Python undo blocks created by this callback will be included in
	the undo step for the change to the text field.
	
	Args:
		comp: the text component
		value: the new value
		prevValue: the previous value
	"""
	_rename_owner_from_text(comp, value)
	_set_text_locked(comp)
	return
