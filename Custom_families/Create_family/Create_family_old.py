"""
Create_family — duplicates the Embeded/Custom template into the Local
container and wakes it up so its own install chain starts.

The source family lives at /ui/Plugins/Custom_families/Embeded/Custom and
is kept cooking-disabled so it never triggers itself. The copy in Local
is the live instance the user actually works with.
"""

EMBEDED_CUSTOM_PATH = '/ui/Plugins/Custom_families/Embeded/Custom'
LOCAL_PATH = '/ui/Plugins/Custom_families/Local'


def Create_family():
	"""Copy Embeded/Custom into Local, set opshortcut, force-cook.

	Returns the freshly created COMP, or None on failure.
	"""
	source = op(EMBEDED_CUSTOM_PATH)
	if source is None:
		debug('[Create_family] source missing: {}'.format(EMBEDED_CUSTOM_PATH))
		return None

	local = op(LOCAL_PATH)
	if local is None:
		debug('[Create_family] Local container missing: {}'.format(LOCAL_PATH))
		return None

	try:
		copy = local.copy(source)
	except Exception as exc:
		debug('[Create_family] copy failed: {}'.format(exc))
		return None

	if copy is None:
		return None

	# Order matters here. The family's auto-install (Auto_install_execute)
	# fires as soon as the COMP starts cooking and reads par.opshortcut to
	# determine its own family_name. If we enable cooking before fixing
	# opshortcut, the install runs with the inherited 'Custom' name, wiring
	# all internal references (Internal_reference.par.Globalshortcut, color
	# CHOPs, parexec listeners) to op.Custom — so Custom1 ends up sharing
	# state with the original Custom (color changes link, color picker on
	# Custom1 silently writes nowhere). Fix opshortcut FIRST while still
	# cooking-disabled, then wake the family up.
	try:
		if hasattr(copy.par, 'opshortcut'):
			copy.par.opshortcut = copy.name
	except Exception:
		pass

	# Now wake the copy: source in Embeded is held cooking-disabled, so the
	# copy inherits allowCooking=False and would never start its install
	# chain otherwise.
	try:
		copy.allowCooking = True
	except Exception:
		pass

	# Force-cook so the Auto_install_execute / onCreate inside the family
	# fires now instead of waiting for an unrelated dependency to wake it.
	try:
		copy.cook(force=True)
	except Exception:
		pass

	return copy
