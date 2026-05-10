CANCEL_KEYS = {'esc', 'escape'}

def _component_ext(dat):
	try:
		comp = dat.parent(2)
	except Exception:
		return None
	try:
		return getattr(comp, 'ComponentEXT', None) or getattr(getattr(comp, 'ext', None), 'ComponentEXT', None)
	except Exception:
		return None

def _clear_keyboard(dat):
	if dat is None:
		return False
	try:
		dat.par.clear.pulse()
		return True
	except Exception:
		return False

def onKey(dat, key, character, alt, lAlt, rAlt, ctrl, lCtrl, rCtrl, shift, lShift, rShift, state, time):
	if not state:
		return
	try:
		key_name = str(key).strip().lower()
	except Exception:
		return
	if key_name not in CANCEL_KEYS:
		return

	ext_obj = _component_ext(dat)
	if ext_obj is not None:
		try:
			ext_obj.CancelPendingPlacement(True)
		except Exception:
			pass
	_clear_keyboard(dat)

def reset_keyboard(dat):
	return _clear_keyboard(dat)
