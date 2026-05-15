# panelValue - the PanelValue object that changed
# Make sure the corresponding toggle is enabled in the Panel Execute DAT.

def _in_rename_mode():
	# Primary: explicit flag stored by chopexec_Rename when entering rename mode
	try:
		if bool(parent().fetch('cf_rename_mode', False)):
			return True
	except Exception:
		pass
	# Fallback: custom integer Cursor parameter == 2 (Text Select)
	try:
		cursor_par = getattr(parent().par, 'Cursor', None) or getattr(parent().par, 'cursor', None)
		if cursor_par is not None:
			return int(cursor_par.val) == 2
	except Exception:
		pass
	return False


def onValueChange(panelValue):
	if _in_rename_mode():
		return
	family_name = parent().name[len('button_'):]
	try:
		getattr(op, family_name).par.Selected = panelValue
	except Exception:
		pass
	return
