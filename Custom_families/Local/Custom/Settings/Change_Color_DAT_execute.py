"""
DAT Execute bridge minimale per UpdateChildrenColor.
"""

def _get_target():
	shortcut = None
	try:
		shortcut = str(iop.Internal_reference.par.Globalshortcut.eval()).strip() or None
	except Exception:
		pass

	if shortcut:
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

	# Fallback: this DAT lives in Settings/ inside the family COMP → parent(2)
	try:
		candidate = parent(2)
		if candidate is not None:
			return candidate
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

	if component_ext is None or not hasattr(component_ext, 'UpdateChildrenColor'):
		return

	try:
		if hasattr(component_ext, 'SyncInstalledColor'):
			component_ext.SyncInstalledColor()
		else:
			component_ext.UpdateChildrenColor()
	except Exception:
		return


def _sync_color_from_target():
	target = _get_target()
	if target is None:
		return

	try:
		component_ext = getattr(getattr(target, 'ext', None), 'ComponentEXT', None)
		if component_ext is None:
			component_ext = getattr(target, 'ComponentEXT', None)
	except Exception:
		component_ext = None

	if component_ext is None:
		return

	try:
		if hasattr(component_ext, 'SyncInstalledColor'):
			component_ext.SyncInstalledColor()
		elif hasattr(component_ext, 'UpdateChildrenColor'):
			component_ext.UpdateChildrenColor()
	except Exception:
		return


def onValueChange(par, prev):
	try:
		par_name = str(getattr(par, 'name', '') or '')
	except Exception:
		par_name = ''

	if par_name in ('Colorr', 'Colorg', 'Colorb', 'Color'):
		_sync_color_from_target()
	return


def onValuesChanged(changes):
	for change in changes or []:
		try:
			par = getattr(change, 'par', None)
		except Exception:
			par = None
		if par is None:
			continue
		try:
			par_name = str(getattr(par, 'name', '') or '')
		except Exception:
			par_name = ''
		if par_name in ('Colorr', 'Colorg', 'Colorb', 'Color'):
			_sync_color_from_target()
			break
	return
