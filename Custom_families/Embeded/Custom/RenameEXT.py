"""
Rename runtime for family identity changes.
"""

import re


class GenericRenameEXT:

	def __init__(self, ownerComp, auto_init=False, enable_runtime_hooks=False):
		self.ownerComp = ownerComp

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

	def _trace(self, message):
		component_ext = self._get_component_ext()
		if component_ext is not None:
			try:
				debug('[RenameEXT] {}'.format(message))
				return
			except Exception:
				pass
		debug('[RenameEXT] {}'.format(message))

	def _has_sibling_family_owner(self, family_name):
		"""Return True if another COMP (sibling of ownerComp) already owns family_name.

		This guards against removing the original family's UI when a copy is
		renamed from 'Custom' to 'Custom1' — the original 'Custom' COMP is a
		sibling and must not be disturbed.
		"""
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return False
		try:
			parent_comp = self.ownerComp.parent()
			if parent_comp is None:
				return False
		except Exception:
			return False

		# Check for a sibling named exactly family_name
		try:
			sibling = parent_comp.op(family_name)
			if sibling is not None and sibling != self.ownerComp:
				return True
		except Exception:
			pass

		# Check for a sibling whose opshortcut equals family_name
		try:
			for child in parent_comp.children:
				if child == self.ownerComp:
					continue
				try:
					shortcut = self._sanitize_family_name(child.par.opshortcut.eval())
					if shortcut == family_name:
						return True
				except Exception:
					pass
		except Exception:
			pass

		return False

	def _safe_destroy(self, op_obj):
		if op_obj is None:
			return False
		try:
			op_obj.destroy()
			return True
		except Exception as e:
			try:
				obj_path = op_obj.path
			except Exception:
				obj_path = str(op_obj)
			self._trace("Direct destroy failed for '{}': {}".format(obj_path, e))
			return False

	def _force_cleanup_menu_op_family(self, family_name, uninstaller=None):
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return 0

		if uninstaller is None:
			uninstaller = self._get_uninstaller_delegate()
		if uninstaller is not None and hasattr(uninstaller, '_destroy_menu_op_first'):
			try:
				return uninstaller._destroy_menu_op_first(family_name) or 0
			except Exception as e:
				self._trace("_destroy_menu_op_first failed for '{}': {}".format(family_name, e))

		try:
			menu_op = op('/ui/dialogs/menu_op')
		except Exception:
			menu_op = None
		if menu_op is None:
			return 0

		candidate_names = [
			'insert_{}'.format(family_name),
			'{}_insert'.format(family_name),
			'panel_execute_{}'.format(family_name),
			'{}_panel_execute'.format(family_name),
		]
		removed = 0
		for name in candidate_names:
			try:
				target = menu_op.op(name)
			except Exception:
				target = None
			if self._safe_destroy(target):
				removed += 1

		if removed:
			self._trace("Direct menu_op cleanup removed={} for '{}'".format(removed, family_name))
		return removed

	def _rename_bookmark_toggle_in_place(self, old_name, new_name):
		"""Rename the live bookmark toggle from button_<old> to button_<new>
		and refresh its stored owner metadata. Paired with preserve_button=True
		in RemoveFamily/_force_cleanup_bookmark_family so _install_toggle later
		reuses the same physical toggle instead of copying a fresh one.
		"""
		old_name = self._sanitize_family_name(old_name)
		new_name = self._sanitize_family_name(new_name)
		if not old_name or not new_name or old_name == new_name:
			return False

		try:
			bookmark_bar = op('/ui/panes/panebar/pane1/Local_bar')
		except Exception:
			bookmark_bar = None
		if bookmark_bar is None:
			return False

		target_name = 'button_{}'.format(new_name)
		toggle = None
		for variant in (
			'button_{}'.format(old_name),
			'{}_toggle'.format(old_name),
			'{}_button'.format(old_name),
		):
			try:
				candidate = bookmark_bar.op(variant)
			except Exception:
				candidate = None
			if candidate is not None:
				toggle = candidate
				break

		if toggle is None:
			return False

		try:
			if toggle.name != target_name:
				toggle.name = target_name
		except Exception as e:
			self._trace("Toggle in-place rename failed '{}'->'{}': {}".format(
				old_name, new_name, e))
			return False

		try:
			toggle.store('cf_family_name', new_name)
		except Exception:
			pass
		try:
			toggle.store('cf_owner_path', self.ownerComp.path)
		except Exception:
			pass
		try:
			toggle.store('family_owner_path', self.ownerComp.path)
		except Exception:
			pass

		self._trace("Renamed bookmark toggle in-place to '{}'".format(target_name))
		return True

	def _force_cleanup_bookmark_family(self, family_name, preserve_button=False):
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return 0

		try:
			bookmark_bar = op('/ui/panes/panebar/pane1/Local_bar')
		except Exception:
			bookmark_bar = None

		if bookmark_bar is None:
			return 0

		# When preserve_button=True (rename path), the visible bookmark toggle
		# is intentionally left alive so _install_toggle can rename it in-place
		# under the new family name. We still clean the side artifacts (watcher,
		# delete_execute) tied to the old name.
		button_variants = (
			'button_{}'.format(family_name),
			'{}_button'.format(family_name),
			'{}_toggle'.format(family_name),
		)
		other_variants = (
			'watcher_{}'.format(family_name),
			'{}_watcher'.format(family_name),
			'delete_execute_{}'.format(family_name),
			'{}_delete_execute'.format(family_name),
		)
		candidate_names = list(other_variants)
		if not preserve_button:
			candidate_names = list(button_variants) + candidate_names

		removed = 0
		for name in candidate_names:
			try:
				target = bookmark_bar.op(name)
			except Exception:
				target = None
			if self._safe_destroy(target):
				removed += 1

		if removed:
			self._trace("Direct bookmark cleanup removed={} for '{}'".format(removed, family_name))
		return removed

	def _get_family_name(self):
		component_ext = self._get_component_ext()
		if component_ext is not None and hasattr(component_ext, 'GetFamilyName'):
			try:
				family_name = self._sanitize_family_name(component_ext.GetFamilyName())
				if family_name:
					return family_name
			except Exception:
				pass

		try:
			opshortcut = self._sanitize_family_name(self.ownerComp.par.opshortcut.eval())
			if opshortcut:
				return opshortcut
		except Exception:
			pass

		try:
			return self._sanitize_family_name(self.ownerComp.name)
		except Exception:
			return ''

	def _is_installed(self):
		try:
			return bool(int(bool(self.ownerComp.par.Install.eval())))
		except Exception:
			return False

	def _get_installer_delegate(self):
		component_ext = self._get_component_ext()
		if component_ext is not None and hasattr(component_ext, '_GetInstallerBridge'):
			try:
				return component_ext._GetInstallerBridge()
			except Exception:
				pass

		for attr_name in ('Installer', 'InstallerEXT', 'installer', 'installerExt', 'GenericInstallerEXT'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None and hasattr(ext_obj, 'Install'):
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
					if ext_obj is not None and hasattr(ext_obj, 'Install'):
						return ext_obj
				except Exception:
					pass

		return None

	def _get_uninstaller_delegate(self):
		component_ext = self._get_component_ext()
		if component_ext is not None and hasattr(component_ext, '_GetUninstallerBridge'):
			try:
				return component_ext._GetUninstallerBridge()
			except Exception:
				pass

		for attr_name in ('Uninstaller', 'UninstallerEXT', 'uninstaller', 'uninstallerExt', 'GenericUninstallerEXT'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None and hasattr(ext_obj, 'RemoveFamily'):
					return ext_obj
			except Exception:
				pass

		try:
			ext_namespace = getattr(self.ownerComp, 'ext', None)
		except Exception:
			ext_namespace = None

		if ext_namespace is not None:
			for attr_name in ('Uninstaller', 'UninstallerEXT', 'uninstaller', 'uninstallerExt', 'GenericUninstallerEXT'):
				try:
					ext_obj = getattr(ext_namespace, attr_name, None)
					if ext_obj is not None and hasattr(ext_obj, 'RemoveFamily'):
						return ext_obj
				except Exception:
					pass

		return None

	def RenameFamily(self, new_name, show_message=False, previous_name=None):
		new_name = self._sanitize_family_name(new_name)
		if not new_name:
			return False

		old_name = self._sanitize_family_name(previous_name) or self._get_family_name()
		if not old_name or new_name == old_name:
			return False

		was_installed = self._is_installed()
		component_ext = self._get_component_ext()
		installer = self._get_installer_delegate()
		uninstaller = self._get_uninstaller_delegate()

		self._trace("RenameFamily start: '{}' -> '{}' installed={}".format(
			old_name,
			new_name,
			was_installed,
		))

		if component_ext is not None:
			try:
				component_ext._renameInProgress = True
			except Exception:
				pass

		try:
			self.ownerComp.store('cf_reinstall_in_progress', 1)
		except Exception:
			pass

		# If a sibling COMP already owns old_name, do NOT touch its UI — this
		# happens when a family is copy-pasted (TD renames the copy from 'Custom'
		# to 'Custom1', triggering this rename with old_name='Custom' while the
		# original 'Custom' COMP is still alive as a sibling).
		old_name_has_sibling = self._has_sibling_family_owner(old_name)

		try:
			# Rename path: preserve the visible bookmark toggle so _install_toggle
			# can rename it in-place. We skip _destroy_button_first here and the
			# direct button-variant cleanups below (preserve_button=True), so the
			# toggle never disappears between old and new name.
			if was_installed and uninstaller is not None and not old_name_has_sibling:
				try:
					try:
						uninstaller.RemoveFamily(family_name=old_name, preserve_button=True)
					except TypeError:
						# Older RemoveFamily signature without preserve_button kwarg.
						uninstaller.RemoveFamily(family_name=old_name)
				except Exception as e:
					self._trace("RemoveFamily failed during rename '{}': {}".format(old_name, e))
			if not old_name_has_sibling:
				self._force_cleanup_bookmark_family(old_name, preserve_button=True)
				self._force_cleanup_menu_op_family(old_name, uninstaller=uninstaller)

			try:
				self.ownerComp.name = new_name
			except Exception as e:
				self._trace("Owner rename failed '{}': {}".format(new_name, e))
				return False

			try:
				if hasattr(self.ownerComp.par, 'opshortcut'):
					try:
						self.ownerComp.par.opshortcut.expr = ''
					except Exception:
						pass
					try:
						self.ownerComp.par.opshortcut.bindExpr = ''
					except Exception:
						pass
					self.ownerComp.par.opshortcut = new_name
			except Exception as e:
				self._trace("Owner opshortcut update failed '{}': {}".format(new_name, e))

			if component_ext is not None:
				try:
					component_ext.UpdateGlobalShortcut()
				except Exception as e:
					self._trace("UpdateGlobalShortcut failed '{}': {}".format(new_name, e))

			# Pre-rename the preserved bookmark toggle from button_<old> to
			# button_<new> so _install_toggle finds it by its canonical name
			# and reuses it. Without this, _install_toggle would search for
			# button_<new> (not found, since the live toggle still bears the
			# old name) and copy a fresh toggle on top — producing two visible
			# buttons for the same family.
			if not old_name_has_sibling:
				self._rename_bookmark_toggle_in_place(old_name, new_name)

			if was_installed and installer is not None:
				# Second cleanup pass for the old name's side artifacts (watcher,
				# delete_execute, menu_op). We keep preserve_button=True here too
				# so the bookmark toggle survives all the way to _install_toggle
				# and gets renamed in-place.
				if not old_name_has_sibling:
					self._force_cleanup_bookmark_family(old_name, preserve_button=True)
					self._force_cleanup_menu_op_family(old_name, uninstaller=uninstaller)

				if uninstaller is not None:
					try:
						uninstaller.RemoveFamily(family_name=new_name)
					except Exception as e:
						self._trace("Pre-install cleanup failed for new family '{}': {}".format(new_name, e))

				try:
					self.ownerComp.par.Install = 1
				except Exception:
					pass

				try:
					result = installer.Install(family_name=new_name, show_message=show_message, reset_trace=False)
					self._trace("RenameFamily reinstall result '{}': {}".format(new_name, result))
					if result and component_ext is not None:
						try:
							component_ext.ScheduleUpdateAll(showMessage=False)
						except Exception:
							pass
					if result and uninstaller is not None and not old_name_has_sibling:
						try:
							try:
								uninstaller.RemoveFamily(family_name=old_name, preserve_button=True)
							except TypeError:
								uninstaller.RemoveFamily(family_name=old_name)
						except Exception as e:
							self._trace("Post-install cleanup failed for old family '{}': {}".format(old_name, e))
					if result and not old_name_has_sibling:
						self._force_cleanup_bookmark_family(old_name, preserve_button=True)
						self._force_cleanup_menu_op_family(old_name, uninstaller=uninstaller)
					return bool(result)
				except TypeError:
					try:
						result = installer.Install(new_name)
						self._trace("RenameFamily reinstall result '{}': {}".format(new_name, result))
						if result and component_ext is not None:
							try:
								component_ext.ScheduleUpdateAll(showMessage=False)
							except Exception:
								pass
						if result and uninstaller is not None and not old_name_has_sibling:
							try:
								uninstaller.RemoveFamily(family_name=old_name)
							except Exception as e:
								self._trace("Post-install cleanup failed for old family '{}': {}".format(old_name, e))
						if result and not old_name_has_sibling:
							self._force_cleanup_bookmark_family(old_name)
							self._force_cleanup_menu_op_family(old_name, uninstaller=uninstaller)
						return bool(result)
					except Exception as e:
						self._trace("Reinstall failed '{}': {}".format(new_name, e))
						return False
				except Exception as e:
					self._trace("Reinstall failed '{}': {}".format(new_name, e))
					return False

			if component_ext is not None:
				try:
					component_ext.ScheduleUpdateAll(showMessage=False)
				except Exception:
					pass
			return True
		finally:
			if component_ext is not None:
				try:
					component_ext._renameInProgress = False
				except Exception:
					pass
			try:
				run(
					"comp=op(args[0]); comp.unstore('cf_reinstall_in_progress') if comp else None",
					self.ownerComp.path,
					delayFrames=1,
				)
			except Exception:
				try:
					self.ownerComp.unstore('cf_reinstall_in_progress')
				except Exception:
					pass

	def HandleObservedNameChange(self, previous_name, new_name, show_message=False):
		previous_name = self._sanitize_family_name(previous_name)
		new_name = self._sanitize_family_name(new_name)

		if not previous_name or not new_name or previous_name == new_name:
			return False

		return self.RenameFamily(
			new_name,
			show_message=show_message,
			previous_name=previous_name,
		)

	def PromptRenameFamily(self):
		dialog = getattr(op.TDResources, 'PopDialog', None)
		if dialog is None:
			return False

		current_name = self._get_family_name() or self._sanitize_family_name(self.ownerComp.name)

		try:
			dialog.OpenDefault(
				title='Rename Family',
				text='Enter the new family name.',
				buttons=['Rename', 'Cancel'],
				callback=self._OnRenameFamilyDialog,
				details={'ownerPath': self.ownerComp.path},
				textEntry=True,
				textEntryDefault=current_name,
				escButton=2,
				enterButton=1,
				escOnClickAway=True,
			)
			return True
		except Exception as e:
			self._trace("PromptRenameFamily failed: {}".format(e))
			return False

	def _OnRenameFamilyDialog(self, info):
		if str(info.get('button', '')) != 'Rename':
			return False

		new_name = info.get('enteredText', '')
		result = self.RenameFamily(new_name, show_message=False)
		if not result:
			try:
				ui.messageBox('Plugin Manager', 'Rename family failed')
			except Exception:
				pass
		return result


RenameEXT = GenericRenameEXT
