import TDFunctions as TDF
import re
import os

SEARCH_DEPTH = 3
ABOUT_PAGE_NAME = 'About'
EXCLUDED_ABOUT_PAR_NAMES = {'Updateallcomponents'}
ABOUT_SKIP_NAMES = {
	'License',
	'Logo_and_license',
}
PLACEMENT_SENTINEL = (-99999.0, -99999.0)
SHORTCUT_BASE_NAME = 'Shortcut'
PLACEMENT_KEYBOARD_NAME = '_placement_keyboard'
PLACEMENT_KEYBOARD_CALLBACK_NAME = '_placement_keyboard_callback'

MANAGED_SCRIPT_BINDINGS = (
	(('ComponentEXT',), 'ComponentEXT.py'),
	(('InstallerEXT',), 'InstallerEXT.py'),
	(('UninstallerEXT',), 'UninstallerEXT.py'),
	(('RenameEXT',), 'RenameEXT.py'),
	(('Shortcut/_placement_keyboard_callback',), os.path.join('Shortcut', 'placement_keyboard_callback.py')),
	(('Ui_scripts/fam_create_callback',), os.path.join('Ui_scripts', 'fam_create_callback.py')),
	(('Ui_scripts/fam_panel_execute',), os.path.join('Ui_scripts', 'fam_panel_execute.py')),
	(('Ui_scripts/fam_script_callbacks',), os.path.join('Ui_scripts', 'fam_script_callbacks.py')),
	(('Parameter/About_page_DAT_execute', 'Parameters/About_page_DAT_execute'), os.path.join('Parameters', 'About_page_DAT_execute.py')),
	(('Parameter/Auto_install_execute', 'Parameters/Auto_install_execute'), os.path.join('Parameters', 'Auto_install_execute.py')),
	(('Parameter/Change_Color_DAT_execute', 'Parameters/Change_Color_DAT_execute'), os.path.join('Parameters', 'Change_Color_DAT_execute.py')),
	(('Parameter/Delete_op_execute', 'Parameters/Delete_op_execute'), os.path.join('Parameters', 'Delete_op_execute.py')),
	(('Parameter/install_dat_execute', 'Parameters/install_dat_execute'), os.path.join('Parameters', 'install_dat_execute.py')),
	(('Parameter/Manual_install_DAT_execute', 'Parameters/Manual_install_DAT_execute'), os.path.join('Parameters', 'Manual_install_DAT_execute.py')),
	(('Settings/Auto_install_execute',), os.path.join('Settings', 'Auto_install_execute.py')),
	(('Settings/Change_Color_DAT_execute',), os.path.join('Settings', 'Change_Color_DAT_execute.py')),
	(('Settings/Delete_op_execute',), os.path.join('Settings', 'Delete_op_execute.py')),
	(('Settings/Rename_op_exec',), os.path.join('Settings', 'Rename_op_exec.py')),
)
class ComponentEXT:

	def __init__(self, ownerComp):
		self.ownerComp = ownerComp
		self._isUpdating = False
		self._updateScheduled = False
		self._installWatchScheduled = False
		self._lastInstallParameterState = None
		self._identitySyncInProgress = False
		self._renameInProgress = False
		self._installerBridgeCache = None
		self._uninstallerBridgeCache = None
		self._renameBridgeCache = None
		self._pendingPlacementClonePath = ''
		self._pendingPlacementPane = None

		TDF.createProperty(self, 'MyProperty', value=0, dependable=True, readOnly=False)
		TDF.createProperty(self, 'Global_op_shortcut', value='', dependable=True, readOnly=False)
		TDF.createProperty(self, 'LastColorRGB', value=(1.0, 1.0, 1.0), dependable=True, readOnly=False)

		try:
			_color = ownerComp.parGroup.Color.eval()
		except Exception:
			_color = (1, 1, 1, 1)
		TDF.createProperty(self, 'Color', value=_color, dependable=True, readOnly=False)

		self.a = 0
		self.B = 1

		try:
			self._ApplyOwnerNameToShortcut(source_label='ComponentEXT.__init__')
		except Exception:
			pass

		try:
			reinstall_in_progress = bool(self.ownerComp.fetch('cf_reinstall_in_progress', 0))
		except Exception:
			reinstall_in_progress = False

		# During rename/reinstall a fresh extension instance can be created on the
		# just-renamed COMP. Avoid scheduling an eager UpdateAll from __init__ in
		# that window, otherwise the new family's UI can appear before the old
		# family's cleanup has fully finished.
		if not reinstall_in_progress:
			self.ScheduleUpdateAll(showMessage=False)

	def ScheduleUpdateAll(self, showMessage=False):
		if self._updateScheduled:
			return False

		self._updateScheduled = True

		try:
			run(
				"comp = op(args[0]); ext = getattr(comp, 'ComponentEXT', None) or getattr(getattr(comp, 'ext', None), 'ComponentEXT', None); ext.DeferredUpdateAll(args[1]) if ext else None",
				self.ownerComp.path,
				showMessage,
				delayFrames=1
			)
			return True
		except Exception as e:
			debug('Errore schedulando UpdateAll: {}'.format(e))
			self._updateScheduled = False
			return False

	def DeferredUpdateAll(self, showMessage=False):
		self._updateScheduled = False

		try:
			rename_in_progress = bool(getattr(self, '_renameInProgress', False))
		except Exception:
			rename_in_progress = False

		try:
			reinstall_in_progress = bool(self.ownerComp.fetch('cf_reinstall_in_progress', 0))
		except Exception:
			reinstall_in_progress = False

		# During the first rename (Custom -> C1) the COMP can be renamed before
		# the old UI has been fully removed. A deferred UpdateAll in that window
		# rebuilds parts of the new UI too early, so the new bookmark tag appears
		# before the old one is gone. Defer the refresh until the rename/reinstall
		# guard is fully cleared so the UI rebuild happens in the same order as
		# consecutive renames: old family removed first, new family installed next.
		if rename_in_progress or reinstall_in_progress:
			self.ScheduleUpdateAll(showMessage=showMessage)
			return False

		return self.UpdateAll(showMessage=showMessage)

	def SanitizePluginName(self, name):
		if name is None:
			return ''

		name = str(name).strip()
		name = name.replace(' ', '')
		name = re.sub(r'[^A-Za-z0-9_]', '', name)

		if name and name[0].isdigit():
			name = '_' + name

		return name

	def _ReadInstallParameterState(self):
		try:
			if hasattr(self.ownerComp.par, 'Install'):
				return int(bool(self.ownerComp.par.Install.eval()))
		except Exception:
			pass
		return None

	def _GetComponentRootPath(self):
		try:
			component_dat = self.ownerComp.op('ComponentEXT')
			if component_dat is not None and hasattr(component_dat.par, 'file'):
				script_path = str(component_dat.par.file.eval()).strip()
				if script_path:
					direct_root = os.path.dirname(script_path)
					if direct_root and os.path.isdir(direct_root):
						return direct_root
		except Exception:
			pass

		try:
			installer_dat = self.ownerComp.op('InstallerEXT')
			if installer_dat is not None and hasattr(installer_dat.par, 'file'):
				script_path = str(installer_dat.par.file.eval()).strip()
				if script_path:
					direct_root = os.path.dirname(script_path)
					if direct_root and os.path.isdir(direct_root):
						return direct_root
		except Exception:
			pass

		try:
			if os.path.isdir(project.folder):
				return project.folder
		except Exception:
			pass

		return ''

	def RepairManagedScriptSyncs(self):
		root_dir = self._GetComponentRootPath()
		if not root_dir:
			return 0

		updated = 0

		for op_path_candidates, rel_file_path in MANAGED_SCRIPT_BINDINGS:
			target_op = None

			for op_path in op_path_candidates:
				try:
					target_op = self.ownerComp.op(op_path)
					if target_op is not None:
						break
				except Exception:
					pass

			if target_op is None:
				continue

			desired_file = os.path.join(root_dir, rel_file_path)
			if not os.path.isfile(desired_file):
				continue

			try:
				current_file = str(target_op.par.file.eval()).strip() if hasattr(target_op.par, 'file') else ''
			except Exception:
				current_file = ''

			try:
				if hasattr(target_op.par, 'file') and current_file != desired_file:
					target_op.par.file = desired_file
					updated += 1
			except Exception as e:
				continue

			try:
				if hasattr(target_op.par, 'syncfile'):
					target_op.par.syncfile = True
			except Exception:
				pass

		return updated

	def _ApplyOwnerNameToShortcut(self, source_label='ComponentEXT.watch'):
		if self._identitySyncInProgress:
			return False

		try:
			owner_name = self.SanitizePluginName(self.ownerComp.name)
		except Exception:
			owner_name = ''

		try:
			current_shortcut = self.SanitizePluginName(self.ownerComp.par.opshortcut.eval())
		except Exception:
			current_shortcut = ''

		desired_shortcut = owner_name

		if not desired_shortcut:
			return False

		if current_shortcut == desired_shortcut:
			self.UpdateGlobalShortcut()
			return False

		self._identitySyncInProgress = True

		try:
			try:
				self.ownerComp.par.opshortcut = desired_shortcut
			except Exception as e:
				return False

			self.UpdateGlobalShortcut()
			return True
		finally:
			self._identitySyncInProgress = False

	def ScheduleInstallStateWatch(self):
		if self._installWatchScheduled:
			return False

		self._installWatchScheduled = True
		if self._lastInstallParameterState is None:
			self._lastInstallParameterState = self._ReadInstallParameterState()

		try:
			run(
				"comp = op(args[0]); ext = getattr(comp, 'ComponentEXT', None) or getattr(getattr(comp, 'ext', None), 'ComponentEXT', None); ext._PollInstallState() if ext else None",
				self.ownerComp.path,
				delayFrames=1
			)
			return True
		except Exception as e:
			self._installWatchScheduled = False
			return False

	def _PollInstallState(self):
		self._installWatchScheduled = False

		try:
			if not self.ownerComp.valid:
				return
		except Exception:
			return

		current_state = self._ReadInstallParameterState()
		previous_state = self._lastInstallParameterState

		if current_state is not None and previous_state is not None and current_state != previous_state:
			self._lastInstallParameterState = current_state

			try:
				if current_state == 1:
					self.Install()
				else:
					self._CallUninstallerRemoveFamily(family_name=self.GetFamilyName())
			except Exception:
				pass
		else:
			self._lastInstallParameterState = current_state

		self.ScheduleInstallStateWatch()

	def _NotifyInstallerFamilyChanged(self, previous_name, new_name):
		previous_key = self.SanitizePluginName(previous_name)
		new_key = self.SanitizePluginName(new_name)

		if not previous_key or not new_key or previous_key == new_key:
			return False

		if getattr(self, '_renameInProgress', False):
			return False

		try:
			if not hasattr(self.ownerComp.par, 'Install') or int(bool(self.ownerComp.par.Install.eval())) != 1:
				return False
		except Exception:
			return False

		return self._ReinstallInstalledFamily(previous_family=previous_key, new_family=new_key)

	def _CallInstallerInstall(self, family_name=None, show_message=False):
		installer = self._GetInstallerBridge()
		if installer is None:
			return False

		install_method = getattr(installer, 'Install', None)
		if not callable(install_method):
			return False

		try:
			if family_name is not None:
				return install_method(family_name=family_name, show_message=show_message)
			return install_method(show_message=show_message)
		except TypeError:
			try:
				if family_name is not None:
					return install_method(family_name)
				return install_method()
			except Exception:
				return False
		except Exception:
			return False

	def _CallUninstallerUiCleanup(self, family_name=None):
		uninstaller = self._GetUninstallerBridge()
		if uninstaller is None:
			return False

		for method_name in ('RemoveInstalledUi',):
			method = getattr(uninstaller, method_name, None)
			if callable(method):
				try:
					return bool(method(family_name=family_name))
				except TypeError:
					try:
						if family_name is not None:
							return bool(method(family_name))
						return bool(method())
					except Exception:
						return False
				except Exception:
					return False
		return False

	def _CallUninstallerRemoveFamily(self, family_name=None):
		uninstaller = self._GetUninstallerBridge()
		if uninstaller is None:
			return False

		for method_name in ('RemoveFamily', 'DeleteCleanup', 'Uninstall'):
			method = getattr(uninstaller, method_name, None)
			if callable(method):
				try:
					return bool(method(family_name=family_name))
				except TypeError:
					try:
						if family_name is not None:
							return bool(method(family_name))
						return bool(method())
					except Exception:
						return False
				except Exception:
					return False
		return False

	def _ReinstallInstalledFamily(self, previous_family, new_family):
		previous_family = self.SanitizePluginName(previous_family)
		new_family = self.SanitizePluginName(new_family)
		if not previous_family or not new_family:
			return False

		# Block any watcher-triggered auto-installs on this COMP while the
		# rename/reinstall is in progress. All InstallerEXT instances on this
		# COMP share the same ownerComp.store, so the flag is visible across
		# instances (including the extension registered as par.InstallerEXT).
		try:
			self.ownerComp.store('cf_reinstall_in_progress', 1)
		except Exception:
			pass

		try:
			removed_previous = self._CallUninstallerRemoveFamily(family_name=previous_family)
			if not removed_previous:
				self._CallUninstallerUiCleanup(family_name=previous_family)

			if new_family != previous_family:
				removed_new = self._CallUninstallerRemoveFamily(family_name=new_family)
				if not removed_new:
					self._CallUninstallerUiCleanup(family_name=new_family)

			try:
				if hasattr(self.ownerComp.par, 'Install'):
					self.ownerComp.par.Install = 1
			except Exception:
				pass

			self._lastInstallParameterState = 1
			return bool(self._CallInstallerInstall(family_name=new_family, show_message=False))
		finally:
			# Defer clearing the flag by 3 frames so watcher polls (deferred 1
			# frame) see the guard and don't fire stale auto-installs.
			try:
				run(
					"comp=op(args[0]); comp.unstore('cf_reinstall_in_progress') if comp else None",
					self.ownerComp.path,
					delayFrames=3,
				)
			except Exception:
				try:
					self.ownerComp.unstore('cf_reinstall_in_progress')
				except Exception:
					pass

	def UpdateGlobalShortcut(self):
		"""
		Legge il vero opshortcut del componente e lo salva solo nella property
		Global_op_shortcut, senza modificarlo.
		"""
		try:
			raw_name = self.ownerComp.par.opshortcut.eval()
		except Exception as e:
			debug('Errore leggendo opshortcut: {}'.format(e))
			raw_name = ''

		clean_name = self.SanitizePluginName(raw_name)
		previous_name = ''

		try:
			previous_name = self.SanitizePluginName(str(self.Global_op_shortcut).strip())
		except Exception:
			previous_name = ''

		try:
			if self.Global_op_shortcut != clean_name:
				self.Global_op_shortcut = clean_name
				self._NotifyInstallerFamilyChanged(previous_name, clean_name)
		except Exception as e:
			debug('Errore impostando Global_op_shortcut: {}'.format(e))

	def GetGlobalShortcut(self):
		"""
		Restituisce il global shortcut sanitizzato corrente.
		"""
		try:
			if not self.Global_op_shortcut:
				self.UpdateGlobalShortcut()
			return self.Global_op_shortcut
		except Exception:
			try:
				return self.SanitizePluginName(self.ownerComp.par.opshortcut.eval())
			except Exception:
				return self.SanitizePluginName(self.ownerComp.name)

	def GetFamilyName(self):
		return self.GetGlobalShortcut()

	def _ResolveCompOp(self, comp_ref):
		if comp_ref is None:
			return None

		try:
			if hasattr(comp_ref, 'path'):
				return comp_ref
		except Exception:
			pass

		try:
			comp_path = str(comp_ref).strip()
		except Exception:
			comp_path = ''

		if not comp_path:
			return None

		try:
			return op(comp_path)
		except Exception:
			return None

	def OpenFamilyContextMenu(self, buttonComp=None):
		button_op = self._ResolveCompOp(buttonComp)
		menu = None
		try:
			menu = getattr(op.TDResources, 'PopMenu', None)
		except Exception:
			menu = None
		if menu is None:
			for menu_name in ('popMenu', 'PopMenu', 'ButtonPopMenu'):
				try:
					menu = op.TDResources.op(menu_name)
				except Exception:
					menu = None
				if menu is not None:
					break
		if menu is None:
			return False

		items = [
			'Rename',
			'Edit custom operators',
			'Export family',
			'Delete',
		]

		try:
			menu.SetPlacement(
				hAlign='Left',
				vAlign='Top',
				alignOffset=(0, 0),
				buttonComp=button_op,
				hAttach='Left',
				vAttach='Bottom',
			)
		except Exception:
			pass

		try:
			menu.Open(
				items=items,
				callback=self._OnFamilyContextMenuSelect,
				callbackDetails={
					'ownerPath': self.ownerComp.path,
					'buttonPath': getattr(button_op, 'path', ''),
				},
			)
			return True
		except Exception as e:
			debug('OpenFamilyContextMenu failed: {}'.format(e))
			return False

	def _OnFamilyContextMenuSelect(self, info):
		item = str(info.get('item', '')).strip()

		if item == 'Rename':
			return self.PromptRenameFamily()
		if item == 'Edit custom operators':
			return self.EditCustomOperators()
		if item == 'Export family':
			return self.ExportFamily()
		if item == 'Delete':
			return self.DeleteFamily()

		return False

	def PromptRenameFamily(self):
		rename_bridge = self._GetRenameBridge()
		if rename_bridge is not None:
			prompt_method = getattr(rename_bridge, 'PromptRenameFamily', None)
			if callable(prompt_method):
				try:
					return bool(prompt_method())
				except Exception as e:
					debug('PromptRenameFamily bridge failed: {}'.format(e))

		dialog = getattr(op.TDResources, 'PopDialog', None)
		if dialog is None:
			return False

		current_name = self.GetFamilyName() or self.SanitizePluginName(self.ownerComp.name)

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
			debug('PromptRenameFamily failed: {}'.format(e))
			return False

	def _OnRenameFamilyDialog(self, info):
		if str(info.get('button', '')) != 'Rename':
			return False

		new_name = self.SanitizePluginName(info.get('enteredText', ''))
		if not new_name:
			try:
				ui.messageBox('Plugin Manager', 'Invalid family name')
			except Exception:
				pass
			return False

		rename_bridge = self._GetRenameBridge()
		if rename_bridge is not None:
			rename_method = getattr(rename_bridge, 'RenameFamily', None)
			if callable(rename_method):
				try:
					return bool(rename_method(new_name, show_message=False))
				except TypeError:
					try:
						return bool(rename_method(new_name))
					except Exception as e:
						debug('Rename family bridge failed: {}'.format(e))
				except Exception as e:
					debug('Rename family bridge failed: {}'.format(e))

		# Do not fall back to the legacy local rename path. That path renames the
		# owner and schedules UpdateAll immediately, which can rebuild the new
		# family's bookmark/menu UI before the previous family has been removed.
		# Keeping rename on the dedicated RenameEXT path ensures the same
		# cleanup+reinstall ordering for the first rename as for consecutive ones.
		try:
			ui.messageBox('Plugin Manager', 'Rename family bridge unavailable')
		except Exception:
			pass
		debug('Rename family aborted: RenameEXT bridge unavailable for {}'.format(self.ownerComp.path))
		return False

	def EditCustomOperators(self):
		root = self._GetCustomOperatorsRoot()
		if root is None:
			return False

		try:
			pane = getattr(ui.panes, 'current', None)
			if pane is not None and hasattr(pane, 'owner'):
				pane.owner = root
		except Exception:
			pass

		try:
			root.openViewer()
		except Exception:
			pass

		return True

	def ExportFamily(self):
		family_name = self.GetFamilyName() or self.SanitizePluginName(self.ownerComp.name) or 'Custom_family'

		try:
			default_path = os.path.join(project.folder, '{}.tox'.format(family_name))
		except Exception:
			default_path = '{}.tox'.format(family_name)

		try:
			export_path = ui.chooseFile(
				load=False,
				start=default_path,
				fileTypes=['tox'],
				title='Export family as',
			)
		except Exception:
			export_path = default_path

		if not export_path:
			return False

		if not str(export_path).lower().endswith('.tox'):
			export_path = '{}.tox'.format(export_path)

		try:
			self.ownerComp.save(export_path)
		except Exception:
			try:
				self.ownerComp.save(fileName=export_path)
			except Exception as e:
				debug('ExportFamily failed: {}'.format(e))
				return False

		try:
			ui.messageBox('Plugin Manager', 'Family exported')
		except Exception:
			pass

		return True

	def DeleteFamily(self):
		return self._CallUninstallerRemoveFamily(family_name=self.GetFamilyName())

	def _GetInstallerBridge(self):
		for attr_name in ('Installer', 'InstallerEXT', 'installer', 'installerExt', 'GenericInstallerEXT'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None and hasattr(ext_obj, 'Install'):
					self._installerBridgeCache = ext_obj
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
						self._installerBridgeCache = ext_obj
						return ext_obj
				except Exception:
					pass

		cached_bridge = self._installerBridgeCache
		if cached_bridge is not None:
			try:
				if hasattr(cached_bridge, 'Install'):
					return cached_bridge
			except Exception:
				self._installerBridgeCache = None

		for dat_name in ('InstallerEXT', 'installerext'):
			try:
				dat_op = self.ownerComp.op(dat_name)
				if dat_op is None:
					continue

				module = dat_op.module
				cls = getattr(module, 'GenericInstallerEXT', None)
				if cls is None:
					cls = getattr(module, 'InstallerEXT', None)
				if cls is None:
					continue

				color = self.GetColorFromOwner()
				installer = cls(
					self.ownerComp,
					color=color,
					auto_init=False,
					enable_runtime_hooks=False,
				)
				self._installerBridgeCache = installer
				return installer
			except Exception as e:
				debug('Errore creando installer bridge da {}: {}'.format(dat_name, e))

		return None


	def _GetUninstallerBridge(self):
		for attr_name in ('Uninstaller', 'UninstallerEXT', 'uninstaller', 'uninstallerExt', 'GenericUninstallerEXT'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None and (hasattr(ext_obj, 'RemoveFamily') or hasattr(ext_obj, 'RemoveInstalledUi')):
					self._uninstallerBridgeCache = ext_obj
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
					if ext_obj is not None and (hasattr(ext_obj, 'RemoveFamily') or hasattr(ext_obj, 'RemoveInstalledUi')):
						self._uninstallerBridgeCache = ext_obj
						return ext_obj
				except Exception:
					pass

		cached_bridge = self._uninstallerBridgeCache
		if cached_bridge is not None:
			try:
				if hasattr(cached_bridge, 'RemoveFamily') or hasattr(cached_bridge, 'RemoveInstalledUi'):
					return cached_bridge
			except Exception:
				self._uninstallerBridgeCache = None

		for dat_name in ('UninstallerEXT', 'uninstallerext'):
			try:
				dat_op = self.ownerComp.op(dat_name)
				if dat_op is None:
					continue
				module = dat_op.module
				cls = getattr(module, 'GenericUninstallerEXT', None) or getattr(module, 'UninstallerEXT', None)
				if cls is None:
					continue
				uninstaller = cls(self.ownerComp, auto_init=False, enable_runtime_hooks=False)
				self._uninstallerBridgeCache = uninstaller
				return uninstaller
			except Exception as e:
				debug('Errore creando uninstaller bridge da {}: {}'.format(dat_name, e))

		return None

	def _GetRenameBridge(self):
		for attr_name in ('Rename', 'RenameEXT', 'rename', 'renameExt', 'GenericRenameEXT'):
			try:
				ext_obj = getattr(self.ownerComp, attr_name, None)
				if ext_obj is not None and hasattr(ext_obj, 'RenameFamily'):
					self._renameBridgeCache = ext_obj
					return ext_obj
			except Exception:
				pass

		try:
			ext_namespace = getattr(self.ownerComp, 'ext', None)
		except Exception:
			ext_namespace = None

		if ext_namespace is not None:
			for attr_name in ('Rename', 'RenameEXT', 'rename', 'renameExt', 'GenericRenameEXT'):
				try:
					ext_obj = getattr(ext_namespace, attr_name, None)
					if ext_obj is not None and hasattr(ext_obj, 'RenameFamily'):
						self._renameBridgeCache = ext_obj
						return ext_obj
				except Exception:
					pass

		cached_bridge = self._renameBridgeCache
		if cached_bridge is not None:
			try:
				if hasattr(cached_bridge, 'RenameFamily'):
					return cached_bridge
			except Exception:
				self._renameBridgeCache = None

		for dat_name in ('RenameEXT', 'renameext'):
			try:
				dat_op = self.ownerComp.op(dat_name)
				if dat_op is None:
					continue
				module = dat_op.module
				cls = getattr(module, 'GenericRenameEXT', None) or getattr(module, 'RenameEXT', None)
				if cls is None:
					continue
				rename_ext = cls(self.ownerComp, auto_init=False, enable_runtime_hooks=False)
				self._renameBridgeCache = rename_ext
				return rename_ext
			except Exception as e:
				debug('Errore creando rename bridge da {}: {}'.format(dat_name, e))

		return None

	def Install(self):
		installer = self._GetInstallerBridge()
		if installer is None:
			debug('Install bridge: installer non trovato su {}'.format(self.ownerComp.path))
			return False

		try:
			self.UpdateGlobalShortcut()
		except Exception:
			pass

		try:
			if hasattr(self.ownerComp.par, 'Install'):
				self.ownerComp.par.Install = 1
		except Exception:
			pass

		self._lastInstallParameterState = 1
		try:
			return installer.Install()
		except Exception as e:
			debug('Install bridge failed su {}: {}'.format(self.ownerComp.path, e))
			return False

	def Uninstall(self):
		self._lastInstallParameterState = 0
		return self._CallUninstallerRemoveFamily(family_name=self.GetFamilyName())

	def HandleInstallValue(self, raw_value, source_label='external'):
		value_str = str(raw_value).strip().lower()
		if value_str in ('1', 'true', 'on', 'yes'):
			return self.Install()
		if value_str in ('0', 'false', 'off', 'no'):
			return self._CallUninstallerRemoveFamily(family_name=self.GetFamilyName())
		return False

	def DeleteCleanup(self):
		self._lastInstallParameterState = 0
		return self._CallUninstallerRemoveFamily(family_name=self.GetFamilyName())

	# -------------------------------------------------------------------------
	# COLOR
	# -------------------------------------------------------------------------

	def GetColorFromOwner(self):
		try:
			r = float(self.ownerComp.par.Colorr.eval())
			g = float(self.ownerComp.par.Colorg.eval())
			b = float(self.ownerComp.par.Colorb.eval())
			return (r, g, b)
		except Exception as e:
			debug('Errore leggendo Colorr/Colorg/Colorb: {}'.format(e))
			return (1.0, 1.0, 1.0)

	def _IsAnnotateComp(self, op_obj):
		if op_obj is None:
			return False

		try:
			return str(op_obj.OPType) == 'annotateCOMP'
		except Exception:
			return False

	def _IsInsideAnnotateComp(self, op_obj):
		current = op_obj

		while current is not None:
			if self._IsAnnotateComp(current):
				return True

			try:
				if current == self.ownerComp:
					return False
			except Exception:
				pass

			try:
				current = current.parent()
			except Exception:
				break

		return False

	def _IsInsideAboutSkipContainer(self, op_obj):
		current = op_obj

		while current is not None:
			try:
				if current == self.ownerComp:
					return False
			except Exception:
				pass

			try:
				current_name = str(current.name)
			except Exception:
				current_name = ''

			if current_name in ABOUT_SKIP_NAMES:
				return True

			try:
				current = current.parent()
			except Exception:
				break

		return False

	def _ShouldSkipManagedOp(self, op_obj):
		if op_obj is None:
			return True

		try:
			if op_obj == self.ownerComp:
				return False
		except Exception:
			pass

		if self._IsInsideAnnotateComp(op_obj):
			return True

		return False

	def _ShouldSkipAboutSyncOp(self, op_obj):
		if self._ShouldSkipManagedOp(op_obj):
			return True

		return self._IsInsideAboutSkipContainer(op_obj)

	def GetColorTargetsOfOwner(self, maxDepth=SEARCH_DEPTH):
		try:
			ops = [self.ownerComp]
			children = self.ownerComp.findChildren(maxDepth=maxDepth, includeUtility=True)
			if children:
				ops.extend(children)

			unique_ops = []
			seen_ids = set()

			for o in ops:
				try:
					oid = o.id
				except Exception:
					oid = id(o)

				if oid in seen_ids:
					continue

				seen_ids.add(oid)
				if not self._ShouldSkipManagedOp(o):
					unique_ops.append(o)

			return unique_ops

		except Exception as e:
			debug('Errore recuperando ownerComp + children: {}'.format(e))
			return [self.ownerComp]

	def UpdateChildrenColor(self, maxDepth=SEARCH_DEPTH):
		rgb = self.GetColorFromOwner()

		if self.LastColorRGB == rgb:
			return []

		self.LastColorRGB = rgb
		target_ops = self.GetColorTargetsOfOwner(maxDepth=maxDepth)

		for o in target_ops:
			try:
				if tuple(o.color) != tuple(rgb):
					o.color = rgb
			except Exception:
				try:
					current = o.par.color.eval()
					if tuple(current) != tuple(rgb):
						o.par.color = rgb
				except Exception:
					pass

		return target_ops

	def SyncInstalledColor(self, maxDepth=SEARCH_DEPTH):
		rgb = self.GetColorFromOwner()
		self.UpdateChildrenColor(maxDepth=maxDepth)

		installer = self._GetInstallerBridge()
		if installer is None:
			return rgb

		try:
			installer.color = rgb
		except Exception:
			pass

		try:
			is_installed = bool(self.ownerComp.par.Install.eval())
		except Exception:
			is_installed = False

		if not is_installed:
			return rgb

		try:
			menu_op = installer._ui('menu_op')
		except Exception:
			menu_op = None

		try:
			if hasattr(installer, '_update_colors_table'):
				installer._update_colors_table(menu_op)
		except Exception as e:
			debug('SyncInstalledColor colors table failed: {}'.format(e))

		try:
			if hasattr(installer, '_sync_button_color'):
				installer._sync_button_color(color=rgb)
		except Exception as e:
			debug('SyncInstalledColor button sync failed: {}'.format(e))

		try:
			if hasattr(installer, '_sync_ui_family_colors'):
				installer._sync_ui_family_colors(color=rgb)
		except Exception as e:
			debug('SyncInstalledColor UI sync failed: {}'.format(e))

		return rgb

	# -------------------------------------------------------------------------
	# ABOUT PAGE SYNC
	# -------------------------------------------------------------------------

	def FindCustomPage(self, o, page_name):
		try:
			for p in o.customPages:
				if p.name == page_name:
					return p
		except Exception:
			pass
		return None

	def GetAboutTargetCompsOfOwner(self, maxDepth=SEARCH_DEPTH):
		try:
			return [
				o for o in self.ownerComp.findChildren(maxDepth=maxDepth)
				if o.isCOMP and not self._ShouldSkipAboutSyncOp(o)
			]
		except Exception as e:
			debug('Errore recuperando target About ricorsivi: {}'.format(e))
			return []

	def _GetRootOpForExternalAboutTargets(self):
		try:
			root = op('/')
			if root is not None:
				return root
		except Exception:
			pass

		try:
			return self.ownerComp.root
		except Exception:
			return None

	def _MatchesExternalAboutFamily(self, op_obj):
		if op_obj is None:
			return False

		try:
			if op_obj == self.ownerComp:
				return False
		except Exception:
			pass

		family_name = self.GetFamilyName() or self.SanitizePluginName(self.ownerComp.name)
		family_name = self.SanitizePluginName(family_name)
		if not family_name:
			return False

		try:
			managed_family = self.SanitizePluginName(op_obj.fetch('cf_managed_family_name', ''))
		except Exception:
			managed_family = ''
		if managed_family == family_name:
			return True

		try:
			stored_family = self.SanitizePluginName(op_obj.fetch('family_name', ''))
		except Exception:
			stored_family = ''
		if stored_family and stored_family != family_name:
			return False

		try:
			stored_owner_path = str(op_obj.fetch('family_owner_path', '')).strip()
		except Exception:
			stored_owner_path = ''
		try:
			if stored_owner_path and stored_owner_path == self.ownerComp.path:
				return True
		except Exception:
			pass

		try:
			stored_shortcut = self.SanitizePluginName(op_obj.fetch('family_owner_shortcut', ''))
		except Exception:
			stored_shortcut = ''
		try:
			owner_shortcut = self.SanitizePluginName(self.ownerComp.par.opshortcut.eval())
		except Exception:
			owner_shortcut = family_name

		if stored_family and stored_shortcut and stored_shortcut == owner_shortcut:
			return True

		return self._RuntimeExecuteMatchesExternalAboutFamily(
			op_obj,
			family_name=family_name,
			owner_shortcut=owner_shortcut,
		)

	def _RuntimeExecuteMatchesExternalAboutFamily(self, op_obj, family_name='', owner_shortcut=''):
		try:
			execute_dat = op_obj.op('family_runtime_execute')
		except Exception:
			execute_dat = None
		if execute_dat is None:
			return False

		try:
			text = str(execute_dat.text or '')
		except Exception:
			return False
		if not text:
			return False

		if "FAMILY_NAME = {!r}".format(family_name) not in text:
			return False

		try:
			if "FAMILY_OWNER_PATH = {!r}".format(self.ownerComp.path) in text:
				return True
		except Exception:
			pass

		if owner_shortcut and "FAMILY_OWNER_SHORTCUT = {!r}".format(owner_shortcut) in text:
			return True

		return False

	def GetExternalAboutTargetComps(self):
		root = self._GetRootOpForExternalAboutTargets()
		if root is None:
			return []

		try:
			candidates = root.findChildren(depth=None)
		except Exception:
			try:
				candidates = root.findChildren(maxDepth=999)
			except Exception as e:
				debug('Errore recuperando target About esterni: {}'.format(e))
				return []

		targets = []
		for candidate in candidates:
			try:
				if not candidate.isCOMP:
					continue
			except Exception:
				continue

			if self._ShouldSkipAboutSyncOp(candidate):
				continue

			if self._MatchesExternalAboutFamily(candidate):
				targets.append(candidate)

		return targets

	def ExtractReferenceAboutDefinition(self, page_name=ABOUT_PAGE_NAME, excluded_par_names=None):
		"""
		Legge la definizione della pagina custom 'About' dal componente owner stesso.
		"""
		if excluded_par_names is None:
			excluded_par_names = EXCLUDED_ABOUT_PAR_NAMES

		reference_op = self.ownerComp
		page = self.FindCustomPage(reference_op, page_name)
		if page is None:
			return None

		par_defs = []

		for ref_par in page.pars:
			if ref_par.name in excluded_par_names:
				continue

			try:
				style_name = str(ref_par.style)
			except Exception:
				style_name = 'Str'

			try:
				size = ref_par.tuplet.size
			except Exception:
				size = 1

			try:
				value = ref_par.eval()
			except Exception:
				try:
					value = ref_par.val
				except Exception:
					value = ''

			menu_names = []
			menu_labels = []

			try:
				if ref_par.menuNames is not None:
					menu_names = list(ref_par.menuNames)
			except Exception:
				pass

			try:
				if ref_par.menuLabels is not None:
					menu_labels = list(ref_par.menuLabels)
			except Exception:
				pass

			par_defs.append({
				'name': ref_par.name,
				'label': ref_par.label,
				'style': style_name,
				'size': size,
				'value': value,
				'menuNames': menu_names,
				'menuLabels': menu_labels,
			})

		return par_defs

	def CreateCustomPage(self, target_op, page_name=ABOUT_PAGE_NAME):
		try:
			return target_op.appendCustomPage(page_name)
		except Exception as e:
			debug("Errore creando pagina '{}' su {}: {}".format(page_name, target_op.path, e))
			return None

	def GetOrCreateCustomPage(self, target_op, page_name=ABOUT_PAGE_NAME):
		page = self.FindCustomPage(target_op, page_name)
		if page is not None:
			return page
		return self.CreateCustomPage(target_op, page_name)

	def ParameterExists(self, target_op, par_name):
		try:
			return getattr(target_op.par, par_name, None) is not None
		except Exception:
			return False

	def AppendParameterFromDefinition(self, target_page, par_def):
		name = par_def['name']
		label = par_def['label']
		style_name = par_def['style']
		size = par_def['size']

		try:
			if style_name == 'Str':
				target_page.appendStr(name, label=label)
			elif style_name == 'StrMenu':
				target_page.appendStrMenu(name, label=label)
			elif style_name == 'Menu':
				target_page.appendMenu(name, label=label)
			elif style_name == 'Float':
				target_page.appendFloat(name, label=label, size=size)
			elif style_name == 'Int':
				target_page.appendInt(name, label=label, size=size)
			elif style_name == 'Toggle':
				target_page.appendToggle(name, label=label, size=size)
			elif style_name == 'Pulse':
				target_page.appendPulse(name, label=label)
			elif style_name == 'Momentary':
				target_page.appendMomentary(name, label=label)
			elif style_name == 'Python':
				target_page.appendPython(name, label=label)
			elif style_name == 'OP':
				target_page.appendOP(name, label=label)
			elif style_name == 'COMP':
				target_page.appendCOMP(name, label=label)
			elif style_name == 'Object':
				target_page.appendObject(name, label=label)
			elif style_name == 'PanelCOMP':
				target_page.appendPanelCOMP(name, label=label)
			elif style_name == 'File':
				target_page.appendFile(name, label=label)
			elif style_name == 'FileSave':
				target_page.appendFileSave(name, label=label)
			elif style_name == 'Folder':
				target_page.appendFolder(name, label=label)
			elif style_name == 'XY':
				target_page.appendXY(name, label=label)
			elif style_name == 'XYZ':
				target_page.appendXYZ(name, label=label)
			elif style_name == 'XYZW':
				target_page.appendXYZW(name, label=label)
			elif style_name == 'UVW':
				target_page.appendUVW(name, label=label)
			elif style_name == 'WH':
				target_page.appendWH(name, label=label)
			elif style_name == 'RGB':
				target_page.appendRGB(name, label=label)
			elif style_name == 'RGBA':
				target_page.appendRGBA(name, label=label)
			else:
				target_page.appendStr(name, label=label)

			return True

		except Exception as e:
			debug("Errore creando parametro '{}' ({}) su {}: {}".format(
				name, style_name, target_page.owner.path, e
			))
			return False

	def EnsureParameterExists(self, target_op, target_page, par_def):
		name = par_def['name']
		if self.ParameterExists(target_op, name):
			return True
		return self.AppendParameterFromDefinition(target_page, par_def)

	def ApplyExtraDefinition(self, target_op, par_def):
		name = par_def['name']
		menu_names = par_def['menuNames']
		menu_labels = par_def['menuLabels']

		try:
			target_par = getattr(target_op.par, name, None)
			if target_par is None:
				return

			if str(target_par.style) in ('Menu', 'StrMenu'):
				try:
					if list(target_par.menuNames) != list(menu_names):
						target_par.menuNames = menu_names
				except Exception as e:
					debug("Errore menuNames '{}' su {}: {}".format(name, target_op.path, e))

				try:
					if list(target_par.menuLabels) != list(menu_labels):
						target_par.menuLabels = menu_labels
				except Exception as e:
					debug("Errore menuLabels '{}' su {}: {}".format(name, target_op.path, e))

		except Exception as e:
			debug("Errore applicando definizione extra '{}' su {}: {}".format(name, target_op.path, e))

	def IsStringLikeStyle(self, style_name):
		return style_name in (
			'Str', 'StrMenu', 'File', 'FileSave', 'Folder',
			'OP', 'COMP', 'Object', 'PanelCOMP', 'Python',
		)

	def SetTupletValues(self, target_op, par_def):
		name = par_def['name']
		size = par_def['size']
		value = par_def['value']
		style_name = par_def['style']

		try:
			target_par = getattr(target_op.par, name, None)
			if target_par is None:
				return

			if size == 1:
				try:
					if str(target_par.style) in ('Menu', 'StrMenu'):
						current_val = target_par.menuIndex if isinstance(value, int) else target_par.eval()
						if current_val != value:
							if isinstance(value, int):
								target_par.menuIndex = value
							else:
								target_par.val = value
					else:
						if target_par.eval() != value:
							target_par.val = value
				except Exception as e:
					debug("Errore assegnando valore a '{}' su {}: {}".format(name, target_op.path, e))

				if self.IsStringLikeStyle(style_name):
					try:
						if not target_par.readOnly:
							target_par.readOnly = True
					except Exception as e:
						debug("Errore settando readOnly su '{}' in {}: {}".format(name, target_op.path, e))
				return

			try:
				tuplet = list(target_par.tuplet)
			except Exception:
				tuplet = [target_par]

			if not isinstance(value, (list, tuple)):
				value = [value] * len(tuplet)

			for i, p in enumerate(tuplet):
				try:
					if p.eval() != value[i]:
						p.val = value[i]
				except Exception as e:
					debug("Errore assegnando valore a '{}[{}]' su {}: {}".format(name, i, target_op.path, e))

				if self.IsStringLikeStyle(style_name):
					try:
						if not p.readOnly:
							p.readOnly = True
					except Exception as e:
						debug("Errore settando readOnly su '{}[{}]' in {}: {}".format(name, i, target_op.path, e))

		except Exception as e:
			debug("Errore finale su '{}' in {}: {}".format(name, target_op.path, e))

	def UpdateAboutSpecialValues(self, target_op):
		if target_op is None:
			return

		try:
			if hasattr(target_op.par, 'Version') and hasattr(self.ownerComp.par, 'Version'):
				new_val = self.ownerComp.par.Version.eval()
				if target_op.par.Version.eval() != new_val:
					target_op.par.Version = new_val
		except Exception as e:
			debug("Errore aggiornando Version su {}: {}".format(target_op.path, e))

		try:
			if hasattr(target_op.par, 'Savedinbuild') and hasattr(self.ownerComp.par, 'Savedinbuild'):
				new_val = self.ownerComp.par.Savedinbuild.eval()
				if target_op.par.Savedinbuild.eval() != new_val:
					target_op.par.Savedinbuild = new_val
		except Exception as e:
			debug("Errore aggiornando Savedinbuild su {}: {}".format(target_op.path, e))

	def SyncAboutOnComp(self, target_op, about_defs, page_name=ABOUT_PAGE_NAME):
		if target_op is None or about_defs is None:
			return

		if not hasattr(target_op, 'customPages'):
			return

		target_about = self.GetOrCreateCustomPage(target_op, page_name=page_name)
		if target_about is None:
			return

		for par_def in about_defs:
			ok = self.EnsureParameterExists(target_op, target_about, par_def)
			if ok:
				self.ApplyExtraDefinition(target_op, par_def)
				self.SetTupletValues(target_op, par_def)

		self.UpdateAboutSpecialValues(target_op)

	def RebuildAboutOnAllComps(self, page_name=ABOUT_PAGE_NAME, maxDepth=SEARCH_DEPTH):
		about_defs = self.ExtractReferenceAboutDefinition(page_name=page_name)
		if about_defs is None:
			return

		target_comps = []
		seen_ids = set()

		for target_op in self.GetAboutTargetCompsOfOwner(maxDepth=maxDepth) + self.GetExternalAboutTargetComps():
			try:
				oid = target_op.id
			except Exception:
				oid = id(target_op)

			if oid in seen_ids:
				continue

			seen_ids.add(oid)
			target_comps.append(target_op)

		if not target_comps:
			return

		for target_op in target_comps:
			self.SyncAboutOnComp(target_op, about_defs, page_name=page_name)

	# -------------------------------------------------------------------------
	# MAIN UPDATE
	# -------------------------------------------------------------------------

	def UpdateAll(self, showMessage=False):
		if self._isUpdating:
			return False

		try:
			rename_in_progress = bool(getattr(self, '_renameInProgress', False))
		except Exception:
			rename_in_progress = False

		try:
			reinstall_in_progress = bool(self.ownerComp.fetch('cf_reinstall_in_progress', 0))
		except Exception:
			reinstall_in_progress = False

		# A direct UpdateAll call can still slip in during the first rename from
		# older rename hooks or a previously queued refresh. If we let it run, it
		# rebuilds the new family's bookmark/menu UI before the old family has been
		# fully removed. Defer it through the guarded path instead.
		if rename_in_progress or reinstall_in_progress:
			self.ScheduleUpdateAll(showMessage=showMessage)
			return False

		self._isUpdating = True

		try:
			self.RepairManagedScriptSyncs()
			self._ConfigureRenameOpExecute()
			self._ApplyOwnerNameToShortcut(source_label='UpdateAll')
			self.UpdateGlobalShortcut()
			self._SetCustomOperatorsStorageState(self._GetCustomOperatorsRoot())
			self.UpdateChildrenColor(maxDepth=SEARCH_DEPTH)
			try:
				installer = self._GetInstallerBridge()
				if installer is not None:
					try:
						if hasattr(installer, '_sync_family_name'):
							installer._sync_family_name(apply_owner_shortcut=False)
						elif hasattr(installer, 'family_name'):
							installer.family_name = self.GetFamilyName() or self.SanitizePluginName(self.ownerComp.name)
					except Exception:
						pass
					if hasattr(installer, 'NormalizeCustomOperatorRuntimeExecutes'):
						try:
							installer.NormalizeCustomOperatorRuntimeExecutes()
						except Exception:
							pass
					if hasattr(installer, '_configure_delete_op_execute'):
						try:
							installer._configure_delete_op_execute()
						except Exception:
							pass
					if hasattr(installer, '_install_delete_execute_watcher'):
						try:
							installer._install_delete_execute_watcher()
						except Exception:
							pass
					if hasattr(installer, '_install_toggle'):
						try:
							installer._install_toggle()
						except Exception:
							pass
					if hasattr(installer, '_install_watcher'):
						try:
							installer._install_watcher()
						except Exception:
							pass
					if hasattr(installer, '_prepare_custom_operator_templates'):
						installer._prepare_custom_operator_templates()
					if hasattr(installer, '_patch_launch_menu_op'):
						try:
							installer._patch_launch_menu_op(installer._ui('menu_op'))
						except Exception:
							pass
					if hasattr(installer, '_ensure_cancel_custom_place_helper'):
						try:
							installer._ensure_cancel_custom_place_helper(installer._ui('menu_op'))
						except Exception:
							pass
					if hasattr(installer, '_cleanup_custom_comp_runners'):
						try:
							installer._cleanup_custom_comp_runners(installer.family_name)
						except Exception:
							pass
					if hasattr(installer, '_patch_create_node'):
						try:
							installer._patch_create_node(installer._ui('menu_op'))
						except Exception:
							pass
					if hasattr(installer, '_install_panel_execute'):
						try:
							installer._install_panel_execute(installer._ui('menu_op'))
						except Exception:
							pass
					if hasattr(installer, '_patch_search_exec'):
						try:
							installer._patch_search_exec(installer._ui('menu_op'))
						except Exception:
							pass
					if hasattr(installer, '_install_family_insert'):
						try:
							installer._install_family_insert(installer._ui('menu_op'))
						except Exception:
							pass
			except Exception as e:
				debug('UpdateAll custom operator refresh failed: {}'.format(e))
			self.RebuildAboutOnAllComps(page_name=ABOUT_PAGE_NAME, maxDepth=SEARCH_DEPTH)

			return True

		except Exception as e:
			debug('UpdateAll failed: {}'.format(e))
			return False

		finally:
			self._isUpdating = False

	def _ConfigureRenameOpExecute(self):
		rename_exec = None
		for name in ('Settings/Rename_op_exec', 'Rename_op_exec'):
			try:
				rename_exec = self.ownerComp.op(name)
				if rename_exec is not None:
					break
			except Exception:
				pass

		if rename_exec is None:
			return False

		root_dir = self._GetComponentRootPath()
		if root_dir:
			script_path = os.path.join(root_dir, 'Settings', 'Rename_op_exec.py')
			try:
				if hasattr(rename_exec.par, 'file'):
					rename_exec.par.file = script_path
			except Exception:
				pass

		try:
			if hasattr(rename_exec.par, 'syncfile'):
				rename_exec.par.syncfile = True
		except Exception:
			pass

		for par_name, par_value in (('active', True), ('namechange', True), ('pathchange', False)):
			try:
				if hasattr(rename_exec.par, par_name):
					setattr(rename_exec.par, par_name, par_value)
			except Exception:
				pass

		par_mode = globals().get('ParMode', None)
		target_expr = "op('{}')".format(str(self.ownerComp.path).replace("\\", "\\\\"))
		target_par_name = ''

		for candidate_name in ('op', 'ops'):
			if hasattr(rename_exec.par, candidate_name):
				target_par_name = candidate_name
				break

		for par_name in ('ops', 'fromop', 'op'):
			if not hasattr(rename_exec.par, par_name):
				continue

			par_obj = getattr(rename_exec.par, par_name)
			if par_name == target_par_name:
				try:
					if par_mode is not None and hasattr(par_obj, 'mode'):
						par_obj.mode = par_mode.EXPRESSION
				except Exception:
					pass

				try:
					par_obj.expr = target_expr
				except Exception:
					pass
				continue

			try:
				if par_mode is not None and hasattr(par_obj, 'mode'):
					par_obj.mode = par_mode.CONSTANT
			except Exception:
				pass

			try:
				par_obj.expr = ''
			except Exception:
				pass

			try:
				setattr(rename_exec.par, par_name, '')
			except Exception:
				pass

		return True

	def _GetCustomOperatorsRoot(self):
		for child_name, lookup in (
			('custom_operators', lambda name: self.ownerComp.op(name)),
			('Custom_operators', lambda name: self.ownerComp.op(name)),
			('custom_operators', lambda name: (self.ownerComp.findChildren(name=name, maxDepth=4) or [None])[0]),
			('Custom_operators', lambda name: (self.ownerComp.findChildren(name=name, maxDepth=4) or [None])[0]),
		):
			try:
				root = lookup(child_name)
				if root is not None:
					self._SetCustomOperatorsStorageState(root)
					return root
			except Exception:
				pass
		return None

	def _SetCustomOperatorsStorageState(self, root):
		if root is None:
			return False

		try:
			root.allowCooking = False
		except Exception:
			pass

		try:
			root.bypass = True
		except Exception:
			pass

		try:
			if hasattr(root, 'par') and hasattr(root.par, 'bypass'):
				root.par.bypass = 1
		except Exception:
			pass

		return True

	def _GetMenuVarTable(self):
		for path in (
			'/ui/dialogs/menu_op/local/set_variables',
			'/ui/dialogs/menu_op/set_variables',
		):
			try:
				var_table = op(path)
				if var_table is not None:
					return var_table
			except Exception:
				pass
		return None

	def _GetPlacementParent(self):
		try:
			pane = ui.panes.current
			if pane is not None and hasattr(pane, 'owner') and pane.owner is not None:
				return pane.owner
		except Exception:
			pass
		return None

	def _GetPlacementPosition(self):
		var_table = self._GetMenuVarTable()
		if var_table is not None:
			try:
				return (float(var_table['xpos', 1].val), float(var_table['ypos', 1].val))
			except Exception:
				pass
		return (0.0, 0.0)

	def _TryNativePlacement(self, master, display_name):
		try:
			pane = ui.panes.current
		except Exception:
			pane = None
		if pane is None:
			return False
		try:
			self._pendingPlacementPane = pane
		except Exception:
			self._pendingPlacementPane = None

		candidates = (
			(pane, 'placeOPs', ([master],), 'pane.placeOPs(list)'),
			(pane, 'placeOPs', (master,), 'pane.placeOPs(single)'),
			(pane, 'placeOP', (master,), 'pane.placeOP(single)'),
			(pane, 'dropOPs', ([master],), 'pane.dropOPs(list)'),
			(pane, 'dropOPs', (master,), 'pane.dropOPs(single)'),
			(pane, 'dropOP', (master,), 'pane.dropOP(single)'),
		)

		for target_obj, method_name, args, label in candidates:
			try:
				method = getattr(target_obj, method_name, None)
			except Exception:
				continue

			if not callable(method):
				continue

			try:
				method(*args)
				return True
			except Exception:
				pass
		return False

	def _BuildPlacedCloneName(self, target_parent, base_name):
		base_name = str(base_name).replace(' ', '_')
		index = 1

		while True:
			candidate = "{}{}".format(base_name, index)
			try:
				if target_parent.op(candidate) is None:
					return candidate
			except Exception:
				return candidate
			index += 1

	def _ApplyLicenseToClone(self, clone, master):
		try:
			license_op = self.ownerComp.op('License')
			if license_op is None or master.family != 'COMP':
				return False

			existing_lic = clone.op('License')
			if existing_lic is not None:
				try:
					if existing_lic.par.Bodytext.eval() == license_op.par.Bodytext.eval():
						return True
					existing_lic.destroy()
				except Exception:
					pass

			clone.copy(license_op)
			return True
		except Exception:
			return False

	def _HidePlacedClone(self, clone):
		try:
			clone.expose = False
		except Exception:
			pass

	def _GetShortcutRoot(self):
		try:
			return self.ownerComp.op(SHORTCUT_BASE_NAME) or self.ownerComp
		except Exception:
			return self.ownerComp

	def _GetPlacementKeyboardCallbackDat(self):
		try:
			container = self._GetShortcutRoot()
			if container is None:
				return None
			callback_dat = container.op(PLACEMENT_KEYBOARD_CALLBACK_NAME)
			if callback_dat is None:
				callback_dat = container.create(textDAT, PLACEMENT_KEYBOARD_CALLBACK_NAME)
			if callback_dat is None:
				return None
			try:
				root_dir = self._GetComponentRootPath()
				desired_file = os.path.join(root_dir, 'Shortcut', 'placement_keyboard_callback.py') if root_dir else ''
				if desired_file and os.path.isfile(desired_file):
					callback_dat.par.file = desired_file
					callback_dat.par.syncfile = True
			except Exception:
				pass
			try:
				callback_dat.nodeX = -120
				callback_dat.nodeY = -200
			except Exception:
				pass
			return callback_dat
		except Exception:
			return None

	def _GetPlacementKeyboardDat(self):
		try:
			container = self._GetShortcutRoot()
			keyboard_dat = container.op(PLACEMENT_KEYBOARD_NAME) if container is not None else None
			if keyboard_dat is None:
				keyboard_dat = container.create(keyboardinDAT, PLACEMENT_KEYBOARD_NAME) if container is not None else None
			if keyboard_dat is None:
				return None
			callback_dat = self._GetPlacementKeyboardCallbackDat()
			try:
				keyboard_dat.par.active = True
			except Exception:
				pass
			try:
				keyboard_dat.par.keys = ''
			except Exception:
				pass
			try:
				keyboard_dat.par.maxlines = 8
			except Exception:
				pass
			try:
				if callback_dat is not None and hasattr(keyboard_dat.par, 'callbacks'):
					keyboard_dat.par.callbacks = callback_dat.path
			except Exception:
				pass
			try:
				if hasattr(keyboard_dat.par, 'executeloc'):
					keyboard_dat.par.executeloc = 'callbacks'
			except Exception:
				pass
			try:
				keyboard_dat.nodeX = -120
				keyboard_dat.nodeY = 0
			except Exception:
				pass
			return keyboard_dat
		except Exception:
			return None

	def _ResetPlacementKeyboard(self):
		keyboard_dat = self._GetPlacementKeyboardDat()
		if keyboard_dat is None:
			return
		callback_dat = self._GetPlacementKeyboardCallbackDat()
		if callback_dat is not None:
			try:
				if callback_dat.module.reset_keyboard(keyboard_dat):
					return
			except Exception:
				pass
		try:
			keyboard_dat.par.clear.pulse()
		except Exception:
			pass

	def _SyncCancelCustomPlaceHelper(self, clone_path='__KEEP__'):
		try:
			helper = op('/ui/dialogs/menu_op/cancel_custom_place')
		except Exception:
			helper = None
		if helper is None:
			return False
		if clone_path == '__KEEP__':
			clone_path = str(self._pendingPlacementClonePath or '').strip()
		try:
			helper.store('pending_clone_path', str(clone_path or ''))
			helper.store('pending_component_path', self.ownerComp.path)
			return True
		except Exception:
			return False

	def _SetPendingPlacementClone(self, clone):
		try:
			self._pendingPlacementClonePath = clone.path if clone is not None else ''
		except Exception:
			self._pendingPlacementClonePath = ''
		self._SyncCancelCustomPlaceHelper()

	def _ClearPendingPlacementClone(self, clone_path=None):
		if clone_path is None or self._pendingPlacementClonePath == clone_path:
			self._pendingPlacementClonePath = ''
			self._pendingPlacementPane = None
			self._SyncCancelCustomPlaceHelper('')

	def _CancelPendingPlacement(self, clear_pane=False):
		clone_path = str(self._pendingPlacementClonePath or '').strip()
		if not clone_path:
			self._SyncCancelCustomPlaceHelper('')
			return False
		clone = op(clone_path)
		try:
			pane = self._pendingPlacementPane if clear_pane else None
		except Exception:
			pane = None
		if clear_pane and pane is None:
			try:
				pane = ui.panes.current
			except Exception:
				pane = None
		self._pendingPlacementClonePath = ''
		self._pendingPlacementPane = None
		self._SyncCancelCustomPlaceHelper('')
		if clone is None:
			self._ResetPlacementKeyboard()
			return False
		try:
			clone.destroy()
		except Exception:
			pass
		if pane is not None:
			for method_name, args in (
				('placeOPs', ([],)),
				('dropOPs', ([],)),
			):
				try:
					method = getattr(pane, method_name, None)
					if callable(method):
						method(*args)
				except Exception:
					pass
		self._ResetPlacementKeyboard()
		return True

	def CancelPendingPlacement(self, clear_pane=False):
		return self._CancelPendingPlacement(clear_pane=clear_pane)

	def _RevealPlacedClone(self, clone):
		try:
			clone.allowCooking = True
		except Exception:
			pass

		try:
			clone.bypass = False
		except Exception:
			pass

		try:
			clone.viewer = ui.preferences['network.viewer']
		except Exception:
			pass

		try:
			clone.expose = True
		except Exception:
			pass

	def _SchedulePlacedCloneFinalize(self, clone, start_x, start_y):
		try:
			run(
				"comp = op(args[0]); ext = getattr(comp, 'ComponentEXT', None) or getattr(getattr(comp, 'ext', None), 'ComponentEXT', None); ext and ext._FinalizePlacedClone(args[1], args[2], args[3])",
				self.ownerComp.path,
				clone.path,
				float(start_x),
				float(start_y),
				delayFrames=2,
				delayRef=op.TDResources
			)
		except Exception:
			pass

	def _FinalizePlacedClone(self, clone_path, start_x, start_y):
		clone = op(clone_path) if clone_path else None
		if clone is None:
			return False

		try:
			current_x = float(clone.nodeX)
			current_y = float(clone.nodeY)
		except Exception:
			current_x = start_x
			current_y = start_y

		if current_x == float(start_x) and current_y == float(start_y):
			self._SchedulePlacedCloneFinalize(clone, start_x, start_y)
			return False

		self._RevealPlacedClone(clone)
		self._ClearPendingPlacementClone(clone.path)
		self._ResetPlacementKeyboard()
		return True

	def PlaceNamedCustomOperator(self, display_name):
		self._CancelPendingPlacement()
		custom_root = self._GetCustomOperatorsRoot()
		if custom_root is None:
			return False

		try:
			master_ops = custom_root.findChildren(name=display_name, maxDepth=1)
		except Exception:
			return False

		if not master_ops:
			return False

		master = master_ops[0]

		target_parent = self._GetPlacementParent()
		if target_parent is None:
			return False

		clone_parent = target_parent
		clone_name = self._BuildPlacedCloneName(clone_parent, display_name)
		x, y = self._GetPlacementPosition()

		try:
			clone = clone_parent.copy(master, name=clone_name)
		except Exception:
			return False

		try:
			clone.allowCooking = True
			clone.bypass = False
		except Exception:
			pass

		self._ApplyLicenseToClone(clone, master)
		try:
			installer = self._GetInstallerBridge()
			if installer is not None and hasattr(installer, 'RefreshCustomOperatorTemplate'):
				installer.RefreshCustomOperatorTemplate(master)
				installer.RefreshCustomOperatorTemplate(clone)
			elif installer is not None and hasattr(installer, 'PrepareCustomOperatorRuntimeLink'):
				installer.PrepareCustomOperatorRuntimeLink(master)
				installer.PrepareCustomOperatorRuntimeLink(clone)
		except Exception:
			pass
		self._HidePlacedClone(clone)
		self._ResetPlacementKeyboard()
		self._SetPendingPlacementClone(clone)
		start_x, start_y = PLACEMENT_SENTINEL
		try:
			clone.nodeX = start_x
			clone.nodeY = start_y
		except Exception:
			pass
		if self._TryNativePlacement(clone, display_name):
			self._SchedulePlacedCloneFinalize(clone, start_x, start_y)
			return True

		self._RevealPlacedClone(clone)
		try:
			clone.nodeX = x
			clone.nodeY = y
		except Exception:
			pass

		return True

	def PlaceOp(self, panelValue, display_name):
		return self.PlaceNamedCustomOperator(display_name)
