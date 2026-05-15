"""
DAT Execute bridge minimale per UpdateAll.
"""

def _get_target():
	try:
		shortcut = str(iop.Internal_reference.par.Globalshortcut.eval()).strip()
	except Exception:
		return None

	if not shortcut:
		return None

	try:
		target = getattr(op, shortcut, None)
		if target is not None:
			return target
	except Exception:
		pass

	for candidate in (shortcut, '/{}'.format(shortcut)):
		try:
			target = op(candidate)
			if target is not None:
				return target
		except Exception:
			pass

	for depth in (2, 1):
		try:
			target = parent(depth)
			if target is not None:
				return target
		except Exception:
			pass

	return None

def onTableChange(dat, prevDAT, info):
	target = _get_target()
	if target is None:
		return

	try:
		component_ext = getattr(getattr(target, 'ext', None), 'ComponentEXT', None)
		if component_ext is None:
			component_ext = getattr(target, 'ComponentEXT', None)
	except Exception:
		component_ext = None

	if component_ext is None or not hasattr(component_ext, 'UpdateAll'):
		return

	try:
		component_ext.UpdateAll(showMessage=False)
	except Exception:
		return
