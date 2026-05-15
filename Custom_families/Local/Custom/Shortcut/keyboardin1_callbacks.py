"""
Keyboard In DAT Callbacks

me - This DAT

keyInfo - A namedtuple containing the following members:
	key - The name of the key attached to the event. This tries to be 
		consistent regardless of which language the keyboard is set to. 
		The values will be the english/ASCII values that most closely 
		match the key pressed. This is what should be used for shortcuts 
		instead of 'character'.
	webCode - The name of the key following web-programming standards.
	character - The unicode character generated.
	alt - True if the alt modifier is pressed
	lAlt - True if the left-alt modifier is pressed
	rAlt - True if the right-alt modifier is pressed
	ctrl - True if the ctrl modifier is pressed
	lCtrl - True if the left-ctrl modifier is pressed
	rCtrl - True if the right-ctrl modifier is pressed
	shift - True if the shift modifier is pressed
	lShift - True if the left-shift modifier is pressed
	rShift - True if the right-shift modifier is pressed
	state - True if the event is a key press event
	time - The time when the event came in milliseconds
	cmd - True if the cmd modifier is pressed
	lCmd - True if the left-cmd modifier is pressed
	rCmd - True if the right-cmd modifier is pressed
"""

FUNCTION_TO_PULSE = {
	'rename': 'Rename',
	'duplicate': 'Duplicate',
	'edit operators': 'Editoperators',
	'change color': 'Changecolor',
	'manual update': 'Manualupdate',
	'export family': 'Exportfamily',
	'delete': 'Delete',
}

MODIFIER_KEYS = {
	'ctrl', 'lctrl', 'rctrl',
	'alt', 'lalt', 'ralt',
	'shift', 'lshift', 'rshift',
	'cmd', 'lcmd', 'rcmd',
}


def _family_comp(dat):
	try:
		return dat.parent(2)
	except Exception:
		return None


def _menu_comp(dat):
	family = _family_comp(dat)
	if family is None:
		return None
	for name in ('Menu', 'menu'):
		try:
			menu = family.op(name)
			if menu is not None:
				return menu
		except Exception:
			pass
	return None


def _is_selected(dat):
	family = _family_comp(dat)
	if family is None or not hasattr(family, 'par') or not hasattr(family.par, 'Selected'):
		return False
	try:
		return bool(family.par.Selected.eval())
	except Exception:
		return False


def _shortcut_table(dat):
	try:
		container = dat.parent()
	except Exception:
		container = None
	if container is None:
		return None
	for name in ('null1', 'merge1', 'table2', 'table1'):
		try:
			table = container.op(name)
			if table is not None:
				return table
		except Exception:
			pass
	return None


def _normalize_shortcut(value):
	text = str(value or '').strip().lower()
	if not text:
		return ''
	text = text.replace('control', 'ctrl')
	text = text.replace('back space', 'canc')
	text = text.replace('backspace', 'canc')
	text = text.replace('delete', 'canc')
	text = text.replace('del', 'canc')
	parts = [part.strip() for part in text.split('+') if part.strip()]
	normalized = []
	for part in parts:
		if part in ('left ctrl', 'right ctrl'):
			part = 'ctrl'
		elif part in ('left shift', 'right shift'):
			part = 'shift'
		elif part in ('left alt', 'right alt'):
			part = 'alt'
		elif part in ('escape',):
			part = 'esc'
		elif part in ('delete', 'del', 'backspace'):
			part = 'canc'
		if part not in normalized:
			normalized.append(part)
	return ' + '.join(normalized)


def _event_shortcut(keyInfo):
	try:
		key_name = str(keyInfo.key or '').strip().lower()
	except Exception:
		key_name = ''
	if not key_name or key_name in MODIFIER_KEYS:
		return ''

	key_name = _normalize_shortcut(key_name)
	modifiers = []
	for active, name in (
		(getattr(keyInfo, 'ctrl', False), 'ctrl'),
		(getattr(keyInfo, 'alt', False), 'alt'),
		(getattr(keyInfo, 'shift', False), 'shift'),
		(getattr(keyInfo, 'cmd', False), 'cmd'),
	):
		if active and name not in modifiers:
			modifiers.append(name)

	if key_name and key_name not in modifiers:
		modifiers.append(key_name)
	return ' + '.join(modifiers)


def _find_function_name(dat, shortcut_text):
	table = _shortcut_table(dat)
	if table is None or not shortcut_text:
		return ''

	target = _normalize_shortcut(shortcut_text)
	try:
		num_rows = int(table.numRows)
	except Exception:
		num_rows = 0

	for row in range(1, num_rows):
		try:
			row_shortcut = _normalize_shortcut(table[row, 0].val)
			row_function = str(table[row, 1].val).strip()
		except Exception:
			continue
		if row_shortcut == target and row_function:
			return row_function
	return ''


def _pulse_menu_action(dat, function_name):
	menu = _menu_comp(dat)
	if menu is None:
		return

	par_name = FUNCTION_TO_PULSE.get(str(function_name or '').strip().lower(), '')
	if not par_name:
		return

	try:
		par = getattr(menu.par, par_name, None)
	except Exception:
		par = None
	if par is None:
		return

	try:
		par.pulse()
	except Exception:
		pass


def onKey(dat: keyboardinDAT, keyInfo: KeyboardInDATInfo):
	"""
	Called when a key event occurs.
	
	Args:
		dat: The DAT that received the key event
		keyInfo: KeyboardInDATInfo namedtuple with key event details
	"""
	try:
		if not bool(keyInfo.state):
			return
	except Exception:
		return

	if not _is_selected(dat):
		return

	function_name = _find_function_name(dat, _event_shortcut(keyInfo))
	if not function_name:
		return

	_pulse_menu_action(dat, function_name)
	return

def onShortcut(dat: keyboardinDAT, shortcutName: str, time: int):
	"""
	Called when a shortcut is triggered.
	
	Args:
		dat: The DAT that received the shortcut event
		shortcutName: The name of the shortcut
		time: The time when the event occurred in milliseconds
	"""
	if not _is_selected(dat):
		return

	function_name = _find_function_name(dat, shortcutName)
	if not function_name:
		function_name = str(shortcutName or '').strip()
	_pulse_menu_action(dat, function_name)
	return
