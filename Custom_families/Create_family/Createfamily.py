"""
Createfamily extension — spawns a new family inside the Local container.

Triggered by chopexec1.py when the user pulses the `Createfamily` par
on the Custom_families root. Clones the Embeded/Custom template COMP
into the sibling Local container so the user gets a fresh, independent
family to edit.
"""


class Createfamily:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp

	def Create(self):
		root = self.ownerComp.parent()
		if root is None:
			debug('[Createfamily] root parent missing')
			return None

		template = root.op('Embeded/Custom')
		if template is None:
			debug('[Createfamily] Embeded/Custom template missing')
			return None

		local = root.op('Local')
		if local is None:
			debug('[Createfamily] Local container missing')
			return None

		try:
			new_comp = local.copy(template)
		except Exception as exc:
			debug('[Createfamily] copy failed: {}'.format(exc))
			return None

		# Align opshortcut with the (possibly auto-incremented) name TD just
		# assigned, so each family in Local resolves to a unique global op.
		try:
			if hasattr(new_comp.par, 'opshortcut'):
				new_comp.par.opshortcut = new_comp.name
		except Exception as exc:
			debug('[Createfamily] opshortcut sync failed: {}'.format(exc))

		# Template ships with cooking disabled; enable it on the clone so the
		# new family starts running its install/setup logic.
		try:
			new_comp.allowCooking = True
		except Exception as exc:
			debug('[Createfamily] enable cooking failed: {}'.format(exc))

		return new_comp
