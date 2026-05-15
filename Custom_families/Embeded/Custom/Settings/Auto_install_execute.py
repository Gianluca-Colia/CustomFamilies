"""
Execute DAT — Auto Install
Fires onCreate / onStart when the DAT is active.
The DAT's active parameter should be bound to the family comp's Autoinstall par.

Calls InstallerEXT through HandleInstallValue so imported families are
first routed into Custom_families/Local when that host exists.
"""


def _get_family_comp():
	"""Return the family component (grandparent of the Settings folder)."""
	try:
		return parent(2)
	except Exception:
		return None


def _autoinstall_enabled(comp):
	"""Return True if Autoinstall is either not present or explicitly True."""
	try:
		return bool(comp.par.Autoinstall.eval())
	except Exception:
		# Parameter doesn't exist — let the DAT's own active binding decide
		return True


def _call_install():
	comp = _get_family_comp()
	if comp is None:
		debug("Auto_install_execute: family comp not found")
		return False

	if not _autoinstall_enabled(comp):
		return False

	try:
		if bool(comp.fetch('cf_reinstall_in_progress', 0)):
			debug("Auto_install_execute: skipping — rename/reinstall in progress for '{}'".format(comp.path))
			return False
	except Exception:
		pass

	try:
		dat = comp.op('InstallerEXT')
		if dat is None:
			debug("Auto_install_execute: InstallerEXT DAT not found in '{}'".format(comp.path))
			return False

		cls = getattr(dat.module, 'InstallerEXT', None)
		if cls is None:
			debug("Auto_install_execute: InstallerEXT class not found in module")
			return False

		cls(comp, auto_init=False, enable_runtime_hooks=False).HandleInstallValue(
			1,
			source_label='Auto.installExecute'
		)
		return True

	except Exception as e:
		debug("Auto_install_execute error: {}".format(e))
		return False


def onCreate():
	return _call_install()


def onStart():
	return _call_install()
