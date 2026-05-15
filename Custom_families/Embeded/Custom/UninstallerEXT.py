"""
Cleanup runtime for UI nodes installed by InstallerEXT.
"""

import re


class GenericUninstallerEXT:
	INSTALLED_FAMILY_STORAGE_KEY = 'installed_family_name'

	DEFAULT_UI_PATHS = {
		'bookmark_bar': '/ui/panes/panebar/pane1/Local_bar',
		'menu_op': '/ui/dialogs/menu_op',
		'node_table': '/ui/dialogs/menu_op/nodetable',
	}

	def __init__(self, ownerComp, ui_paths=None, auto_init=False, enable_runtime_hooks=False):
		self.ownerComp = ownerComp
		self.family_name = self._get_family_name()
		self.ui_paths = dict(self.DEFAULT_UI_PATHS)
		if ui_paths:
			self.ui_paths.update(ui_paths)

	def _trace(self, message, showMessage=False):
		installer = self._get_installer_delegate()
		if installer is not None and hasattr(installer, '_trace'):
			try:
				return installer._trace(message, showMessage=showMessage)
			except Exception:
				pass
		debug(message)

	def _ui(self, key):
		path = self.ui_paths.get(key, '')
		if not path:
			return None
		try:
			return op(path)
		except Exception:
			return None

	def _get_component_ext(self):
		for attr_name in ('Component', 'ComponentEXT', 'component', 'componentExt'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None:
					return ext_obj
			except Exception:
				pass

		try:
			ext_namespace = getattr(self.ownerComp, 'ext', None)
		except Exception:
			ext_namespace = None

		if ext_namespace is not None:
			for attr_name in ('Component', 'ComponentEXT', 'component', 'componentExt'):
				try:
					ext_obj = getattr(ext_namespace, attr_name, None)
					if ext_obj is not None:
						return ext_obj
				except Exception:
					pass

		return None

	def _sanitize_family_name(self, name):
		name = '' if name is None else str(name).strip()
		if not name:
			return ''

		component_ext = self._get_component_ext()
		if component_ext is not None and hasattr(component_ext, 'SanitizePluginName'):
			try:
				return component_ext.SanitizePluginName(name)
			except Exception:
				pass

		name = name.replace(' ', '')
		name = re.sub(r'[^A-Za-z0-9_]', '', name)
		if name and name[0].isdigit():
			name = '_' + name
		return name

	def _get_family_name(self):
		try:
			opshortcut = self._sanitize_family_name(self.ownerComp.par.opshortcut.eval())
			if opshortcut:
				return opshortcut
		except Exception:
			pass

		try:
			name = self._sanitize_family_name(self.ownerComp.name)
			if name:
				return name
		except Exception:
			pass

		return ''

	def _get_installer_delegate(self):
		for attr_name in ('Installer', 'InstallerEXT', 'installer', 'installerExt', 'GenericInstallerEXT'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None and hasattr(ext_obj, '_destroy_ui_clones'):
					return ext_obj
			except Exception:
				pass

		try:
			ext_namespace = getattr(self.ownerComp, 'ext', None)
		except Exception:
			ext_namespace = None

		if ext_namespace is not None:
			for attr_name in ('Installer', 'InstallerEXT', 'installer', 'installerExt', 'GenericInstallerEXT'):
				try:
					ext_obj = getattr(ext_namespace, attr_name, None)
					if ext_obj is not None and hasattr(ext_obj, '_destroy_ui_clones'):
						return ext_obj
				except Exception:
					pass

		for dat_name in ('InstallerEXT', 'installerext'):
			try:
				dat_op = self.ownerComp.op(dat_name)
				if dat_op is None:
					continue

				module = dat_op.module
				cls = getattr(module, 'GenericInstallerEXT', None) or getattr(module, 'InstallerEXT', None)
				if cls is None:
					continue

				return cls(self.ownerComp, auto_init=False, enable_runtime_hooks=False)
			except Exception:
				pass

		return None

	def _clone_name(self, prefix, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return ''
		return '{}_{}'.format(prefix, family_name)

	def _bookmark_toggle_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		names = [
			self._clone_name('button', family_name),
			'{}_toggle'.format(family_name),
			'{}_button'.format(family_name),
		]
		if family_name != 'Custom':
			names.append(family_name)
		return names

	def _delete_execute_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		return [
			self._clone_name('delete_execute', family_name),
			'{}_delete_execute'.format(family_name),
			'Delete_op_execute',
		]

	def _watcher_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		return [
			self._clone_name('watcher', family_name),
			'{}_watcher'.format(family_name),
		]

	def _panel_execute_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		return [
			self._clone_name('panel_execute', family_name),
			'{}_panel_execute'.format(family_name),
		]

	def _inject_op_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		return [
			self._clone_name('inject', family_name) + '_fam',
			self._clone_name('inject', family_name),
			'{}_fam'.format(family_name),
		]

	def _family_insert_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		return [
			self._clone_name('insert', family_name),
			'{}_insert'.format(family_name),
		]

	def _find_child_by_names(self, parent_op, candidate_names):
		if parent_op is None:
			return None

		for name in candidate_names:
			try:
				child = parent_op.op(name)
				if child is not None:
					return child
			except Exception:
				pass

		return None

	def _safe_destroy(self, op_obj):
		if op_obj is None:
			return False

		try:
			op_obj.allowCooking = False
		except Exception:
			pass

		try:
			if getattr(op_obj, 'isCOMP', False):
				try:
					for child in list(op_obj.findChildren(depth=None)):
						try:
							child.allowCooking = False
						except Exception:
							pass
						try:
							child.destroy()
						except Exception:
							pass
				except Exception:
					pass
		except Exception:
			pass

		try:
			op_obj.destroy()
		except Exception as e:
			try:
				obj_path = op_obj.path
			except Exception:
				obj_path = str(op_obj)
			self._trace("Destroy failed for '{}': {}".format(obj_path, e), showMessage=True)
			return False

		try:
			still_valid = bool(op_obj.valid)
		except Exception:
			still_valid = False
		return not still_valid

	def _fallback_cleanup(self, family_name=None, destroy_toggle=False):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return False

		menu_op = self._ui('menu_op')
		node_table = self._ui('node_table')
		bookmark_bar = self._ui('bookmark_bar')
		removed = 0

		if bookmark_bar and destroy_toggle:
			for names in (
				self._bookmark_toggle_names(family_name),
				self._delete_execute_names(family_name),
				self._watcher_names(family_name),
			):
				target = self._find_child_by_names(bookmark_bar, names)
				if self._safe_destroy(target):
					removed += 1

		if menu_op:
			for names in (self._family_insert_names(family_name), self._panel_execute_names(family_name)):
				target = self._find_child_by_names(menu_op, names)
				if self._safe_destroy(target):
					removed += 1

		if node_table:
			target = self._find_child_by_names(node_table, self._inject_op_names(family_name))
			if self._safe_destroy(target):
				removed += 1

		self._trace(
			"Fallback cleanup for '{}': removed={} destroy_toggle={}".format(
				family_name,
				removed,
				destroy_toggle,
			),
			showMessage=True,
		)
		return removed > 0

	def _cleanup_external_delete_helpers(self, installer, family_name):
		if installer is None or not hasattr(installer, '_cleanup_external_delete_helpers'):
			return
		try:
			installer._cleanup_external_delete_helpers(family_name)
		except Exception as e:
			self._trace(
				"External delete helper cleanup failed for '{}': {}".format(family_name, e),
				showMessage=True,
			)

	def _call_installer_helper(self, installer, helper_name, *args, **kwargs):
		if installer is None:
			return None
		helper = getattr(installer, helper_name, None)
		if not callable(helper):
			return None
		try:
			return helper(*args, **kwargs)
		except Exception as e:
			self._trace(
				"Installer helper '{}' failed for '{}': {}".format(
					helper_name,
					self.family_name,
					e,
				),
				showMessage=True,
			)
			return None

	def _perform_ui_cleanup(self, installer, family_name=None, destroy_toggle=False):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return False

		self.family_name = family_name
		menu_op = self._ui('menu_op')
		node_table = self._ui('node_table')
		bookmark_bar = self._ui('bookmark_bar')
		self._trace("Cleanup start for '{}' destroy_toggle={}".format(family_name, destroy_toggle))

		toggle_op = self._find_child_by_names(
			bookmark_bar, self._bookmark_toggle_names(family_name)
		) if bookmark_bar else None
		delete_exec_op = self._find_child_by_names(
			bookmark_bar, self._delete_execute_names(family_name)
		) if bookmark_bar else None
		insert_op = self._find_child_by_names(
			menu_op, self._family_insert_names(family_name)
		) if menu_op else None

		if insert_op is None and self._sanitize_family_name(family_name) == 'Custom':
			insert_op = self._call_installer_helper(
				installer,
				'_find_custom_menu_entry',
				menu_op,
				managed_only=True,
			) if menu_op else None

		panel_execute_op = self._find_child_by_names(
			menu_op, self._panel_execute_names(family_name)
		) if menu_op else None
		inject_op = self._find_child_by_names(
			node_table, self._inject_op_names(family_name)
		) if node_table else None

		if bookmark_bar:
			if destroy_toggle:
				self._safe_destroy(toggle_op)
				self._safe_destroy(delete_exec_op)
				self._call_installer_helper(installer, '_destroy_bookmark_family_ops', family_name)
			else:
				try:
					if toggle_op is not None:
						toggle_op.allowCooking = True
				except Exception:
					pass

		if menu_op:
			self._call_installer_helper(installer, '_restore_family_insert_connection', menu_op, family_name=family_name)
			self._safe_destroy(insert_op)
			self._safe_destroy(panel_execute_op)
			self._call_installer_helper(installer, '_cleanup_custom_comp_runners', family_name)
			self._call_installer_helper(installer, '_remove_color_row', menu_op, family_name=family_name)
			self._call_installer_helper(installer, '_remove_compatible_entries', menu_op, family_name=family_name)
			self._call_installer_helper(installer, '_cleanup_eval4', node_table, family_name=family_name)
			self._call_installer_helper(installer, '_cleanup_launch_menu_op', menu_op)
			self._call_installer_helper(installer, '_cleanup_create_node', menu_op, family_name=family_name)
			self._call_installer_helper(installer, '_cleanup_native_custom_flow')
			self._call_installer_helper(installer, '_cleanup_search_exec', menu_op, family_name=family_name)
			self._call_installer_helper(installer, '_reset_menu_current_family', family_name=family_name)

		if node_table:
			self._call_installer_helper(installer, '_restore_inject_connection', node_table, family_name=family_name)
			self._safe_destroy(inject_op)
			try:
				self._safe_destroy(node_table.op('switch1'))
			except Exception:
				pass
			fam_op = node_table.op('families')
			try:
				if fam_op:
					fam_op.bypass = False
			except Exception:
				pass
			self._call_installer_helper(installer, '_refresh_external_families_bypass', node_table)

		self._call_installer_helper(installer, '_destroy_ui_family_ops', family_name, destroy_toggle=destroy_toggle)
		self._call_installer_helper(installer, '_destroy_family_residues', family_name=family_name, destroy_toggle=destroy_toggle)
		self._trace("Cleanup finished for '{}'".format(family_name))
		return True

	def _destroy_button_first(self, family_name=None):
		"""Hide then destroy every button/toggle variant for family_name.

		Called as the very first step of RemoveFamily so the button disappears
		visually BEFORE the opshortcut changes — preventing the black-flash on
		rename.  allowCooking=False is set immediately (reliable in TD); destroy()
		is attempted right after and, if it fails, a deferred run() is scheduled
		so the hidden button is cleaned up within 2 frames.
		"""
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return 0

		bookmark_bar = self._ui('bookmark_bar')
		if bookmark_bar is None:
			return 0

		try:
			owner_path = self.ownerComp.path
		except Exception:
			owner_path = ''

		hidden = 0
		removed = 0
		deferred_paths = []
		seen = set()

		def _handle(target):
			nonlocal hidden, removed
			if target is None:
				return
			try:
				path = target.path
			except Exception:
				path = None
			if path in seen:
				return
			if path:
				seen.add(path)
			# Step 1: hide immediately so the button vanishes before any state change
			try:
				target.allowCooking = False
				hidden += 1
			except Exception:
				pass
			# Step 2: try sync destroy
			if self._safe_destroy(target):
				removed += 1
			else:
				# Step 3: schedule deferred destroy for hidden-but-undestroyed button
				if path:
					deferred_paths.append(path)

		# Pass 1 — direct lookup by all known name variants
		for name in self._bookmark_toggle_names(family_name):
			try:
				target = bookmark_bar.op(name)
			except Exception:
				target = None
			_handle(target)

		# Pass 2 — full scan to catch any remnant the name lookup missed.
		# Buttons copied into Local_bar store cf_family_name; that metadata is
		# more stable than the visual/operator name during manual delete flows.
		try:
			children = bookmark_bar.findChildren(depth=None, maxDepth=2)
		except Exception:
			children = []

		for child in children:
			if child is None:
				continue
			try:
				name = child.name
			except Exception:
				continue
			try:
				stored_family = self._sanitize_family_name(child.fetch('cf_family_name', ''))
			except Exception:
				stored_family = ''
			try:
				stored_delete_family = self._sanitize_family_name(child.fetch('delete_family_name', ''))
			except Exception:
				stored_delete_family = ''
			try:
				stored_owner_path = str(child.fetch('cf_owner_path', '')).strip()
			except Exception:
				stored_owner_path = ''
			if (
				name == 'button_{}'.format(family_name)
				or name == '{}_toggle'.format(family_name)
				or name == '{}_button'.format(family_name)
				or name == family_name
				or stored_family == family_name
				or stored_delete_family == family_name
				or (owner_path and stored_owner_path == owner_path)
			):
				_handle(child)

		# Deferred destroy for anything hidden but not yet destroyed
		if deferred_paths:
			try:
				run(
					"for p in args:\n    t = op(p)\n    t.destroy() if t is not None else None",
					*deferred_paths,
					delayFrames=2,
				)
			except Exception:
				pass

		self._trace(
			'_destroy_button_first hidden={} removed={} deferred={} for "{}"'.format(
				hidden, removed, len(deferred_paths), family_name),
			showMessage=bool(hidden or removed),
		)
		return hidden + removed

	def _destroy_menu_op_first(self, family_name=None):
		"""Hide then destroy every insert_/panel_execute_ variant for family_name.

		Mirrors _destroy_button_first for /ui/dialogs/menu_op so that the old
		family's insert and panel_execute nodes cannot survive a rename even
		when _perform_ui_cleanup's by-name lookup fails (e.g. when a reference
		became stale because opshortcut was already rewritten).
		"""
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return 0

		menu_op = self._ui('menu_op')
		node_table = self._ui('node_table')
		if menu_op is None and node_table is None:
			return 0

		hidden = 0
		removed = 0
		deferred_paths = []
		seen = set()

		target_names = set(self._family_insert_names(family_name))
		target_names.update(self._panel_execute_names(family_name))
		target_names.update(self._inject_op_names(family_name))

		def _handle(target):
			nonlocal hidden, removed
			if target is None:
				return
			try:
				path = target.path
			except Exception:
				path = None
			if path in seen:
				return
			if path:
				seen.add(path)
			try:
				target.allowCooking = False
				hidden += 1
			except Exception:
				pass
			if self._safe_destroy(target):
				removed += 1
			else:
				if path:
					deferred_paths.append(path)

		roots = [r for r in (menu_op, node_table) if r is not None]

		for root in roots:
			for name in target_names:
				try:
					target = root.op(name)
				except Exception:
					target = None
				_handle(target)

		try:
			owner_id = str(self.ownerComp.id)
		except Exception:
			owner_id = ''
		try:
			owner_path = self.ownerComp.path
		except Exception:
			owner_path = ''

		residue_prefixes = ('insert_', 'panel_execute_', 'inject_')
		residue_suffixes = ('_insert', '_panel_execute', '_fam')

		for root in roots:
			try:
				children = root.findChildren(depth=None, maxDepth=2)
			except Exception:
				children = []
			for child in children:
				if child is None:
					continue
				try:
					name = child.name
				except Exception:
					continue
				if name in target_names:
					_handle(child)
					continue

				is_residue_shape = name.startswith(residue_prefixes) or name.endswith(residue_suffixes)
				if not is_residue_shape:
					continue

				try:
					child_owner_id = str(child.fetch('cf_owner_id', ''))
				except Exception:
					child_owner_id = ''
				try:
					child_owner_path = str(child.fetch('cf_owner_path', ''))
				except Exception:
					child_owner_path = ''

				owned_by_us = False
				if owner_id and child_owner_id and child_owner_id == owner_id:
					owned_by_us = True
				elif owner_path and child_owner_path and child_owner_path == owner_path:
					owned_by_us = True

				if not owned_by_us:
					continue

				try:
					managed_family = self._sanitize_family_name(
						str(child.fetch('cf_managed_family_name', ''))
					)
				except Exception:
					managed_family = ''

				if managed_family and managed_family != family_name:
					# Residue from a previous family name (pre-rename) owned by this COMP.
					continue

				_handle(child)

		if deferred_paths:
			try:
				run(
					"for p in args:\n    t = op(p)\n    t.destroy() if t is not None else None",
					*deferred_paths,
					delayFrames=2,
				)
			except Exception:
				pass

		self._trace(
			'_destroy_menu_op_first hidden={} removed={} deferred={} for "{}"'.format(
				hidden, removed, len(deferred_paths), family_name),
			showMessage=bool(hidden or removed),
		)
		return hidden + removed

	def RemoveInstalledUi(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self._get_family_name())
		if not family_name:
			return False

		self.family_name = family_name
		installer = self._get_installer_delegate()

		if installer is not None and hasattr(installer, '_destroy_ui_clones'):
			try:
				installer.family_name = family_name
			except Exception:
				pass
			try:
				self._perform_ui_cleanup(installer, family_name=family_name, destroy_toggle=False)
				self._destroy_menu_op_first(family_name)
				self._cleanup_external_delete_helpers(installer, family_name)
				self._trace("RemoveInstalledUi completed for '{}'".format(family_name), showMessage=True)
				return True
			except Exception as e:
				self._trace("RemoveInstalledUi delegate failed for '{}': {}".format(family_name, e), showMessage=True)

		return self._fallback_cleanup(family_name=family_name, destroy_toggle=False)

	def RemoveFamily(self, family_name=None, preserve_button=False):
		family_name = self._sanitize_family_name(family_name or self._get_family_name())
		if not family_name:
			return False

		# Destroy the button before anything else so rename can never leave a
		# stale button behind if the deeper cleanup fails to find it by name.
		# preserve_button=True is set by RenameEXT so the bookmark toggle stays
		# alive across the rename and _install_toggle can rename it in-place
		# (avoiding the disappear/reappear flicker the user sees on the bookmark).
		if not preserve_button:
			self._destroy_button_first(family_name)

		self.family_name = family_name
		installer = self._get_installer_delegate()

		if installer is not None and hasattr(installer, '_destroy_ui_clones'):
			try:
				installer.family_name = family_name
			except Exception:
				pass
			try:
				self._perform_ui_cleanup(installer, family_name=family_name, destroy_toggle=not preserve_button)
				self._destroy_menu_op_first(family_name)
				self._cleanup_external_delete_helpers(installer, family_name)
				try:
					if hasattr(installer, '_set_recorded_installed_family'):
						installer._set_recorded_installed_family('')
				except Exception:
					pass
				try:
					if hasattr(self.ownerComp, 'store'):
						self.ownerComp.store(self.INSTALLED_FAMILY_STORAGE_KEY, '')
				except Exception:
					pass
				try:
					self.ownerComp.par.Install = 0
				except Exception:
					pass
				self._trace("RemoveFamily completed for '{}'".format(family_name), showMessage=True)
				return True
			except Exception as e:
				self._trace("RemoveFamily delegate failed for '{}': {}".format(family_name, e), showMessage=True)

		result = self._fallback_cleanup(family_name=family_name, destroy_toggle=not preserve_button)
		self._destroy_menu_op_first(family_name)
		try:
			if hasattr(self.ownerComp, 'store'):
				self.ownerComp.store(self.INSTALLED_FAMILY_STORAGE_KEY, '')
		except Exception:
			pass
		try:
			self.ownerComp.par.Install = 0
		except Exception:
			pass
		return result

	def DeleteCleanup(self, family_name=None):
		return self.RemoveFamily(family_name=family_name)

	def Uninstall(self, family_name=None):
		return self.RemoveFamily(family_name=family_name)


UninstallerEXT = GenericUninstallerEXT
