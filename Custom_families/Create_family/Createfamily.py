"""
Createfamily extension — spawns a new family inside the Local or Server container.

Triggered by chopexec1.py when the user pulses the `Createfamily` par
on the Custom_families root.

Source resolution:
  1. If any family in Local has par.Selected = 1 → duplicate that one into Local
  2. Else if any family in Server has par.Selected = 1 → duplicate that one into Server
  3. Else (no selection) → fall back to Embeded/Custom template, place into Local

Naming: the new COMP gets the first free name in the series '<root>',
'<root>1', '<root>2', ... where <root> is the source name with any
trailing digits stripped. So 'STV' -> 'STV1' on first duplicate, then
'STV2', etc. Bare base name is reserved for the original family.

Post-copy cleanup: storage keys that track install/import state on the
source are reset on the duplicate so the new family starts with a
clean slate instead of inheriting the source's installed-name cache
(which would otherwise revert the duplicate's name during install).
"""

import re


# Storage keys persisted on a family COMP that must NOT be carried over
# to a freshly-duplicated copy — they would otherwise make the install
# pipeline think the duplicate is the source (revert the rename, reuse
# the source's bookmark, etc.).
INHERITED_STORAGE_KEYS = (
	'installed_family_name',
	'cf_install_complete',
	'cf_hosted_import_pending',
	'cf_hosted_import_family',
	'cf_hosted_source_delegated',
	'cf_external_tox_import',
	'cf_external_tox_source',
	'cf_reinstall_in_progress',
	'cf_rename_mode',
	'cf_owner_path',
	'cf_family_name',
	'cf_owner_id',
	'cf_hosted_import_copy',
)


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

		# server is optional: a project without Server still creates fine into Local
		server = root.op('Server')

		source, target = self._pick_source_and_target(root, local, server)
		if source is None or target is None:
			debug('[Createfamily] no source/target available (no Selected family in Local or Server, Embeded/Custom missing)')
			return None

		try:
			new_comp = target.copy(source)
		except Exception as exc:
			debug('[Createfamily] copy failed: {}'.format(exc))
			return None

		# Clear stale stored state inherited from the source so install can't
		# revert the duplicate to the source's identity.
		self._clear_inherited_storage(new_comp)

		# Force a name that continues the source's naming series, regardless of
		# what TD's auto-namer picked (it only avoids collisions, it doesn't
		# preserve a monotonic counter — so after a rename frees 'STV', a
		# subsequent copy of 'STV' would otherwise land back on 'STV' instead
		# of 'STV1').
		try:
			new_comp.name = self._next_unique_name(target, source.name, exclude=new_comp)
		except Exception as exc:
			debug('[Createfamily] rename to unique name failed: {}'.format(exc))

		# Keep opshortcut aligned with the final COMP name so each family in
		# Local/Server resolves to a unique global op.
		try:
			if hasattr(new_comp.par, 'opshortcut'):
				new_comp.par.opshortcut.expr = ''
				new_comp.par.opshortcut.bindExpr = ''
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

	def _pick_source_and_target(self, root, local, server):
		"""Return (source_comp, target_container).

		Priority:
		  1. Selected family in Local → (selected, local)
		  2. Selected family in Server → (selected, server)
		  3. Embeded/Custom template → (template, local)
		"""
		selected_local = self._find_selected_child(local)
		if selected_local is not None:
			return selected_local, local

		selected_server = self._find_selected_child(server)
		if selected_server is not None:
			return selected_server, server

		template = root.op('Embeded/Custom')
		if template is None:
			return None, None
		return template, local

	def _find_selected_child(self, container):
		if container is None:
			return None
		try:
			for child in getattr(container, 'children', []):
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
		return None

	def _clear_inherited_storage(self, new_comp):
		"""Reset storage keys that would otherwise make the install pipeline
		treat the duplicate as the source (and revert any rename).
		"""
		if new_comp is None:
			return
		# par.Selected: the source may have Selected=1 (that's how we picked
		# it); the copy inherits that. Clear it so the duplicate is not
		# considered the next-selected source.
		try:
			if hasattr(new_comp.par, 'Selected'):
				new_comp.par.Selected = 0
		except Exception:
			pass

		for key in INHERITED_STORAGE_KEYS:
			# Two-pass: unstore (removes the key entirely if possible) +
			# overwrite with empty/false fallback. TD's unstore signature
			# varies across versions, so we try both ways and swallow errors.
			try:
				if hasattr(new_comp, 'unstore'):
					new_comp.unstore(key)
			except Exception:
				pass
			try:
				new_comp.store(key, '')
			except Exception:
				pass

	def _next_unique_name(self, container, base_name, exclude=None):
		"""Return the first free name among '<root>', '<root>1', '<root>2', ...
		in container's children. <root> is base_name with any trailing digits
		stripped, so 'STV1' -> 'STV' and the search continues from 'STV1'
		onward (never 'STV12').

		The bare <root> is used when free — so a fresh install with empty
		Local yields 'Custom' (not 'Custom1'). Duplicates only get a numeric
		suffix when the bare name is already taken.
		"""
		match = re.match(r'^(.*?)(\d+)$', str(base_name or ''))
		root = match.group(1) if match else str(base_name or '')
		if not root:
			root = 'Custom'

		existing = set()
		try:
			for child in getattr(container, 'children', []):
				if child is exclude:
					continue
				try:
					existing.add(str(child.name))
				except Exception:
					pass
		except Exception:
			pass

		if root not in existing:
			return root

		n = 1
		while '{}{}'.format(root, n) in existing:
			n += 1
		return '{}{}'.format(root, n)
