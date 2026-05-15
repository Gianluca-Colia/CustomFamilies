"""
Createfamily extension — spawns a new family inside the Local container.

Triggered by chopexec1.py when the user pulses the `Createfamily` par
on the Custom_families root. If a family in Local has par.Selected = 1,
clones that one (so the new family continues its naming series — e.g.
'STV' -> 'STV1' -> 'STV2'). Otherwise falls back to the canonical
Embeded/Custom template, producing 'Custom', 'Custom1', ...

In both cases the new COMP gets a unique name in Local (base + lowest
free integer suffix, starting at 1), par.opshortcut is synced to that
name, and cooking is enabled.
"""

import re


class Createfamily:
	def __init__(self, ownerComp):
		self.ownerComp = ownerComp

	def Create(self):
		root = self.ownerComp.parent()
		if root is None:
			debug('[Createfamily] root parent missing')
			return None

		local = root.op('Local')
		if local is None:
			debug('[Createfamily] Local container missing')
			return None

		source = self._pick_source(root, local)
		if source is None:
			debug('[Createfamily] no source available (no Selected family, Embeded/Custom missing)')
			return None

		try:
			new_comp = local.copy(source)
		except Exception as exc:
			debug('[Createfamily] copy failed: {}'.format(exc))
			return None

		# Force a name that continues the source's naming series, regardless of
		# what TD's auto-namer picked (it only avoids collisions, it doesn't
		# preserve a monotonic counter — so after a rename frees 'STV', a
		# subsequent copy of 'STV' would otherwise land back on 'STV' instead
		# of 'STV1').
		try:
			new_comp.name = self._next_unique_name(local, source.name, exclude=new_comp)
		except Exception as exc:
			debug('[Createfamily] rename to unique name failed: {}'.format(exc))

		# Keep opshortcut aligned with the final COMP name so each family in
		# Local resolves to a unique global op.
		try:
			if hasattr(new_comp.par, 'opshortcut'):
				new_comp.par.opshortcut = new_comp.name
		except Exception as exc:
			debug('[Createfamily] opshortcut sync failed: {}'.format(exc))

		# Template/source may have cooking disabled; enable it on the clone so
		# the new family starts running its install/setup logic.
		try:
			new_comp.allowCooking = True
		except Exception as exc:
			debug('[Createfamily] enable cooking failed: {}'.format(exc))

		return new_comp

	def _pick_source(self, root, local):
		"""Pick the COMP to duplicate.

		Preferred: a child of Local whose par.Selected evaluates truthy.
		Fallback: the canonical Embeded/Custom template embedded in the plugin.
		"""
		try:
			for child in getattr(local, 'children', []):
				try:
					if not getattr(child, 'isCOMP', False):
						continue
				except Exception:
					continue
				try:
					if not hasattr(child.par, 'Selected'):
						continue
					if bool(child.par.Selected.eval()):
						return child
				except Exception:
					continue
		except Exception:
			pass

		return root.op('Embeded/Custom')

	def _next_unique_name(self, local, base_name, exclude=None):
		"""Return base_name + smallest integer N>=1 such that '<base><N>' is
		free among local's children. The bare base_name is reserved for the
		original family — duplicates always carry a numeric suffix.

		If base_name already ends with digits we strip them so 'STV1' -> 'STV2',
		not 'STV12'.
		"""
		match = re.match(r'^(.*?)(\d+)$', str(base_name or ''))
		root = match.group(1) if match else str(base_name or '')
		if not root:
			root = 'Custom'

		existing = set()
		try:
			for child in getattr(local, 'children', []):
				if child is exclude:
					continue
				try:
					existing.add(str(child.name))
				except Exception:
					pass
		except Exception:
			pass

		n = 1
		while '{}{}'.format(root, n) in existing:
			n += 1
		return '{}{}'.format(root, n)
