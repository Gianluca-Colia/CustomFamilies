"""
Createfamily — extension on /ui/Plugins/Custom_families/Create_family.

Clones the canonical family template (Embeded/Custom) into the Local
container and wakes the copy up so its own install chain starts. The
source family in Embeded is kept cooking-disabled so it never triggers
itself; the copy in Local is the live instance the user works with.

Triggered by a pulse on the Custom_families root COMP's `Createfamily`
par: the par is exported via par1 (Parameter CHOP) → chopexec1.onOffToOn
calls `parent().ext.Createfamily.Create()`.
"""

EMBEDED_CUSTOM_PATH = '/ui/Plugins/Custom_families/Embeded/Custom'
LOCAL_PATH = '/ui/Plugins/Custom_families/Local'


class Createfamily:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp

	def Create(self):
		"""Copy Embeded/Custom into Local, set opshortcut, force-cook.

		Returns the freshly created COMP, or None on failure.
		"""
		source = op(EMBEDED_CUSTOM_PATH)
		if source is None:
			debug('[Createfamily] source missing: {}'.format(EMBEDED_CUSTOM_PATH))
			return None

		local = op(LOCAL_PATH)
		if local is None:
			debug('[Createfamily] Local container missing: {}'.format(LOCAL_PATH))
			return None

		try:
			copy = local.copy(source)
		except Exception as exc:
			debug('[Createfamily] copy failed: {}'.format(exc))
			return None

		if copy is None:
			return None

		# Order matters. The family's auto-install (Auto_install_execute)
		# fires as soon as the COMP starts cooking and reads par.opshortcut
		# to determine its own family_name. Set opshortcut FIRST while the
		# copy is still cooking-disabled, then wake it up.
		try:
			if hasattr(copy.par, 'opshortcut'):
				copy.par.opshortcut = copy.name
		except Exception:
			pass

		# Wake the copy: the source in Embeded is cooking-disabled, so the
		# copy inherits allowCooking=False and would never start its install
		# chain otherwise.
		try:
			copy.allowCooking = True
		except Exception:
			pass

		# Force-cook so Auto_install_execute / onCreate inside the family
		# fires now instead of waiting for an unrelated dependency.
		try:
			copy.cook(force=True)
		except Exception:
			pass

		return copy
