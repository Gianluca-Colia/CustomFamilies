"""
Installer runtime.
"""

import time
import re
import os
import ssl
import urllib.request
import urllib.error


class GenericInstallerEXT:
	TRACE_FILE_NAME = 'ui_clone_manager_trace.txt'
	INSTALLED_FAMILY_STORAGE_KEY = 'installed_family_name'
	HOSTED_IMPORT_PENDING_KEY = 'cf_hosted_import_pending'
	HOSTED_IMPORT_FAMILY_KEY = 'cf_hosted_import_family'
	HOSTED_SOURCE_DELEGATED_KEY = 'cf_hosted_source_delegated'
	EXTERNAL_TOX_IMPORT_KEY = 'cf_external_tox_import'
	EXTERNAL_TOX_SOURCE_KEY = 'cf_external_tox_source'
	EXTERNAL_DROP_HELPER_PATH = '/sys/cf_external_tox_drop'
	SYS_DROP_ROUTE_MARKER_START = '# >>> CUSTOM_FAMILY_EXTERNAL_DROP START'
	SYS_DROP_ROUTE_MARKER_END = '# <<< CUSTOM_FAMILY_EXTERNAL_DROP END'
	CUSTOM_OPERATOR_LINK_START = '# >>> CUSTOM_FAMILY_LINK START'
	CUSTOM_OPERATOR_LINK_END = '# <<< CUSTOM_FAMILY_LINK END'
	CUSTOM_OPERATOR_RUNTIME_EXECUTE_NAME = 'family_runtime_execute'
	CUSTOM_COMP_RUNNER_PREFIX = 'cf'
	CUSTOM_COMP_RUNNER_MARKER = '# CUSTOM_FAMILY_RUNNER'
	CUSTOM_OPERATOR_RUNTIME_BASE_PARS = ('Colorr', 'Colorg', 'Colorb', 'Version')
	PLUGINS_ROOT_PATH = '/ui/Plugins'
	CUSTOM_FAMILIES_MANAGER_NAME = 'Custom_families'
	CUSTOM_FAMILIES_MANAGER_PATH = '/ui/Plugins/Custom_families'
	CUSTOM_FAMILIES_LOCAL_PATH = '/ui/Plugins/Custom_families/Local'
	CUSTOM_FAMILIES_SERVER_PATH = '/ui/Plugins/Custom_families/Server'
	LOCAL_BAR_PATH = '/ui/panes/panebar/pane1/Local_bar'
	SERVER_BAR_PATH = '/ui/panes/panebar/pane1/Server_bar'
	EMBEDDED_ROOT_NAME = 'Embeded'
	# Bootstrap-from-repo: when a family is dropped into a project that does
	# NOT have Custom_families installed (no /ui/Plugins/Custom_families and
	# no Local container), the family downloads the plugin .tox from this URL
	# and loads it into TD. We point at the dev raw .tox during alpha; switch
	# to a release asset (releases/download/<tag>/Custom_families.tox) once
	# we leave alpha to get versioning + download counter on each bootstrap.
	BOOTSTRAP_TOX_URL = 'https://github.com/Gianluca-Colia/CustomFamilies/raw/main/.tox/Custom_families/Custom_families.tox'
	BOOTSTRAP_TOX_TEMP_NAME = 'bootstrap_Custom_families.tox'
	CUSTOM_FAMILIES_INSTALL_COMPLETE_KEY = 'cf_install_complete'
	CUSTOM_OPERATOR_EXTENSION_SIGNATURES = (
		'Extension classes enhance TouchDesigner components with python',
		'from TDStoreTools import StorageManager',
		'import TDFunctions as TDF',
		'def onInitTD(',
		'def onDestroyTD(',
		'TDF.createProperty(',
	)

	DEFAULT_UI_PATHS = {
		'ui_root': '/ui',
		'bookmark_bar': '/ui/panes/panebar/pane1/Local_bar',
		'bookmark_empty_panel': '/ui/panes/panebar/pane1/Local_bar/emptypanel',
		'menu_op': '/ui/dialogs/menu_op',
		'custom_comps': '/ui/dialogs/menu_op/customCOMPs',
		'node_table': '/ui/dialogs/menu_op/nodetable',
		'colors_table': '/ui/dialogs/menu_op/colors',
		'launch_menu_op': '/ui/dialogs/menu_op/launch_menu_op',
		'create_node': '/ui/dialogs/menu_op/create_node',
		'cancel_custom_place': '/ui/dialogs/menu_op/cancel_custom_place',
		'search_exec': '/ui/dialogs/menu_op/search/panelexec1',
		'node_script': '/ui/dialogs/menu_op/node_script',
		'switch_script': '/ui/dialogs/menu_op/switch_script',
		'compatible_table': '/ui/dialogs/menu_op/compatible',
		'insert1': '/ui/dialogs/menu_op/insert1',
	}

	DEFAULT_SCRIPT_PATHS = {
		'fam_toggle': 'Ui_inject/button_Custom',
		'fam_panel_execute': 'Ui_inject/panel_execute_Custom',
		'fam_script_callbacks': 'Ui_inject/Inject_Custom/fam_script_callbacks',
		'fam_insert': 'Ui_inject/Insert_Custom',
		'fam_watcher': 'Ui_inject/Watcher_Custom',
	}

	SCRIPT_PATH_VARIANTS = {
		'fam_toggle': (
			'Ui_inject/button_Custom',
			'Family_toggle_button',
			'family_toggle_button',
			'Ui_scripts/Family_toggle_button',
			'Ui_scripts/fam_toggle',
			'fam_toggle',
		),
		'fam_panel_execute': (
			'Ui_inject/panel_execute_Custom',
			'Ui_scripts/fam_panel_execute',
		),
		'fam_script_callbacks': (
			'Ui_inject/Inject_Custom/fam_script_callbacks',
			'Ui_inject/Inject_custom/fam_script_callbacks',
			'Ui_scripts/fam_script_callbacks',
		),
		'fam_insert': (
			'Ui_inject/Insert_Custom',
			'Insert_Custom',
		),
		'fam_watcher': (
			'Ui_inject/Watcher_Custom',
			'Watcher_Custom',
		),
	}

	def __init__(
		self,
		ownerComp,
		color=None,
		compatible_types=None,
		connection_map=None,
		ui_paths=None,
		script_paths=None,
		auto_init=False,
		enable_runtime_hooks=True,
	):
		self.ownerComp = ownerComp
		self.color = color if color is not None else self._get_owner_color()
		self.compatible_types = compatible_types or []
		self._enableRuntimeHooks = bool(enable_runtime_hooks)
		self._autoInstallGuard = False

		self.ui_paths = dict(self.DEFAULT_UI_PATHS)
		self.script_paths = dict(self.DEFAULT_SCRIPT_PATHS)

		if ui_paths:
			self.ui_paths.update(ui_paths)

		if script_paths:
			self.script_paths.update(script_paths)

		self.last_install_time = 0
		self.install_cooldown = 2.0
		self._traceCleared = False
		self._installWatchScheduled = False
		self._lastInstallParameterState = None
		self._handlingInstallValue = False
		self._currentInstallSourceLabel = ''
		self._postInitScheduled = False
		self._lastInstallWasUpdate = False

		self.family_name = self._get_family_name()
		self._lastInstalledFamilyName = self._get_recorded_installed_family()

		self._trace("InstallerEXT init for '{}' hooks_enabled={}".format(
			self.ownerComp.path,
			self._enableRuntimeHooks
		))
		if self._enableRuntimeHooks:
			self.SchedulePostInitSetup()

	def _get_family_name(self):
		name, _ = self._get_family_identity()
		if name:
			return name

		try:
			name = str(self.ownerComp.par.opshortcut.eval()).strip()
			if name:
				return name
		except Exception:
			pass

		return str(self.ownerComp.name).strip()

	def _get_recorded_installed_family(self):
		recorded_family = ''

		try:
			if hasattr(self.ownerComp, 'fetch'):
				recorded_family = self.ownerComp.fetch(self.INSTALLED_FAMILY_STORAGE_KEY, '')
		except Exception:
			recorded_family = ''

		recorded_family = self._sanitize_family_name(recorded_family)
		return recorded_family

	def _set_recorded_installed_family(self, family_name):
		recorded_family = self._sanitize_family_name(family_name)
		self._lastInstalledFamilyName = recorded_family

		try:
			if hasattr(self.ownerComp, 'store'):
				self.ownerComp.store(self.INSTALLED_FAMILY_STORAGE_KEY, recorded_family)
		except Exception:
			pass

		return recorded_family


	def _get_uninstaller_delegate_for_comp(self, comp=None):
		comp = comp or self.ownerComp
		if comp is None:
			return None

		for attr_name in ('Uninstaller', 'UninstallerEXT', 'uninstaller', 'uninstallerExt', 'GenericUninstallerEXT'):
			try:
				ext_obj = getattr(comp, attr_name, None)
				if ext_obj is not None and (hasattr(ext_obj, 'RemoveFamily') or hasattr(ext_obj, 'RemoveInstalledUi')):
					return ext_obj
			except Exception:
				pass

		try:
			ext_namespace = getattr(comp, 'ext', None)
		except Exception:
			ext_namespace = None

		if ext_namespace is not None:
			for attr_name in ('Uninstaller', 'UninstallerEXT', 'uninstaller', 'uninstallerExt', 'GenericUninstallerEXT'):
				try:
					ext_obj = getattr(ext_namespace, attr_name, None)
					if ext_obj is not None and (hasattr(ext_obj, 'RemoveFamily') or hasattr(ext_obj, 'RemoveInstalledUi')):
						return ext_obj
				except Exception:
					pass

		for dat_name in ('UninstallerEXT', 'uninstallerext'):
			try:
				dat_op = comp.op(dat_name)
				if dat_op is None:
					continue
				module = dat_op.module
				cls = getattr(module, 'GenericUninstallerEXT', None) or getattr(module, 'UninstallerEXT', None)
				if cls is None:
					continue
				return cls(comp, auto_init=False, enable_runtime_hooks=False)
			except Exception:
				pass

		return None

	def _request_family_ui_cleanup(self, family_name=None, comp=None):
		delegate = self._get_uninstaller_delegate_for_comp(comp=comp)
		if delegate is None:
			return False
		method = getattr(delegate, 'RemoveInstalledUi', None)
		if not callable(method):
			return False
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

	def _request_family_remove(self, family_name=None, comp=None):
		delegate = self._get_uninstaller_delegate_for_comp(comp=comp)
		if delegate is None:
			return False
		for method_name in ('RemoveFamily', 'DeleteCleanup', 'Uninstall'):
			method = getattr(delegate, method_name, None)
			if not callable(method):
				continue
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

	def _cleanup_previous_family_before_install(self, new_family):
		new_family = self._sanitize_family_name(new_family)
		previous_family = self._get_recorded_installed_family()

		if not previous_family or not new_family or previous_family == new_family:
			return False

		# If a sibling COMP still owns previous_family, never remove its UI.
		# This covers the copy-paste case where the top-up Install() is called
		# directly (source_label='') and the duplicate guard via source_label
		# would otherwise be skipped.
		if self._find_sibling_family_owner(previous_family) is not None:
			self._trace("Cleanup previous family '{}' skipped: sibling COMP still owns it".format(previous_family))
			return False

		if self._should_preserve_existing_family_on_duplicate(
			previous_family,
			new_family,
		):
			return False

		self._trace("Cleanup previous installed family before install via UninstallerEXT: '{}' -> '{}'".format(
			previous_family,
			new_family,
		), showMessage=True)
		removed = self._request_family_remove(previous_family, comp=self.ownerComp)
		if not removed:
			self._request_family_ui_cleanup(previous_family, comp=self.ownerComp)
		self._cleanup_external_delete_helpers(previous_family)
		return True

	def _ui(self, key):
		# bookmark_bar / bookmark_empty_panel are resolved dynamically based
		# on the owner's current location (Local vs Server). All other keys
		# fall through to the static ui_paths dict.
		if key == 'bookmark_bar':
			return op(self._resolve_bookmark_bar_path())
		if key == 'bookmark_empty_panel':
			return op(self._resolve_bookmark_bar_path() + '/emptypanel')
		path = self.ui_paths.get(key, '')
		o = op(path)
		if o is None:
			debug("Missing UI path '{}' -> '{}'".format(key, path))
		return o

	def _resolve_bookmark_bar_path(self, owner=None):
		"""Return the toolbar path the family's bookmark toggle should live in.

		Server_bar when ownerComp lives under Custom_families/Server/...;
		Local_bar in every other case (Local container, pre-routing limbo,
		or any unknown drop location — those eventually get routed into
		Local by _resolve_install_host()).
		"""
		comp = owner if owner is not None else self.ownerComp
		try:
			owner_path = str(comp.path) if comp is not None else ''
		except Exception:
			owner_path = ''
		if owner_path.startswith(self.CUSTOM_FAMILIES_SERVER_PATH + '/'):
			return self.SERVER_BAR_PATH
		return self.LOCAL_BAR_PATH

	def _script(self, key):
		candidates = []
		configured_path = self.script_paths.get(key, '')
		if configured_path:
			candidates.append(configured_path)

		for variant in self.SCRIPT_PATH_VARIANTS.get(key, ()):
			if variant not in candidates:
				candidates.append(variant)

		for path in candidates:
			try:
				o = self.ownerComp.op(path)
				if o is not None:
					self.script_paths[key] = path
					return o
			except Exception:
				pass

		debug("Missing local script template '{}' -> {} under {}".format(
			key, candidates, self.ownerComp.path
		))
		return None

	def _parameter_dat(self, *names):
		for name in names:
			try:
				o = self.ownerComp.op(name)
				if o is not None:
					return o
			except Exception:
				pass
		return None

	def _get_component_root_candidates(self):
		candidates = []

		try:
			installer_dat = self.ownerComp.op('InstallerEXT')
			if installer_dat is not None and hasattr(installer_dat.par, 'file'):
				script_path = str(installer_dat.par.file.eval()).strip()
				if script_path:
					direct_root = os.path.dirname(script_path)
					if direct_root and direct_root not in candidates:
						candidates.append(direct_root)

					parent_root = os.path.dirname(direct_root)
					if parent_root and parent_root not in candidates:
						candidates.append(parent_root)
		except Exception:
			pass

		try:
			comp_path = getattr(self.ownerComp, 'path', '')
			if comp_path:
				# solo informativo nel trace quando il resolver usa fallback
				self._trace("Root candidates for '{}': {}".format(
					comp_path,
					' | '.join(candidates) if candidates else '<none>'
				))
		except Exception:
			pass

		return candidates

	def _get_parameter_script_path(self, filename):
		# The script files for parameter DATs live in Custom_fam/Settings/ on
		# disk. Older layouts used Parameters/ or Parameter/, so we still try
		# those for backward compatibility.
		for root_dir in self._get_component_root_candidates():
			for candidate in (
				os.path.join(root_dir, 'Settings', filename),
				os.path.join(root_dir, 'Parameters', filename),
				os.path.join(root_dir, 'Parameter', filename),
				os.path.join(root_dir, 'Scripts', 'Parameters', filename),
			):
				try:
					if os.path.isfile(candidate):
						return candidate
				except Exception:
					pass

		try:
			for candidate in (
				os.path.join(project.folder, 'Settings', filename),
				os.path.join(project.folder, 'Parameters', filename),
				os.path.join(project.folder, 'Parameter', filename),
				os.path.join(project.folder, 'Scripts', 'Parameters', filename),
			):
				if os.path.isfile(candidate):
					return candidate
		except Exception:
			pass

		return ''

	def _get_owner_color(self):
		try:
			return (
				float(self.ownerComp.par.Colorr.eval()),
				float(self.ownerComp.par.Colorg.eval()),
				float(self.ownerComp.par.Colorb.eval()),
			)
		except Exception:
			pass

		try:
			color_val = self.ownerComp.parGroup.Color.eval()
			if len(color_val) >= 3:
				return (float(color_val[0]), float(color_val[1]), float(color_val[2]))
		except Exception:
			pass

		return (1.0, 1.0, 1.0)

	def _show_message(self, text, delay_frames=5):
		try:
			run(
				"ui.messageBox('Plugin Manager', args[0])",
				text,
				delayFrames=delay_frames,
				delayRef=op.TDResources
			)
		except Exception as e:
			debug("Message scheduling failed: {}".format(e))

	def SchedulePostInitSetup(self):
		if self._postInitScheduled:
			return False

		self._postInitScheduled = True
		try:
			run(
				"comp = op(args[0]); ext_ns = getattr(comp, 'ext', None); installer = getattr(comp, 'InstallerEXT', None) or getattr(comp, 'GenericInstallerEXT', None) or getattr(ext_ns, 'InstallerEXT', None) or getattr(ext_ns, 'GenericInstallerEXT', None); installer._DeferredPostInitSetup() if installer else None",
				self.ownerComp.path,
				delayFrames=2
			)
			self._trace("InstallerEXT post init scheduled for '{}'".format(self.ownerComp.path))
			return True
		except Exception as e:
			self._postInitScheduled = False
			self._trace("InstallerEXT post init schedule failed for '{}': {}".format(self.ownerComp.path, e))
			return False

	def _DeferredPostInitSetup(self):
		self._postInitScheduled = False

		try:
			if not self.ownerComp.valid:
				return False
		except Exception:
			return False

		# Post-init can run a few frames after a rename. Always resync the live
		# family identity from the current COMP name before touching UI helpers
		# or scheduling any recovery install.
		try:
			self._sync_family_name(apply_owner_shortcut=False)
		except Exception:
			pass

		self._trace("InstallerEXT post init start for '{}'".format(self.ownerComp.path))
		try:
			self._patch_sys_drop_route()
		except Exception:
			pass
		try:
			self._patch_launch_menu_op(self._ui('menu_op'))
		except Exception:
			pass
		try:
			self._ensure_cancel_custom_place_helper(self._ui('menu_op'))
		except Exception:
			pass
		self.ScheduleInstallStateWatch()
		self._configure_delete_op_execute()
		try:
			existing_delete_watcher = self._find_child_by_names(
				self._ui('bookmark_bar'),
				self._delete_execute_names(self.family_name),
			)
		except Exception:
			existing_delete_watcher = None
		if existing_delete_watcher is not None:
			self._install_delete_execute_watcher()
		self._cleanup_external_delete_helpers()
		self._trace("InstallerEXT post init finished for '{}'".format(self.ownerComp.path))
		self._schedule_post_init_install_top_up()
		return True

	def _schedule_post_init_install_top_up(self):
		"""Schedule a deferred install pass to recover missing UI elements
		(toggle / inject / watcher) when the component was imported from a .tox
		that ran an older version of Install() that didn't place them."""
		try:
			if self.ownerComp.fetch(self.HOSTED_SOURCE_DELEGATED_KEY, False):
				return
		except Exception:
			pass

		owner_path = self.ownerComp.path
		if not str(owner_path).startswith(self.CUSTOM_FAMILIES_LOCAL_PATH + '/'):
			return

		if not self._read_install_parameter_state():
			return
		fam = self.family_name
		try:
			run(
				"comp=op(args[0]); fam=args[1];"
				# Skip entirely if a rename/reinstall is already in progress.
				" _skip=bool(comp.fetch('cf_reinstall_in_progress',0)) if comp else True;"
				" _skip=_skip or (bool(comp.fetch('cf_hosted_source_delegated',0)) if comp else True);"
				" _skip=_skip or (not str(args[0]).startswith('/ui/Plugins/Custom_families/Local/'));"
				" cur=(str(comp.name).strip() if (not _skip and comp is not None) else '') or (str(comp.par.opshortcut.eval()).strip() if (not _skip and hasattr(comp.par,'opshortcut')) else '');"
				" fam=cur if cur else fam;"
				" bb=op('/ui/panes/panebar/pane1/Local_bar'); nt=op('/ui/dialogs/menu_op/nodetable');"
				" btn=bb.op('button_'+fam) if bb else None;"
				" inj=nt.op('inject_'+fam) if nt else None;"
				" wtch=bb.op('watcher_'+fam) if bb else None;"
				" dat=(comp.op('InstallerEXT') if (not _skip and (btn is None or inj is None or wtch is None)) else None);"
				" cls=getattr(dat.module,'GenericInstallerEXT',None) if dat else None;"
				" cls(comp,auto_init=False,enable_runtime_hooks=False).HandleInstallValue(1, source_label='PostInit.topUp') if cls else None",
				owner_path,
				fam,
				delayFrames=15,
			)
			self._trace("InstallerEXT post init top-up scheduled for '{}'".format(owner_path))
		except Exception as e:
			self._trace("InstallerEXT post init top-up schedule failed for '{}': {}".format(owner_path, e))

	def _reset_trace(self, label=None):
		trace_path = self._get_trace_file_path()

		if not self._traceCleared:
			try:
				with open(trace_path, 'a', encoding='utf-8') as trace_file:
					trace_file.write("\n=== TRACE SESSION {} ===\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
			except Exception:
				pass
			self._traceCleared = True

		if label:
			try:
				with open(trace_path, 'a', encoding='utf-8') as trace_file:
					trace_file.write("\n=== {} @ {} ===\n".format(label, time.strftime('%Y-%m-%d %H:%M:%S')))
			except Exception:
				pass

	def _get_trace_file_path(self):
		try:
			installer_dat = self.ownerComp.op('InstallerEXT')
			if installer_dat is not None and hasattr(installer_dat.par, 'file'):
				script_path = str(installer_dat.par.file.eval()).strip()
				if script_path:
					return os.path.join(os.path.dirname(script_path), self.TRACE_FILE_NAME)
		except Exception:
			pass

		try:
			return os.path.join(project.folder, 'Scripts', self.TRACE_FILE_NAME)
		except Exception:
			return self.TRACE_FILE_NAME

	def _write_trace(self, message):
		trace_path = self._get_trace_file_path()
		mode = 'a'

		if not self._traceCleared:
			try:
				with open(trace_path, 'a', encoding='utf-8') as trace_file:
					trace_file.write("\n=== TRACE SESSION {} ===\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
			except Exception:
				pass
			self._traceCleared = True

		try:
			with open(trace_path, mode, encoding='utf-8') as trace_file:
				trace_file.write(str(message) + '\n')
		except Exception:
			pass

	def _trace(self, message, showMessage=False):
		self._write_trace(message)
		return

	def _get_install_message(self, install_kind=None):
		# Clarify the popup: this is the *family* install completing, not the
		# plugin install (the plugin's own Install_window says "Installation
		# Completed!"). Include the family name so users with several families
		# see which one just finished.
		try:
			family_label = self._sanitize_family_name(self.family_name) or str(self.ownerComp.name)
		except Exception:
			family_label = str(getattr(self.ownerComp, 'name', '') or 'family')

		if isinstance(install_kind, bool):
			return "Family '{}' updated!".format(family_label) if install_kind else "Family '{}' installed!".format(family_label)

		install_kind = str(install_kind or '').strip().lower()
		if install_kind == 'copy':
			return "Family '{}' copied!".format(family_label)
		if install_kind == 'update':
			return "Family '{}' updated!".format(family_label)
		return "Family '{}' installed!".format(family_label)

	def _show_route_message(self, route_label, delay_frames=1):
		route_label = str(route_label or '').strip()
		if not route_label:
			return False
		self._show_message("Route: {}".format(route_label), delay_frames=delay_frames)
		return True

	def _get_external_drop_router_script_path(self):
		for root_dir in self._get_component_root_candidates():
			for candidate in (
				os.path.join(root_dir, 'external_tox_drop_router.py'),
				os.path.join(root_dir, 'Drop_scripts', 'external_tox_drop_router.py'),
			):
				try:
					if os.path.isfile(candidate):
						return candidate
				except Exception:
					pass
		return ''

	def _external_drop_helper(self):
		try:
			return op(self.EXTERNAL_DROP_HELPER_PATH)
		except Exception:
			return None

	def _ensure_external_drop_helper(self):
		try:
			sys_comp = op('/sys')
		except Exception:
			sys_comp = None

		if sys_comp is None:
			return None

		helper = self._external_drop_helper()
		if helper is None:
			try:
				helper = sys_comp.create(textDAT, os.path.basename(self.EXTERNAL_DROP_HELPER_PATH))
			except Exception as e:
				self._trace("External drop helper create failed: {}".format(e))
				return None

		script_path = self._get_external_drop_router_script_path()
		if script_path:
			try:
				if hasattr(helper.par, 'file'):
					helper.par.file = script_path
			except Exception as e:
				self._trace("External drop helper file binding failed: {}".format(e))
			try:
				if hasattr(helper.par, 'syncfile'):
					helper.par.syncfile = True
			except Exception:
				pass

		return helper

	def _sys_drop_route_hook_block(self):
		return (
			"\t\t\t{}\n"
			"\t\t\ttry:\n"
			"\t\t\t\tdrop_hook = op('{}')\n"
			"\t\t\t\tdrop_mod = getattr(drop_hook, 'module', None) if drop_hook is not None else None\n"
			"\t\t\t\tif drop_mod is not None and hasattr(drop_mod, 'onCreatedDroppedOp'):\n"
			"\t\t\t\t\tdrop_mod.onCreatedDroppedOp(dropDict, newOp)\n"
			"\t\t\texcept Exception:\n"
			"\t\t\t\tpass\n"
			"\t\t\t{}\n"
		).format(
			self.SYS_DROP_ROUTE_MARKER_START,
			self.EXTERNAL_DROP_HELPER_PATH,
			self.SYS_DROP_ROUTE_MARKER_END,
		)

	def _patch_sys_drop_route(self):
		self._ensure_external_drop_helper()

		try:
			drop_dat = op('/sys/drop')
		except Exception:
			drop_dat = None

		if drop_dat is None:
			return False

		try:
			current_text = str(drop_dat.text)
		except Exception:
			return False

		pattern = re.compile(
			re.escape(self.SYS_DROP_ROUTE_MARKER_START) + r'.*?' + re.escape(self.SYS_DROP_ROUTE_MARKER_END) + r'\n?',
			re.S,
		)
		clean_text = re.sub(pattern, '', current_text)

		hook_anchor = "\t\t\tnewOp = getattr(DragDrop,funcName)(dropDict)\n"
		if hook_anchor not in clean_text:
			self._trace("Sys drop route patch skipped: anchor not found")
			return False

		new_text = clean_text.replace(hook_anchor, hook_anchor + self._sys_drop_route_hook_block(), 1)
		if new_text == current_text:
			return True

		try:
			drop_dat.text = new_text
			self._trace("Sys drop route patch applied to /sys/drop")
			return True
		except Exception as e:
			self._trace("Sys drop route patch failed: {}".format(e))
			return False

	def _peek_external_tox_drop_info_for_owner(self):
		helper = self._ensure_external_drop_helper() or self._external_drop_helper()
		if helper is None:
			return {}

		try:
			module = helper.module
		except Exception:
			module = None

		if module is None or not hasattr(module, 'peekPendingForPath'):
			return {}

		try:
			info = module.peekPendingForPath(self.ownerComp.path)
		except Exception:
			info = {}

		return dict(info) if isinstance(info, dict) else {}

	def _pop_external_tox_drop_info_for_owner(self):
		helper = self._ensure_external_drop_helper() or self._external_drop_helper()
		if helper is None:
			return {}

		try:
			module = helper.module
		except Exception:
			module = None

		if module is None or not hasattr(module, 'popPendingForPath'):
			return {}

		try:
			info = module.popPendingForPath(self.ownerComp.path)
		except Exception:
			info = {}

		return dict(info) if isinstance(info, dict) else {}

	def _has_external_tox_import_marker(self):
		try:
			return bool(self.ownerComp.fetch(self.EXTERNAL_TOX_IMPORT_KEY, False))
		except Exception:
			return False

	def _set_external_tox_import_marker(self, active=False, source_path=''):
		updated = False
		try:
			self.ownerComp.store(self.EXTERNAL_TOX_IMPORT_KEY, bool(active))
			self.ownerComp.store(self.EXTERNAL_TOX_SOURCE_KEY, str(source_path or ''))
			updated = True
		except Exception:
			pass
		return updated

	def _clear_external_tox_import_marker(self):
		return self._set_external_tox_import_marker(False, '')

	def _is_auto_source(self, source_label):
		return str(source_label).startswith('Auto.')

	def _is_hosted_auto_import(self, source_label):
		return str(source_label).strip() == 'Auto.hostedCopy'

	def _has_hosted_copy_marker(self):
		try:
			return bool(self.ownerComp.fetch('cf_hosted_import_copy', False))
		except Exception:
			return False

	def _set_hosted_copy_marker(self, state):
		try:
			self.ownerComp.store('cf_hosted_import_copy', bool(state))
			return True
		except Exception:
			return False

	def _is_duplicate_install_source(self, source_label):
		source_label = str(source_label).strip()
		return self._is_auto_source(source_label) or source_label == 'InstallerEXT.watch'

	def _find_sibling_family_owner(self, family_name):
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return None

		try:
			parent_comp = self.ownerComp.parent()
		except Exception:
			parent_comp = None

		if parent_comp is None:
			return None

		try:
			sibling = parent_comp.op(family_name)
		except Exception:
			sibling = None

		if sibling is None or sibling == self.ownerComp:
			return None
		return sibling

	def _is_internal_duplicate_copy(self, source_label):
		if not self._is_duplicate_install_source(source_label):
			return False

		if self._is_hosted_auto_import(source_label):
			return False

		if self._has_external_tox_import_marker():
			return False

		if self._peek_external_tox_drop_info_for_owner():
			return False

		if self._has_hosted_copy_marker():
			return False

		if self._has_hosted_import_pending():
			return False

		try:
			candidate_name = self._sanitize_family_name(self.ownerComp.name)
		except Exception:
			candidate_name = self._sanitize_family_name(self.family_name)

		base_name, suffix_digits = self._split_family_suffix_digits(candidate_name)
		if base_name and suffix_digits and self._has_external_family_source(base_name):
			self._trace("Duplicate copy check skipped: hosted external source detected for '{}'".format(base_name))
			return False
		if not (base_name and suffix_digits):
			return False

		if self._find_sibling_family_owner(base_name) is not None:
			self._trace("Duplicate copy detected via sibling family '{}' -> '{}'".format(
				base_name,
				candidate_name,
			))
			return True

		return bool(self._is_inside_custom_families_base())

	def _should_preserve_existing_family_on_duplicate(self, previous_family, new_family, source_label=None):
		previous_family = self._sanitize_family_name(previous_family)
		new_family = self._sanitize_family_name(new_family)
		source_label = str(source_label or getattr(self, '_currentInstallSourceLabel', '')).strip()

		if not previous_family or not new_family or previous_family == new_family:
			return False

		if not self._is_duplicate_install_source(source_label):
			return False

		if self._is_hosted_auto_import(source_label):
			return False

		if self._has_external_tox_import_marker() or self._peek_external_tox_drop_info_for_owner():
			return False

		base_name, suffix_digits = self._split_family_suffix_digits(new_family)
		if not (base_name and suffix_digits):
			return False

		if previous_family != base_name:
			return False

		if self._find_sibling_family_owner(base_name) is None:
			return False

		self._trace("Duplicate install guard preserving existing family '{}' while adding '{}'".format(
			previous_family,
			new_family,
		))
		return True

	def _prepare_internal_duplicate_identity(self):
		try:
			duplicate_name = self._sanitize_family_name(self.ownerComp.name)
		except Exception:
			duplicate_name = self._sanitize_family_name(self.family_name)

		if not duplicate_name:
			return ''

		self.family_name = duplicate_name
		self._set_owner_shortcut(duplicate_name)
		try:
			# A duplicated family should start from a fully initialized identity,
			# otherwise its first manual rename behaves like a "first-ever" rename:
			# some cleanup/reinstall paths still see it as uninitialized and the old
			# bookmark button can linger longer than on consecutive renames.
			self._set_recorded_installed_family(duplicate_name)
		except Exception:
			pass
		try:
			rename_exec = self.ownerComp.op('Settings/Rename_op_exec') or self.ownerComp.op('Rename_op_exec')
		except Exception:
			rename_exec = None
		if rename_exec is not None:
			try:
				rename_exec.store('cf_last_family_name', duplicate_name)
			except Exception:
				pass
			try:
				rename_exec.store('cf_rename_exec_guard', False)
			except Exception:
				pass
		self._trace("Prepared duplicated family identity '{}' without canonical update".format(
			duplicate_name
		))
		return duplicate_name

	def _get_hosted_import_store_host(self):
		return self.ownerComp

	def _get_hosted_import_family(self):
		family_name = ''

		try:
			family_name = self.ownerComp.fetch(self.HOSTED_IMPORT_FAMILY_KEY, '')
		except Exception:
			family_name = ''

		family_name = self._sanitize_family_name(family_name)
		return self._sanitize_family_name(family_name)

	def _has_hosted_import_pending(self):
		pending = False

		try:
			pending = bool(self.ownerComp.fetch(self.HOSTED_IMPORT_PENDING_KEY, False))
		except Exception:
			pending = False

		if pending:
			return bool(self._get_hosted_import_family())

		return False

	def _set_hosted_import_pending(self, family_name=''):
		family_name = self._sanitize_family_name(family_name)
		updated = False

		try:
			self.ownerComp.store(self.HOSTED_IMPORT_PENDING_KEY, bool(family_name))
			self.ownerComp.store(self.HOSTED_IMPORT_FAMILY_KEY, family_name)
			updated = True
		except Exception:
			pass

		return updated

	def _clear_hosted_import_pending(self):
		cleared = False

		try:
			self.ownerComp.store(self.HOSTED_IMPORT_PENDING_KEY, False)
			self.ownerComp.store(self.HOSTED_IMPORT_FAMILY_KEY, '')
			cleared = True
		except Exception:
			pass

		return cleared

	def _get_auto_install_guard(self):
		return bool(getattr(self, '_autoInstallGuard', False))

	def _set_auto_install_guard(self, value=True):
		self._autoInstallGuard = bool(value)
		return True

	def _normalize_install_action(self, raw_value):
		value_str = str(raw_value).strip().lower()

		if value_str in ('1', 'true', 'on', 'yes'):
			return value_str, 'Install'

		if value_str in ('0', 'false', 'off', 'no'):
			return value_str, 'Uninstall'

		return value_str, None

	def _current_frame(self):
		try:
			return int(absTime.frame)
		except Exception:
			return -1

	def SuppressContextMenuToggle(self, frame_window=3):
		expected_state = self._read_install_parameter_state()
		if expected_state is None:
			expected_state = 1 if getattr(self, '_lastInstallParameterState', 1) else 0

		try:
			self.ownerComp.store('cf_context_menu_toggle_guard_until', self._current_frame() + max(int(frame_window), 1))
			self.ownerComp.store('cf_context_menu_toggle_guard_state', int(bool(expected_state)))
			self._trace(
				"Context menu toggle suppressed for '{}' until frame {} state={}".format(
					self.ownerComp.path,
					self.ownerComp.fetch('cf_context_menu_toggle_guard_until', -1),
					int(bool(expected_state)),
				)
			)
			return True
		except Exception:
			return False

	def _context_menu_toggle_guard_state(self):
		try:
			until_frame = int(self.ownerComp.fetch('cf_context_menu_toggle_guard_until', -1))
		except Exception:
			until_frame = -1

		current_frame = self._current_frame()
		if until_frame < 0 or current_frame < 0 or current_frame > until_frame:
			return None

		try:
			return int(bool(self.ownerComp.fetch('cf_context_menu_toggle_guard_state', 0)))
		except Exception:
			return 0

	def _clear_context_menu_toggle_guard(self):
		try:
			self.ownerComp.store('cf_context_menu_toggle_guard_until', -1)
			self.ownerComp.store('cf_context_menu_toggle_guard_state', 0)
			return True
		except Exception:
			return False

	def _read_install_parameter_state(self):
		try:
			if hasattr(self.ownerComp.par, 'Install'):
				return int(bool(self.ownerComp.par.Install.eval()))
		except Exception:
			pass
		return None

	def ScheduleInstallStateWatch(self):
		if not self._enableRuntimeHooks:
			return False

		if self._installWatchScheduled:
			return False

		self._installWatchScheduled = True
		if self._lastInstallParameterState is None:
			self._lastInstallParameterState = self._read_install_parameter_state()
			self._trace("InstallerEXT watcher initialized on '{}': state={}".format(
				self.ownerComp.path,
				self._lastInstallParameterState
			), showMessage=True)

		try:
			run(
				"comp = op(args[0]); ext_ns = getattr(comp, 'ext', None); installer = getattr(comp, 'InstallerEXT', None) or getattr(comp, 'GenericInstallerEXT', None) or getattr(ext_ns, 'InstallerEXT', None) or getattr(ext_ns, 'GenericInstallerEXT', None); installer._PollInstallState() if installer else None",
				self.ownerComp.path,
				delayFrames=1
			)
			return True
		except Exception as e:
			self._installWatchScheduled = False
			self._trace("InstallerEXT watcher schedule failed on '{}': {}".format(
				self.ownerComp.path,
				e
			), showMessage=True)
			return False

	def _PollInstallState(self):
		self._installWatchScheduled = False

		try:
			if not self.ownerComp.valid:
				return
		except Exception:
			return

		current_state = self._read_install_parameter_state()
		previous_state = self._lastInstallParameterState

		if (
			not self._handlingInstallValue
			and current_state is not None
			and previous_state is not None
			and current_state != previous_state
		):
			# If a rename/reinstall is in progress on this COMP (set by
			# ComponentEXT._ReinstallInstalledFamily), skip the watcher trigger
			# to avoid a stale auto-install that would recreate old-family nodes.
			try:
				reinstall_in_progress = bool(self.ownerComp.fetch('cf_reinstall_in_progress', 0))
			except Exception:
				reinstall_in_progress = False
			if reinstall_in_progress:
				self._lastInstallParameterState = current_state
				self.ScheduleInstallStateWatch()
				return
			# Sync family_name from the COMP's actual current opshortcut before
			# acting so a stale family_name doesn't cause a re-install with the old name.
			try:
				cur_shortcut = str(self.ownerComp.par.opshortcut.eval()).strip()
				if cur_shortcut:
					self.family_name = self._sanitize_family_name(cur_shortcut)
			except Exception:
				pass
			self._trace("InstallerEXT watcher change on '{}': {} -> {}".format(
				self.ownerComp.path,
				previous_state,
				current_state
			), showMessage=True)
			self._lastInstallParameterState = current_state
			self.HandleInstallValue(current_state, source_label='InstallerEXT.watch')
		else:
			self._lastInstallParameterState = current_state

		self.ScheduleInstallStateWatch()

	def _set_owner_shortcut(self, value):
		try:
			# Clear any expression/bind that would override the constant value after assignment.
			# The template may have par.opshortcut.expr = 'Custom' (hardcoded in expression mode);
			# without clearing it, .eval() keeps returning 'Custom' even after setting the constant.
			try:
				self.ownerComp.par.opshortcut.expr = ''
			except Exception:
				pass
			try:
				self.ownerComp.par.opshortcut.bindExpr = ''
			except Exception:
				pass
			self.ownerComp.par.opshortcut = value
		except Exception as e:
			debug("Failed setting owner opshortcut '{}': {}".format(value, e))

	def _get_main_root(self):
		try:
			root_op = op('/')
			if root_op is not None:
				return root_op
		except Exception:
			pass

		current = self.ownerComp
		last_valid = current

		while current is not None:
			last_valid = current
			try:
				parent_op = current.parent()
			except Exception:
				parent_op = None

			if parent_op is None:
				break

			current = parent_op

		return last_valid

	def _get_project_root(self):
		current = self.ownerComp
		last_valid = current

		while current is not None:
			last_valid = current
			try:
				parent_op = current.parent()
			except Exception:
				parent_op = None

			if parent_op is None:
				break

			try:
				if str(parent_op.path) == '/':
					return current
			except Exception:
				pass

			current = parent_op

		return last_valid

	def _progress(self, message):
		debug('[Custom_fam install] {}'.format(message))
		self._trace(message)

	def _get_or_create_plugins_root(self):
		plugins_root = op(self.PLUGINS_ROOT_PATH)
		if plugins_root is not None:
			return plugins_root

		ui_root = op('/ui')
		if ui_root is None:
			return None

		plugins_root = ui_root.create(baseCOMP, 'Plugins')
		return plugins_root

	def _is_inside_custom_families_base(self):
		# Canonical path match first (cheap).
		owner_path = str(self.ownerComp.path)
		if owner_path == self.CUSTOM_FAMILIES_MANAGER_PATH or \
			owner_path.startswith(self.CUSTOM_FAMILIES_MANAGER_PATH + '/'):
			return True
		# Ancestry match: family is sitting inside a Custom_families COMP that
		# lives somewhere else (e.g. a freshly-dragged .tox at /project1/...).
		# In that case the plugin's own install dialog will handle install;
		# the family must NOT bootstrap a fresh download on top.
		return self._is_component_inside_custom_families(self.ownerComp)

	def _is_inside_custom_families_local(self):
		owner_path = str(self.ownerComp.path)
		return owner_path.startswith(self.CUSTOM_FAMILIES_LOCAL_PATH + '/')

	def _is_component_inside_custom_families(self, candidate):
		current = candidate
		while current is not None:
			try:
				if str(current.name) == 'Custom_families':
					return True
			except Exception:
				pass

			try:
				current = current.parent()
			except Exception:
				current = None

		return False

	def _has_external_family_source(self, family_name):
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return False

		for candidate in self._iter_main_root_components():
			if candidate is None:
				continue
			if self._is_component_inside_custom_families(candidate):
				continue
			if self._is_owner_subtree_member(candidate):
				continue

			candidate_name, candidate_shortcut = self._family_identity_of_op(candidate)
			candidate_name = self._sanitize_family_name(candidate_name)
			candidate_shortcut = self._sanitize_family_name(candidate_shortcut)
			if family_name in (candidate_name, candidate_shortcut):
				return True

		return False

	def _queue_auto_install_in_custom_families(self):
		# Two clear cases only:
		#  Case 1 - Custom_families host already installed AND its Local exists:
		#           move the imported family directly into Local and trigger
		#           its install chain.
		#  Case 2 - Host not yet installed (no global op shortcut, no Local):
		#           install the embedded Custom_families into /ui/Plugins,
		#           enable cooking, pulse the Install button on the host. Then:
		#             - wait until host Installstate becomes 1, then fall back
		#               to Case 1 logic to install the family.
		if self._is_inside_custom_families_base():
			return False

		# Resolve via full paths only. Using the global op shortcut
		# (op.Custom_families) is unsafe here: while we are still holding the
		# embedded Custom_families inside this family AND the installed copy
		# under /ui/Plugins/Custom_families both carry the same shortcut, the
		# lookup becomes ambiguous and TD can resolve it to the wrong one.
		cf_root = op(self.CUSTOM_FAMILIES_MANAGER_PATH)
		cf_local = op(self.CUSTOM_FAMILIES_LOCAL_PATH)

		if cf_root is not None and cf_local is not None:
			return self._move_family_to_local(cf_local)

		# Case C-special: family dropped into a project where the plugin
		# isn't installed (no /ui/Plugins/Custom_families, no Local). Pull
		# the plugin .tox straight from GitHub and load it under /ui/Plugins,
		# then wait for its install to complete before moving the family
		# into the now-existing Local container.
		host = self._install_host_from_repo()
		if host is None:
			return False

		self._schedule_wait_for_host_then_move(host)
		return True

	def _move_family_to_local(self, cf_local):
		canonical_family = self._resolve_canonical_family_name(self.family_name) or self.family_name or str(self.ownerComp.name)
		external_drop_info = self._peek_external_tox_drop_info_for_owner()
		is_external_tox_drop = bool(external_drop_info)

		try:
			self.ownerComp.store(self.HOSTED_SOURCE_DELEGATED_KEY, True)
		except Exception:
			pass

		try:
			copied_owner = cf_local.copy(self.ownerComp, name=str(self.ownerComp.name), includeDocked=True)
		except Exception as e:
			self._trace("Family copy into Local failed for '{}': {}".format(self.ownerComp.path, e))
			return False

		if copied_owner is None:
			return False

		# The embedded host lives under Embeded and is kept as inert source
		# material. Do not destroy it: only the copied host at /ui/Plugins is
		# allowed to cook and run its installer.
		try:
			embedded_root = copied_owner.op(self.EMBEDDED_ROOT_NAME)
			if embedded_root is not None:
				embedded_root.allowCooking = False
		except Exception:
			pass

		try:
			if hasattr(copied_owner.par, 'opshortcut'):
				copied_owner.par.opshortcut = canonical_family
		except Exception:
			pass

		try:
			copied_owner.store('cf_hosted_import_copy', True)
			copied_owner.store(self.HOSTED_SOURCE_DELEGATED_KEY, False)
			copied_owner.store(self.HOSTED_IMPORT_PENDING_KEY, True)
			copied_owner.store(self.HOSTED_IMPORT_FAMILY_KEY, canonical_family)
			copied_owner.store(self.EXTERNAL_TOX_IMPORT_KEY, is_external_tox_drop)
			copied_owner.store(
				self.EXTERNAL_TOX_SOURCE_KEY,
				str(external_drop_info.get('source', '')) if is_external_tox_drop else ''
			)
		except Exception:
			pass

		try:
			self.ownerComp.allowCooking = False
		except Exception:
			pass

		if is_external_tox_drop:
			self._pop_external_tox_drop_info_for_owner()

		run(
			"comp = op(args[0]); ext_ns = getattr(comp, 'ext', None); installer = getattr(comp, 'InstallerEXT', None) or getattr(comp, 'GenericInstallerEXT', None) or getattr(ext_ns, 'InstallerEXT', None) or getattr(ext_ns, 'GenericInstallerEXT', None); installer.HandleInstallValue(1, source_label='Auto.hostedCopy') if installer else None",
			copied_owner.path,
			delayFrames=8
		)
		run(
			"comp = op(args[0]); comp.destroy() if comp is not None else None",
			self.ownerComp.path,
			delayFrames=2
		)
		self._trace("Family moved into Custom_families/Local: '{}' -> '{}'".format(
			self.ownerComp.path, copied_owner.path
		))
		return True

	def _install_host_from_repo(self):
		"""Bootstrap Custom_families when it isn't installed yet by downloading
		the plugin .tox from GitHub and loading it under /ui/Plugins.

		Replaces the legacy embedded-host path (which required every family
		to ship a full copy of the plugin under its Embeded/ folder). The
		family no longer needs the embedded payload — only network access
		on the very first install. Subsequent family imports skip this
		path because plugins_root.op(Custom_families) already exists.
		"""
		plugins_root = self._get_or_create_plugins_root()
		if plugins_root is None:
			self._trace("Plugins root could not be created under /ui")
			return None

		host = plugins_root.op(self.CUSTOM_FAMILIES_MANAGER_NAME)
		if host is None:
			tox_path = os.path.join(
				app.preferencesFolder,
				'Custom families',
				self.BOOTSTRAP_TOX_TEMP_NAME,
			)
			try:
				os.makedirs(os.path.dirname(tox_path), exist_ok=True)
			except Exception:
				pass

			self._show_message('Downloading Custom_families plugin...')
			try:
				self._download_bootstrap_tox(self.BOOTSTRAP_TOX_URL, tox_path)
			except Exception as exc:
				self._trace("Bootstrap download failed: {}: {}".format(type(exc).__name__, exc))
				self._show_message('Custom_families download failed — check your internet connection.')
				return None

			self._show_message('Custom families host installation started')
			try:
				host = plugins_root.loadTox(tox_path)
			except Exception as exc:
				self._trace("loadTox failed for '{}': {}".format(tox_path, exc))
				self._show_message('Failed to load Custom_families.tox.')
				return None

			if host is None:
				self._trace("loadTox returned None for '{}'".format(tox_path))
				return None

			try:
				if host.name != self.CUSTOM_FAMILIES_MANAGER_NAME:
					host.name = self.CUSTOM_FAMILIES_MANAGER_NAME
			except Exception:
				pass

			try:
				os.remove(tox_path)
			except Exception:
				pass

		host.allowCooking = True
		# Do NOT set host.par.opshortcut here. We resolve Custom_families by
		# full path (CUSTOM_FAMILIES_MANAGER_PATH) on purpose to avoid global
		# name collisions with the embedded Custom_families still living inside
		# this family until the source copy is destroyed.

		# Reset stale install flags inherited from the embedded source. The
		# embedded Custom_families inside this family may carry baked-in state
		# from prior testing (cf_install_complete=True, Installstate=1). If we
		# leave them as-is, the chopexec1 -> Install.Run() chain hits the
		# install-complete guard and silently returns: Installstate stays at 1
		# but no toolbar/watcher/injects are actually installed.
		try:
			host.store(self.CUSTOM_FAMILIES_INSTALL_COMPLETE_KEY, False)
		except Exception:
			pass
		try:
			state_par = getattr(host.par, 'Installstate', None)
			if state_par is not None:
				state_par.val = 0
		except Exception:
			pass

		# Pulse the Install button on Custom_families. The host's chopexec1
		# inside its Installer COMP listens for this pulse and calls
		# parent().ext.Install.Run(), which kicks off the structural install
		# (split, panel change, watcher inject, dialog inject, ...).
		try:
			install_par = getattr(host.par, 'Install', None)
			if install_par is not None:
				install_par.pulse()
		except Exception:
			pass

		self._trace("Custom_families host installed at '{}', state reset and Install pulse fired".format(host.path))
		return host

	def _download_bootstrap_tox(self, url, dest_path):
		"""Stream the Custom_families plugin .tox from GitHub to disk.

		Mirrors the SSL/User-Agent handling in Installer/Install._download_zip:
		TD's embedded Python ships without a CA bundle, so the default verified
		context fails on github.com. We try verified first and fall back to an
		unverified context only on SSL errors. The User-Agent header avoids
		GitHub 403s on 'unknown client'.
		"""
		req = urllib.request.Request(
			url,
			headers={'User-Agent': 'Custom_families-family-bootstrap'},
		)
		try:
			response = urllib.request.urlopen(req, timeout=30)
		except (ssl.SSLError, urllib.error.URLError) as ssl_exc:
			is_ssl = isinstance(ssl_exc, ssl.SSLError) or (
				isinstance(ssl_exc, urllib.error.URLError)
				and isinstance(ssl_exc.reason, ssl.SSLError)
			)
			if not is_ssl:
				raise
			self._trace("Bootstrap SSL verification failed, retrying unverified: {}".format(ssl_exc))
			ctx = ssl._create_unverified_context()
			response = urllib.request.urlopen(req, timeout=30, context=ctx)

		with response, open(dest_path, 'wb') as out:
			while True:
				chunk = response.read(64 * 1024)
				if not chunk:
					break
				out.write(chunk)

	def _schedule_wait_for_host_then_move(self, host, delay_frames=20):
		run(
			"owner = op(args[0]); host = op(args[1]); "
			"ext_ns = getattr(owner, 'ext', None) if owner is not None else None; "
			"installer = (getattr(owner, 'InstallerEXT', None) or getattr(owner, 'GenericInstallerEXT', None) or "
			"getattr(ext_ns, 'InstallerEXT', None) or getattr(ext_ns, 'GenericInstallerEXT', None)) if owner is not None else None; "
			"installer._poll_host_then_move(host) if installer is not None else None",
			self.ownerComp.path,
			host.path,
			delayFrames=delay_frames
		)

	def _poll_host_then_move(self, host):
		if host is None or not host.valid:
			self._trace("Host disappeared while waiting for Installstate=1")
			return

		state_par = getattr(host.par, 'Installstate', None)
		state_val = int(state_par.eval()) if state_par is not None else 0

		if state_val != 1:
			self._schedule_wait_for_host_then_move(host)
			return

		cf_local = host.op('Local')
		if cf_local is None:
			self._trace("Host installed but Local missing on '{}'".format(host.path))
			return

		self._move_family_to_local(cf_local)

	def _is_system_subtree_member(self, candidate):
		if candidate is None:
			return False

		try:
			candidate_path = str(candidate.path).rstrip('/')
		except Exception:
			return False

		if not candidate_path:
			return False

		for system_root in ('/ui', '/sys', '/local'):
			if candidate_path == system_root or candidate_path.startswith(system_root + '/'):
				return True

		return False

	def _is_owner_subtree_member(self, candidate):
		if candidate is None:
			return False

		try:
			if candidate == self.ownerComp:
				return True
		except Exception:
			pass

		try:
			owner_path = self.ownerComp.path.rstrip('/')
			candidate_path = candidate.path.rstrip('/')
			if not owner_path or not candidate_path:
				return False
			return candidate_path.startswith(owner_path + '/')
		except Exception:
			return False

	def _iter_main_root_components(self):
		main_root = self._get_main_root()
		if main_root is None:
			return []

		found = []
		seen = set()

		try:
			root_path = main_root.path
		except Exception:
			root_path = ''

		if root_path:
			seen.add(root_path)
		found.append(main_root)

		try:
			candidates = main_root.findChildren(maxDepth=100)
		except Exception:
			candidates = []

		for candidate in candidates:
			if candidate is None:
				continue

			if self._is_system_subtree_member(candidate):
				continue

			try:
				if not getattr(candidate, 'isCOMP', False):
					continue
			except Exception:
				continue

			try:
				candidate_path = candidate.path
			except Exception:
				candidate_path = str(candidate)

			if candidate_path in seen:
				continue

			seen.add(candidate_path)
			found.append(candidate)

		return found

	def _family_identity_of_op(self, candidate):
		op_name = ''
		op_shortcut = ''

		try:
			op_name = self._sanitize_family_name(candidate.name)
		except Exception:
			pass

		try:
			if hasattr(candidate, 'par') and hasattr(candidate.par, 'opshortcut'):
				try:
					op_shortcut = self._sanitize_family_name(candidate.par.opshortcut.eval())
				except Exception:
					op_shortcut = self._sanitize_family_name(candidate.par.opshortcut)
		except Exception:
			pass

		return op_name, op_shortcut

	def _family_compare_key(self, name):
		name = self._sanitize_family_name(name)
		if not name:
			return ''
		match = re.match(r'^(.*?)(\d+)$', name)
		if match:
			base_name = self._sanitize_family_name(match.group(1))
			if base_name:
				return base_name
		return name

	def _split_family_suffix_digits(self, name):
		name = self._sanitize_family_name(name)
		if not name:
			return '', ''

		match = re.match(r'^(.*?)(\d+)$', name)
		if not match:
			return name, ''

		base_name = self._sanitize_family_name(match.group(1))
		suffix = str(match.group(2) or '').strip()
		return base_name or name, suffix

	def _find_existing_family_owners_by_exact_identity(self, family_name):
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return []

		found = []
		seen = set()

		for candidate in self._iter_main_root_components():
			if candidate is None:
				continue

			if self._is_owner_subtree_member(candidate):
				continue

			try:
				if not getattr(candidate, 'isCOMP', False):
					continue
			except Exception:
				pass

			candidate_name, candidate_shortcut = self._family_identity_of_op(candidate)
			candidate_name = self._sanitize_family_name(candidate_name)
			candidate_shortcut = self._sanitize_family_name(candidate_shortcut)
			if family_name not in (candidate_name, candidate_shortcut):
				continue

			try:
				candidate_path = candidate.path
			except Exception:
				candidate_path = str(candidate)

			if candidate_path in seen:
				continue

			seen.add(candidate_path)
			found.append(candidate)

		return found

	def _resolve_canonical_family_name(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return ''
		return family_name

	def _apply_canonical_family_name(self, family_name):
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return False

		changed = False

		try:
			if str(self.ownerComp.name).strip() != family_name:
				self.ownerComp.name = family_name
				changed = True
		except Exception as e:
			self._trace("Canonical rename failed on '{}': {}".format(self.ownerComp.path, e))

		try:
			current_shortcut = ''
			if hasattr(self.ownerComp.par, 'opshortcut'):
				try:
					current_shortcut = self._sanitize_family_name(self.ownerComp.par.opshortcut.eval())
				except Exception:
					current_shortcut = self._sanitize_family_name(self.ownerComp.par.opshortcut)
			if current_shortcut != family_name:
				self.ownerComp.par.opshortcut = family_name
				changed = True
		except Exception as e:
			self._trace("Canonical opshortcut update failed on '{}': {}".format(self.ownerComp.path, e))

		self.family_name = family_name
		return changed

	def _find_existing_family_owners(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []

		exact_matches = self._find_existing_family_owners_by_exact_identity(family_name)
		if exact_matches:
			return exact_matches

		return []

	def _replace_existing_family_owners(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return False

		replaced_any = False

		for existing_op in self._find_existing_family_owners(family_name):
			try:
				self._trace("Replacing existing installer '{}' for family '{}'".format(
					existing_op.path,
					family_name,
				))
			except Exception:
				pass

			removed = self._request_family_remove(family_name=family_name, comp=existing_op)
			if not removed:
				try:
					self._request_family_ui_cleanup(family_name=family_name, comp=existing_op)
				except Exception:
					pass
				try:
					if getattr(existing_op, 'valid', True):
						existing_op.destroy()
				except Exception as e:
					self._trace("Existing installer destroy failed for '{}': {}".format(
						getattr(existing_op, 'path', existing_op),
						e,
					))
					continue

			replaced_any = True

		if replaced_any:
			self._trace("Existing installers replaced for family '{}'".format(family_name))

		return replaced_any

	def _destroy_existing_family_owners_only(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return False

		destroyed_any = False

		for existing_op in self._find_existing_family_owners(family_name):
			try:
				self._request_family_ui_cleanup(family_name=family_name, comp=existing_op)
			except Exception:
				pass
			try:
				if getattr(existing_op, 'valid', True):
					existing_op.destroy()
					destroyed_any = True
			except Exception:
				pass

		return destroyed_any

	def _clone_name(self, function_name, family_name=None):
		family_name = family_name or self.family_name
		return "{}_{}".format(function_name, family_name)

	def _button_shortcut_name(self, family_name=None):
		family_name = family_name or self.family_name
		return "{}_button".format(family_name)

	def _bookmark_toggle_name(self, family_name=None):
		return self._clone_name('button', family_name)

	def _watcher_name(self, family_name=None):
		return self._clone_name('watcher', family_name)

	def _bookmark_toggle_names(self, family_name=None):
		family_name = family_name or self.family_name
		names = [
			self._bookmark_toggle_name(family_name),
			"{}_toggle".format(family_name),
			"{}_button".format(family_name),
		]

		family_key = self._sanitize_family_name(family_name)
		if family_key and family_key != 'Custom':
			names.append("{}".format(family_name))

		return names

	def _find_toggle_by_owner_path(self, bookmark_bar):
		"""Scan bookmark_bar for a toggle whose stored cf_owner_path matches ownerComp.
		Used during rename to find the old-named button that lookup-by-name misses."""
		if bookmark_bar is None:
			return None
		try:
			owner_path = self.ownerComp.path
		except Exception:
			return None
		if not owner_path:
			return None
		try:
			children = bookmark_bar.findChildren(depth=None, maxDepth=1)
		except Exception:
			return None
		for child in children:
			if child is None:
				continue
			try:
				if child.fetch('cf_owner_path', '') == owner_path:
					return child
			except Exception:
				pass
		return None

	def _find_watcher_by_owner_path(self, bookmark_bar):
		"""Scan bookmark_bar for a watcher this family installed (by cf_owner_path).
		Used during rename to find the old-named watcher for in-place rename."""
		if bookmark_bar is None:
			return None
		try:
			owner_path = self.ownerComp.path
		except Exception:
			return None
		if not owner_path:
			return None
		try:
			children = bookmark_bar.findChildren(depth=None, maxDepth=1)
		except Exception:
			return None
		watcher_prefix = 'watcher_'
		for child in children:
			if child is None:
				continue
			try:
				if not child.name.startswith(watcher_prefix):
					continue
				if child.fetch('cf_owner_path', '') == owner_path:
					return child
			except Exception:
				pass
		return None

	def _delete_execute_name(self, family_name=None):
		return self._clone_name('delete_execute', family_name)

	def _delete_execute_names(self, family_name=None):
		family_name = family_name or self.family_name
		return [
			self._delete_execute_name(family_name),
			"{}_delete_execute".format(family_name),
			"Delete_op_execute",
		]

	def _bookmark_family_key_from_name(self, op_name):
		op_name = self._sanitize_family_name(op_name)
		if not op_name:
			return ''

		for prefix in ('button_', 'delete_execute_', 'watcher_'):
			if op_name.startswith(prefix):
				return self._sanitize_family_name(op_name[len(prefix):])

		if op_name.endswith('_button'):
			return self._sanitize_family_name(op_name[:-len('_button')])

		if op_name.endswith('_toggle'):
			return self._sanitize_family_name(op_name[:-len('_toggle')])

		return self._sanitize_family_name(op_name)

	def _ui_clone_family_key_from_name(self, op_name):
		op_name = self._sanitize_family_name(op_name)
		if not op_name:
			return '', ''

		prefix_map = (
			('button_', 'toggle'),
			('delete_execute_', 'delete_execute'),
			('watcher_', 'watcher'),
			('insert_', 'insert'),
			('panel_execute_', 'panel_execute'),
			('inject_', 'inject'),
		)

		for prefix, clone_type in prefix_map:
			if op_name.startswith(prefix):
				family_part = op_name[len(prefix):]
				if clone_type == 'inject' and family_part.endswith('_fam'):
					family_part = family_part[:-len('_fam')]
				return self._sanitize_family_name(family_part), clone_type

		suffix_map = (
			('_button', 'toggle'),
			('_toggle', 'toggle'),
			('_delete_execute', 'delete_execute'),
			('_watcher', 'watcher'),
			('_insert', 'insert'),
			('_panel_execute', 'panel_execute'),
		)

		for suffix, clone_type in suffix_map:
			if op_name.endswith(suffix):
				return self._sanitize_family_name(op_name[:-len(suffix)]), clone_type

		return self._sanitize_family_name(op_name), ''

	def _destroy_bookmark_family_ops(self, *family_names):
		bookmark_bar = self._ui('bookmark_bar')
		if bookmark_bar is None:
			return 0

		family_keys = set()
		for family_name in family_names:
			family_key = self._sanitize_family_name(family_name)
			if family_key:
				family_keys.add(family_key)

		if not family_keys:
			return 0

		removed = 0
		try:
			candidates = bookmark_bar.findChildren(depth=None, maxDepth=2)
		except Exception:
			candidates = []

		for candidate in candidates:
			if candidate is None:
				continue

			try:
				candidate_name = str(candidate.name)
			except Exception:
				continue

			candidate_key = self._bookmark_family_key_from_name(candidate_name)
			if candidate_key not in family_keys:
				continue

			if self._safe_destroy(candidate):
				removed += 1

		if removed:
			self._trace("Bookmark cleanup by family keys {} removed={}".format(
				sorted(family_keys),
				removed,
			))
		return removed

	def _destroy_ui_family_ops(self, *family_names, destroy_toggle=False):
		family_keys = set()
		for family_name in family_names:
			family_key = self._sanitize_family_name(family_name)
			if family_key:
				family_keys.add(family_key)

		if not family_keys:
			return 0

		roots = [
			self._ui('bookmark_bar'),
			self._ui('menu_op'),
			self._ui('node_table'),
		]

		preserved_types = set()
		if not destroy_toggle:
			preserved_types.update(('toggle', 'delete_execute'))

		removed = 0
		seen = set()

		for root in roots:
			if root is None:
				continue

			try:
				candidates = root.findChildren(depth=None, maxDepth=4)
			except Exception:
				candidates = []

			for candidate in candidates:
				if candidate is None:
					continue

				try:
					candidate_path = str(candidate.path)
					candidate_name = str(candidate.name)
				except Exception:
					continue

				if candidate_path in seen:
					continue

				candidate_key, clone_type = self._ui_clone_family_key_from_name(candidate_name)
				if candidate_key not in family_keys:
					continue

				if clone_type in preserved_types:
					continue

				seen.add(candidate_path)
				if self._safe_destroy(candidate):
					removed += 1

		if removed:
			self._trace("UI family cleanup by keys {} removed={} destroy_toggle={}".format(
				sorted(family_keys),
				removed,
				destroy_toggle,
			))
		return removed

	def _inject_op_name(self, family_name=None):
		return self._clone_name('inject', family_name)

	def _inject_op_names(self, family_name=None):
		family_name = family_name or self.family_name
		return [self._inject_op_name(family_name), "inject_{}_fam".format(family_name)]

	def _panel_execute_name(self, family_name=None):
		return self._clone_name('panel_execute', family_name)

	def _panel_execute_names(self, family_name=None):
		family_name = family_name or self.family_name
		return [self._panel_execute_name(family_name), "{}_panel_execute".format(family_name)]

	def _family_insert_name(self, family_name=None):
		return self._clone_name('insert', family_name)

	def _family_insert_names(self, family_name=None):
		family_name = family_name or self.family_name
		return [self._family_insert_name(family_name), "{}_insert".format(family_name)]

	def _family_residue_names(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return set()
		names = set()
		for group in (
			[name for name in self._family_insert_names(family_name) if name != family_name],
			self._panel_execute_names(family_name),
			self._inject_op_names(family_name),
			[
				self._bookmark_toggle_name(family_name),
				"{}_toggle".format(family_name),
				"{}_button".format(family_name),
				self._watcher_name(family_name),
				"{}_watcher".format(family_name),
			],
			self._delete_execute_names(family_name),
		):
			for name in group:
				name = self._sanitize_family_name(name)
				if name:
					names.add(name)
		return names

	def _safe_destroy(self, o):
		if o is None:
			return
		try:
			o.allowCooking = False
		except Exception:
			pass
		try:
			o.destroy()
		except Exception as e:
			try:
				obj_path = o.path
			except Exception:
				obj_path = str(o)
			self._trace("_safe_destroy failed {} -> {}".format(obj_path, e), showMessage=True)
			debug("Destroy failed for {}: {}".format(o, e))

	def _find_family_residue_ops(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return []
		target_names = self._family_residue_names(family_name)
		if not target_names:
			return []

		roots = [
			self._ui('menu_op'),
			self._ui('node_table'),
			self._ui('bookmark_bar'),
		]
		found = []
		seen = set()

		for root in roots:
			if root is None:
				continue
			try:
				candidates = root.findChildren(depth=None, maxDepth=4)
			except Exception:
				candidates = []

			for candidate in candidates:
				if candidate is None:
					continue
				try:
					name = str(candidate.name)
					path = str(candidate.path)
				except Exception:
					continue

				if name not in target_names:
					continue

				if path in seen:
					continue

				seen.add(path)
				found.append(candidate)

		found.sort(key=lambda item: len(getattr(item, 'path', '')), reverse=True)
		return found

	def _destroy_family_residues(self, family_name=None, destroy_toggle=False):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		removed = 0
		preserved_names = set()
		if not destroy_toggle:
			preserved_names.update(self._bookmark_toggle_names(family_name))
			preserved_names.update(self._delete_execute_names(family_name))
		for residue in self._find_family_residue_ops(family_name):
			if residue is None:
				continue
			try:
				residue_name = str(residue.name)
			except Exception:
				residue_name = ''
			if residue_name in preserved_names:
				continue
			if self._safe_destroy(residue):
				removed += 1
		self._trace(
			"Residue cleanup for '{}': removed={} destroy_toggle={}".format(
				family_name,
				removed,
				destroy_toggle,
			)
		)
		return removed

	def _find_child_by_names(self, parent_op, candidate_names):
		if parent_op is None:
			return None

		for name in candidate_names:
			try:
				o = parent_op.op(name)
				if o is not None:
					return o
			except Exception:
				pass

		return None

	def _compatible_types_expr(self, compatible_types=None):
		types_list = compatible_types if compatible_types is not None else self.compatible_types
		if not types_list:
			return "False"
		return ' or '.join(["menu_type=='{}'".format(t) for t in types_list])

	def _get_linked_component_ext(self):
		try:
			for attr_name in ('Component', 'ComponentEXT', 'component', 'componentExt'):
				ext = getattr(self.ownerComp, attr_name, None)
				if ext is not None:
					return ext
		except Exception:
			pass
		return None

	def _sanitize_family_name(self, name):
		name = '' if name is None else str(name).strip()
		if not name:
			return ''

		linked_ext = self._get_linked_component_ext()
		if linked_ext is not None and hasattr(linked_ext, 'SanitizePluginName'):
			try:
				return linked_ext.SanitizePluginName(name)
			except Exception as e:
				debug("Errore sanitizzando family name via ComponentEXT: {}".format(e))

		name = name.replace(' ', '')
		name = re.sub(r'[^A-Za-z0-9_]', '', name)
		if name and name[0].isdigit():
			name = '_' + name
		return name

	def _get_family_identity(self):
		family_name = ''
		global_shortcut = ''
		owner_name = ''

		try:
			owner_name = self._sanitize_family_name(self.ownerComp.name)
		except Exception:
			owner_name = ''

		linked_ext = self._get_linked_component_ext()

		if linked_ext is not None:
			try:
				if hasattr(linked_ext, 'GetGlobalShortcut'):
					global_shortcut = str(linked_ext.GetGlobalShortcut()).strip()
				else:
					global_shortcut = str(linked_ext.Global_op_shortcut).strip()
			except Exception:
				pass

			try:
				if hasattr(linked_ext, 'SanitizePluginName') and not global_shortcut:
					raw_name = self.ownerComp.par.opshortcut.eval()
					global_shortcut = linked_ext.SanitizePluginName(raw_name)
			except Exception as e:
				debug("Errore leggendo Global_op_shortcut dall'extension collegata: {}".format(e))

		if not global_shortcut:
			for attr_name in ('Global_op_shortcut', 'global_op_shortcut'):
				try:
					global_shortcut = str(getattr(self.ownerComp, attr_name)).strip()
					if global_shortcut:
						break
				except Exception:
					pass

		if not global_shortcut:
			try:
				global_shortcut = str(self.ownerComp.par.opshortcut.eval()).strip()
			except Exception:
				pass

		if not global_shortcut:
			global_shortcut = str(self.ownerComp.name).strip()

		global_shortcut = self._sanitize_family_name(global_shortcut)
		family_name = owner_name or global_shortcut
		return family_name, global_shortcut

	def _sync_family_name(self, apply_owner_shortcut=False):
		family_name, global_shortcut = self._get_family_identity()
		if family_name:
			self.family_name = family_name

		if apply_owner_shortcut and family_name:
			self._set_owner_shortcut(family_name)

		return family_name, global_shortcut

	def _get_global_custom_operators_path(self):
		search_paths = [
			'custom_operators',
			'./custom_operators',
			'../custom_operators',
			'../../custom_operators',
		]

		for rel_path in search_paths:
			try:
				o = self.ownerComp.op(rel_path)
				if o is not None:
					return o.path
			except Exception:
				pass

		try:
			p = self.ownerComp.parent()
			depth = 0
			while p is not None and depth < 6:
				try:
					o = p.op('custom_operators')
					if o is not None:
						return o.path
				except Exception:
					pass

				try:
					p = p.parent()
				except Exception:
					p = None

				depth += 1
		except Exception as e:
			debug("Errore cercando global custom_operators path: {}".format(e))

		return ''

	def _set_script_variable(self, dat_op, var_name, value):
		if dat_op is None:
			return False

		try:
			text = dat_op.text
			pattern = r"(?m)^{}\s*=\s*.*$".format(re.escape(var_name))
			replacement = "{} = {!r}".format(var_name, value)
			new_text, count = re.subn(pattern, replacement, text)

			if count > 0:
				dat_op.text = new_text
				return True

			debug("Variabile '{}' non trovata in {}".format(var_name, dat_op.path))
		except Exception as e:
			debug("Errore aggiornando variabile '{}' in {}: {}".format(var_name, dat_op.path, e))

		return False

	def _get_custom_operator_root(self):
		custom_ops_path = self._get_global_custom_operators_path()
		if not custom_ops_path:
			return None

		try:
			root = op(custom_ops_path)
		except Exception:
			return None

		self._ensure_custom_operator_storage_state(root)
		return root

	def _ensure_custom_operator_storage_state(self, root=None):
		if root is None:
			custom_ops_path = self._get_global_custom_operators_path()
			if not custom_ops_path:
				return False
			try:
				root = op(custom_ops_path)
			except Exception:
				root = None
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

	def _is_custom_operator_template(self, operator_comp):
		if operator_comp is None:
			return False

		root = self._get_custom_operator_root()
		if root is None:
			return False

		try:
			return operator_comp.parent == root
		except Exception:
			return False

	def _apply_custom_operator_template_storage_state(self, operator_comp):
		if operator_comp is None or not self._is_custom_operator_template(operator_comp):
			return False

		try:
			operator_comp.allowCooking = False
		except Exception:
			pass

		try:
			operator_comp.bypass = True
		except Exception:
			pass

		try:
			if hasattr(operator_comp, 'par') and hasattr(operator_comp.par, 'bypass'):
				operator_comp.par.bypass = 1
		except Exception:
			pass

		return True

	def _iter_custom_operator_templates(self):
		root = self._get_custom_operator_root()
		if root is None:
			return []

		templates = []
		for child in getattr(root, 'children', []):
			try:
				if child.isCOMP:
					templates.append(child)
			except Exception:
				pass
		return templates

	def _custom_comp_runner_name(self, family_name=None, operator_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		operator_name = self._sanitize_family_name(operator_name)
		if not family_name or not operator_name:
			return ''
		return '{}_{}_{}'.format(self.CUSTOM_COMP_RUNNER_PREFIX, family_name, operator_name)

	def _iter_custom_comp_runner_defs(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		runner_defs = []
		for operator_comp in self._iter_custom_operator_templates():
			try:
				operator_name = str(operator_comp.name).strip()
			except Exception:
				operator_name = ''
			try:
				source_path = str(operator_comp.path).strip()
			except Exception:
				source_path = ''
			runner_name = self._custom_comp_runner_name(family_name, operator_name)
			if runner_name and operator_name and source_path:
				runner_defs.append((runner_name, operator_name, source_path))
		return runner_defs

	def _build_custom_comp_runner_text(self, operator_name, source_path):
		source_path = str(source_path or '').strip()
		return '\n'.join([
			self.CUSTOM_COMP_RUNNER_MARKER,
			"#USAGE {} pane".format(self._sanitize_family_name(operator_name)),
			'args pane',
			'',
			'set panepath = `arg(execute("desk -l 3 $pane"),1)`',
			'if(`opexists("$panepath")` == 0)',
			'\texit',
			'endif',
			'',
			'set newnode = `execute("opcp -v {} $panepath/")`'.format(source_path),
			'if("$newnode" == "")',
			'\texit',
			'endif',
			'',
			'set newpath = $panepath/$newnode',
			'opplace -n "undo" -p $pane $newpath',
			'',
		])

	def _cleanup_custom_comp_runners(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		custom_comps = self._ui('custom_comps')
		if custom_comps is None or not family_name:
			return 0

		prefix = '{}_{}_'.format(self.CUSTOM_COMP_RUNNER_PREFIX, family_name)
		removed = 0
		for child in list(getattr(custom_comps, 'children', [])):
			try:
				name = str(child.name)
			except Exception:
				name = ''
			if not name.startswith(prefix):
				continue
			if self._safe_destroy(child):
				removed += 1
		return removed

	def _has_custom_comp_runners(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		custom_comps = self._ui('custom_comps')
		if custom_comps is None or not family_name:
			return False

		prefix = '{}_{}_'.format(self.CUSTOM_COMP_RUNNER_PREFIX, family_name)
		for child in getattr(custom_comps, 'children', []):
			try:
				name = str(child.name)
			except Exception:
				name = ''
			if name.startswith(prefix):
				return True
		return False

	def _install_custom_comp_runners(self):
		custom_comps = self._ui('custom_comps')
		if custom_comps is None:
			return 0

		installed = 0
		expected_names = set()
		for runner_name, operator_name, source_path in self._iter_custom_comp_runner_defs():
			expected_names.add(runner_name)
			try:
				runner_dat = custom_comps.op(runner_name)
			except Exception:
				runner_dat = None
			try:
				if runner_dat is None:
					runner_dat = custom_comps.create(textDAT, runner_name)
			except Exception as e:
				debug("Custom runner create failed '{}': {}".format(runner_name, e))
				continue
			if runner_dat is None:
				continue
			try:
				if hasattr(runner_dat.par, 'language'):
					runner_dat.par.language = 'tscript'
			except Exception:
				pass
			try:
				desired_text = self._build_custom_comp_runner_text(operator_name, source_path)
				if runner_dat.text != desired_text:
					runner_dat.text = desired_text
			except Exception as e:
				debug("Custom runner text failed '{}': {}".format(runner_name, e))
				continue
			installed += 1

		prefix = '{}_{}_'.format(self.CUSTOM_COMP_RUNNER_PREFIX, self._sanitize_family_name(self.family_name))
		for child in list(getattr(custom_comps, 'children', [])):
			try:
				name = str(child.name)
			except Exception:
				name = ''
			if not name.startswith(prefix):
				continue
			if name not in expected_names:
				self._safe_destroy(child)

		self._trace("Installed native custom runners for '{}' count={}".format(self.family_name, installed))
		return installed

	def _cleanup_legacy_panel_execute(self, menu_op=None, family_name=None):
		menu_op = menu_op or self._ui('menu_op')
		family_name = family_name or self.family_name
		if menu_op is None:
			return False
		legacy = self._find_child_by_names(menu_op, self._panel_execute_names(family_name))
		if legacy is None:
			return False
		return self._safe_destroy(legacy)

	def _is_extension_script_dat(self, dat_op):
		if dat_op is None or not hasattr(dat_op, 'text'):
			return False

		try:
			text = str(dat_op.text or '')
		except Exception:
			return False

		if not text:
			return False

		if self.CUSTOM_OPERATOR_LINK_START in text and self.CUSTOM_OPERATOR_LINK_END in text:
			return True

		signature_hits = 0
		for signature in self.CUSTOM_OPERATOR_EXTENSION_SIGNATURES:
			if signature in text:
				signature_hits += 1

		return 'class ' in text and signature_hits >= 2

	def _build_custom_operator_link_block(self, operator_comp):
		operator_name = ''
		try:
			operator_name = str(operator_comp.name).strip()
		except Exception:
			operator_name = ''

		family_name = self._sanitize_family_name(self.family_name)
		owner_path = getattr(self.ownerComp, 'path', '')
		owner_shortcut = ''
		try:
			owner_shortcut = str(self.ownerComp.par.opshortcut.eval()).strip()
		except Exception:
			owner_shortcut = family_name

		lines = [
			self.CUSTOM_OPERATOR_LINK_START,
			"FAMILY_OWNER_PATH = {!r}".format(owner_path),
			"FAMILY_OWNER_SHORTCUT = {!r}".format(owner_shortcut),
			"FAMILY_NAME = {!r}".format(family_name),
			"CUSTOM_OPERATOR_NAME = {!r}".format(operator_name),
			'',
			'def get_family_owner():',
			'\tcomp = None',
			'\ttry:',
			'\t\tcomp = op(FAMILY_OWNER_PATH)',
			'\texcept Exception:',
			'\t\tcomp = None',
			'\tif comp is None and FAMILY_OWNER_SHORTCUT:',
			'\t\ttry:',
			'\t\t\tcomp = getattr(op, FAMILY_OWNER_SHORTCUT, None)',
			'\t\texcept Exception:',
			'\t\t\tcomp = None',
			'\treturn comp',
			'',
			'def get_family_component_ext():',
			'\tcomp = get_family_owner()',
			'\tif comp is None:',
			'\t\treturn None',
			'\tfor attr_name in ("ComponentEXT", "componentExt"):',
			'\t\ttry:',
			'\t\t\text_obj = getattr(comp, attr_name, None)',
			'\t\t\tif ext_obj is not None:',
			'\t\t\t\treturn ext_obj',
			'\t\texcept Exception:',
			'\t\t\tpass',
			'\ttry:',
			'\t\tnamespace = getattr(comp, "ext", None)',
			'\texcept Exception:',
			'\t\tnamespace = None',
			'\tif namespace is not None:',
			'\t\tfor attr_name in ("ComponentEXT", "componentExt"):',
			'\t\t\ttry:',
			'\t\t\t\text_obj = getattr(namespace, attr_name, None)',
			'\t\t\t\tif ext_obj is not None:',
			'\t\t\t\t\treturn ext_obj',
			'\t\t\texcept Exception:',
			'\t\t\t\tpass',
			'\treturn None',
			self.CUSTOM_OPERATOR_LINK_END,
		]
		return '\n'.join(lines)

	def _replace_managed_block(self, text, block):
		pattern = r'(?s){}\n.*?\n{}\n?'.format(
			re.escape(self.CUSTOM_OPERATOR_LINK_START),
			re.escape(self.CUSTOM_OPERATOR_LINK_END),
		)
		replacement = block.rstrip() + '\n'

		if re.search(pattern, text):
			return re.sub(pattern, replacement, text, count=1)

		if not text:
			return replacement

		return replacement + '\n' + text.lstrip('\n')

	def _get_custom_operator_runtime_parameter_names(self):
		par_names = []
		for par_name in self.CUSTOM_OPERATOR_RUNTIME_BASE_PARS:
			if par_name not in par_names:
				par_names.append(par_name)

		linked_ext = self._get_linked_component_ext()
		if linked_ext is None or not hasattr(linked_ext, 'ExtractReferenceAboutDefinition'):
			return par_names

		try:
			about_defs = linked_ext.ExtractReferenceAboutDefinition()
		except Exception:
			about_defs = None

		for par_def in about_defs or []:
			try:
				par_name = str(par_def.get('name', '')).strip()
			except Exception:
				par_name = ''
			if par_name and par_name not in par_names:
				par_names.append(par_name)

		return par_names

	def _build_custom_operator_runtime_execute_text(self, operator_comp):
		operator_name = ''
		try:
			operator_name = str(operator_comp.name).strip()
		except Exception:
			operator_name = ''

		family_name = self._sanitize_family_name(self.family_name)
		owner_path = getattr(self.ownerComp, 'path', '')
		owner_shortcut = ''
		try:
			owner_shortcut = str(self.ownerComp.par.opshortcut.eval()).strip()
		except Exception:
			owner_shortcut = family_name

		parameter_names = self._get_custom_operator_runtime_parameter_names()
		parameter_names_repr = repr(parameter_names)

		lines = [
			'"""Custom family runtime observer."""',
			'',
			"FAMILY_OWNER_PATH = {!r}".format(owner_path),
			"FAMILY_OWNER_SHORTCUT = {!r}".format(owner_shortcut),
			"FAMILY_NAME = {!r}".format(family_name),
			"CUSTOM_OPERATOR_NAME = {!r}".format(operator_name),
			"OBSERVED_PARAMETERS = {}".format(parameter_names_repr),
			'',
			'def _get_target_comp():',
			'\ttry:',
			'\t\treturn parent()',
			'\texcept Exception:',
			'\t\treturn None',
			'',
			'def _get_owner_comp():',
			'\tcomp = None',
			'\ttry:',
			'\t\tcomp = op(FAMILY_OWNER_PATH)',
			'\texcept Exception:',
			'\t\tcomp = None',
			'\tif comp is None and FAMILY_OWNER_SHORTCUT:',
			'\t\ttry:',
			'\t\t\tcomp = getattr(op, FAMILY_OWNER_SHORTCUT, None)',
			'\t\texcept Exception:',
			'\t\t\tcomp = None',
			'\treturn comp',
			'',
			'def _get_component_ext(owner):',
			'\tfor attr_name in ("ComponentEXT", "componentExt"):',
			'\t\ttry:',
			'\t\t\text_obj = getattr(owner, attr_name, None)',
			'\t\t\tif ext_obj is not None:',
			'\t\t\t\treturn ext_obj',
			'\t\texcept Exception:',
			'\t\t\tpass',
			'\ttry:',
			'\t\tnamespace = getattr(owner, "ext", None)',
			'\texcept Exception:',
			'\t\tnamespace = None',
			'\tif namespace is not None:',
			'\t\tfor attr_name in ("ComponentEXT", "componentExt"):',
			'\t\t\ttry:',
			'\t\t\t\text_obj = getattr(namespace, attr_name, None)',
			'\t\t\t\tif ext_obj is not None:',
			'\t\t\t\t\treturn ext_obj',
			'\t\t\texcept Exception:',
			'\t\t\t\tpass',
			'\treturn None',
			'',
			'def sync_owner_state():',
			'\ttarget = _get_target_comp()',
			'\towner = _get_owner_comp()',
			'\tif target is None or owner is None:',
			'\t\treturn',
			'\ttry:',
			'\t\ttarget.store("family_owner_path", FAMILY_OWNER_PATH)',
			'\t\ttarget.store("family_owner_shortcut", FAMILY_OWNER_SHORTCUT)',
			'\t\ttarget.store("family_name", FAMILY_NAME)',
			'\texcept Exception:',
			'\t\tpass',
			'\tcomponent_ext = _get_component_ext(owner)',
			'\tif component_ext is not None:',
			'\t\ttry:',
			'\t\t\trgb = component_ext.GetColorFromOwner()',
			'\t\texcept Exception:',
			'\t\t\trgb = None',
			'\t\tif rgb is not None:',
			'\t\t\ttry:',
			'\t\t\t\ttarget.color = rgb',
			'\t\t\texcept Exception:',
			'\t\t\t\ttry:',
			'\t\t\t\t\ttarget.par.color = rgb',
			'\t\t\t\texcept Exception:',
			'\t\t\t\t\tpass',
			'\t\ttry:',
			'\t\t\tabout_defs = component_ext.ExtractReferenceAboutDefinition()',
			'\t\t\tcomponent_ext.SyncAboutOnComp(target, about_defs)',
			'\t\texcept Exception:',
			'\t\t\tpass',
			'\ttry:',
			'\t\tversion = getattr(owner.par, "Version", None)',
			'\t\tif version is not None:',
			'\t\t\ttarget.store("family_version", str(version.eval()))',
			'\texcept Exception:',
			'\t\tpass',
			'\treturn',
			'',
			'def onValueChange(par, prev):',
			'\tsync_owner_state()',
			'\treturn',
			'',
			'def onValuesChanged(changes):',
			'\tsync_owner_state()',
			'\treturn',
		]
		return '\n'.join(lines)

	def _ensure_custom_operator_runtime_execute(self, operator_comp):
		if operator_comp is None:
			return False

		execute_dat = None
		try:
			execute_dat = operator_comp.op(self.CUSTOM_OPERATOR_RUNTIME_EXECUTE_NAME)
		except Exception:
			execute_dat = None

		try:
			if execute_dat is not None and not hasattr(execute_dat.par, 'pars'):
				execute_dat.destroy()
				execute_dat = None
		except Exception:
			execute_dat = None

		try:
			if execute_dat is None:
				execute_dat = operator_comp.create(parameterexecuteDAT, self.CUSTOM_OPERATOR_RUNTIME_EXECUTE_NAME)
		except Exception as e:
			debug("Custom operator runtime execute create failed on {}: {}".format(
				operator_comp.path if hasattr(operator_comp, 'path') else operator_comp,
				e,
			))
			return False

		try:
			execute_dat.text = self._build_custom_operator_runtime_execute_text(operator_comp)
		except Exception as e:
			debug("Custom operator runtime execute text failed on {}: {}".format(
				execute_dat.path if hasattr(execute_dat, 'path') else execute_dat,
				e,
			))
			return False

		observed_parameters = self._get_custom_operator_runtime_parameter_names()
		for par_name, value in (
			('active', True),
			('valuechange', True),
			('valueschanged', True),
			('custom', True),
			('builtin', True),
		):
			try:
				if hasattr(execute_dat.par, par_name):
					setattr(execute_dat.par, par_name, value)
			except Exception:
				pass

		try:
			if hasattr(execute_dat.par, 'op'):
				try:
					execute_dat.par.op.bindExpr = ''
				except Exception:
					pass
				execute_dat.par.op.expr = "parent(3).path"
		except Exception:
			pass

		try:
			if hasattr(execute_dat.par, 'pars'):
				execute_dat.par.pars = ' '.join(observed_parameters)
		except Exception:
			pass

		return True

	def NormalizeCustomOperatorRuntimeExecutes(self):
		updated = 0
		for operator_comp in self._iter_custom_operator_templates():
			try:
				if self._ensure_custom_operator_runtime_execute(operator_comp):
					updated += 1
			except Exception:
				pass
		self._trace("Normalized custom operator runtime executes for '{}' count={}".format(
			self.family_name,
			updated,
		))
		return updated

	def _sync_custom_operator_about(self, operator_comp):
		linked_ext = self._get_linked_component_ext()
		if linked_ext is None:
			return False

		if not hasattr(linked_ext, 'ExtractReferenceAboutDefinition') or not hasattr(linked_ext, 'SyncAboutOnComp'):
			return False

		try:
			about_defs = linked_ext.ExtractReferenceAboutDefinition()
			linked_ext.SyncAboutOnComp(operator_comp, about_defs)
			return True
		except Exception as e:
			debug("Custom operator about sync failed on {}: {}".format(
				operator_comp.path if hasattr(operator_comp, 'path') else operator_comp,
				e,
			))
			return False

	def PrepareCustomOperatorRuntimeLink(self, operator_comp):
		if operator_comp is None:
			return 0

		try:
			operator_comp.store('family_owner_path', self.ownerComp.path)
			operator_comp.store('family_owner_shortcut', self.family_name)
			operator_comp.store('family_name', self.family_name)
		except Exception:
			pass

		self._ensure_custom_operator_runtime_execute(operator_comp)

		block = self._build_custom_operator_link_block(operator_comp)
		updated_count = 0

		try:
			candidates = [operator_comp]
			candidates.extend(operator_comp.findChildren(maxDepth=2, includeUtility=True))
		except Exception:
			candidates = [operator_comp]

		seen = set()
		for candidate in candidates:
			try:
				candidate_path = candidate.path
			except Exception:
				candidate_path = str(id(candidate))

			if candidate_path in seen:
				continue
			seen.add(candidate_path)

			if not self._is_extension_script_dat(candidate):
				continue

			try:
				original_text = str(candidate.text or '')
				new_text = self._replace_managed_block(original_text, block)
				if new_text != original_text:
					candidate.text = new_text
				updated_count += 1
			except Exception as e:
				debug("Custom operator link update failed on {}: {}".format(
					candidate.path if hasattr(candidate, 'path') else candidate,
					e,
				))

		return updated_count

	def _apply_family_color_to_operator(self, operator_comp):
		if operator_comp is None:
			return 0

		updated_count = 0
		targets = [operator_comp]
		try:
			targets.extend(operator_comp.findChildren(maxDepth=6, includeUtility=True))
		except Exception:
			pass

		seen = set()
		for candidate in targets:
			try:
				candidate_path = candidate.path
			except Exception:
				candidate_path = str(id(candidate))

			if candidate_path in seen:
				continue
			seen.add(candidate_path)

			try:
				if tuple(candidate.color) != tuple(self.color):
					candidate.color = self.color
					updated_count += 1
					continue
			except Exception:
				pass

			try:
				color_par = getattr(candidate.par, 'color', None)
				if color_par is not None:
					current = tuple(color_par.eval())
					if current != tuple(self.color):
						candidate.par.color = self.color
						updated_count += 1
			except Exception:
				pass

		return updated_count

	def RefreshCustomOperatorTemplate(self, operator_comp):
		link_updates = self.PrepareCustomOperatorRuntimeLink(operator_comp)
		color_updates = self._apply_family_color_to_operator(operator_comp)
		about_updated = self._sync_custom_operator_about(operator_comp)
		self._apply_custom_operator_template_storage_state(operator_comp)
		return {
			'link_updates': link_updates,
			'color_updates': color_updates,
			'about_updated': about_updated,
		}

	def _prepare_custom_operator_templates(self):
		self._ensure_custom_operator_storage_state()
		updated_templates = 0
		updated_colors = 0
		for operator_comp in self._iter_custom_operator_templates():
			result = self.RefreshCustomOperatorTemplate(operator_comp)
			updated_templates += int(result.get('link_updates', 0))
			updated_colors += int(result.get('color_updates', 0))

		self._trace("Prepared custom operator extension templates for '{}' updated_dats={} updated_colors={}".format(
			self.family_name,
			updated_templates,
			updated_colors,
		))
		return updated_templates or updated_colors

	def _prepare_fam_script_callbacks_template(self):
		callbacks_dat = self._script('fam_script_callbacks')
		if callbacks_dat is None:
			debug("fam_script_callbacks non trovato, skip prepare template")
			return False

		self._trace("Prepared fam_script_callbacks template for '{}' without rewriting shared file".format(
			self.family_name
		))
		return True

	def _prepare_fam_panel_execute_template(self):
		panel_execute_dat = self._script('fam_panel_execute')
		if panel_execute_dat is None:
			debug("fam_panel_execute non trovato, skip prepare template")
			return False

		self._trace("Prepared panel execute template for '{}' without rewriting shared file".format(
			self.family_name
		))
		return True

	def _prepare_fam_toggle_template(self):
		fam_toggle = self._script('fam_toggle')
		if fam_toggle is None:
			return False

		family_name, _ = self._sync_family_name(apply_owner_shortcut=False)
		family_name = family_name or self.family_name
		updated = False

		try:
			if hasattr(fam_toggle.par, 'opshortcut'):
				fam_toggle.par.opshortcut = ''
				updated = True
		except Exception as e:
			debug("Toggle template opshortcut update failed: {}".format(e))

		try:
			for text_op in (
				fam_toggle.op('text'),
				fam_toggle.op('button/text1'),
				fam_toggle.op('text1'),
			):
				if text_op is not None and hasattr(text_op, 'par') and hasattr(text_op.par, 'text'):
					text_op.par.text = family_name
					updated = True
					break
		except Exception as e:
			debug("Toggle button text update failed: {}".format(e))

		try:
			if self._prepare_bookmark_toggle_visuals(fam_toggle):
				updated = True
		except Exception as e:
			debug("Toggle template visual prep failed: {}".format(e))

		try:
			try:
				fam_toggle.par.value0.expr = ''
			except Exception:
				pass
			fam_toggle.par.value0.bindExpr = 'parent(2).par.Selected'
			updated = True
		except Exception as e:
			debug("Toggle template value0 bindExpr failed: {}".format(e))

		try:
			panelexec2 = (
				fam_toggle.op('panelexec1') or
				fam_toggle.op('panelexec2')
			)
			script_path = ''
			for root_dir in self._get_component_root_candidates():
				for folder, fname in (
					('Ui_inject/button_Custom', 'panelexec1.py'),
					('button_Custom', 'panelexec1.py'),
					('Family_toggle_button', 'panelexec2.py'),
				):
					candidate = os.path.join(root_dir, folder, fname)
					try:
						if os.path.isfile(candidate):
							script_path = candidate
							break
					except Exception:
						pass
				if script_path:
					break

			if panelexec2 is not None and script_path:
				if hasattr(panelexec2.par, 'file'):
					panelexec2.par.file = script_path
				if hasattr(panelexec2.par, 'syncfile'):
					panelexec2.par.syncfile = True
				self._configure_toggle_context_execute(panelexec2)
				updated = True
		except Exception as e:
			debug("Toggle template panelexec sync failed: {}".format(e))

		try:
			fam_toggle.store('cf_owner_path', self.ownerComp.path)
			fam_toggle.store('cf_family_name', family_name)
			updated = True
		except Exception:
			pass

		self._trace("Prepared toggle template for '{}' with local opshortcut cleared and clone opshortcut '{}'".format(
			family_name,
			self._button_shortcut_name(family_name)
		))

		return updated

	def _apply_bookmark_toggle_label(self, toggle, family_name=None):
		toggle = toggle if toggle is not None else None
		family_name = family_name or self.family_name
		if toggle is None or not family_name:
			return False

		updated = False
		for text_op in (
			toggle.op('text') if hasattr(toggle, 'op') else None,
			toggle.op('button/text1') if hasattr(toggle, 'op') else None,
			toggle.op('text1') if hasattr(toggle, 'op') else None,
		):
			try:
				if text_op is not None and hasattr(text_op, 'par') and hasattr(text_op.par, 'text'):
					text_op.par.text = family_name
					updated = True
					break
			except Exception:
				pass

		try:
			if hasattr(toggle.par, 'label'):
				toggle.par.label.expr = ''
				toggle.par.label.bindExpr = "{}.par.Familyname".format(self._owner_bind_expr_op())
				updated = True
		except Exception:
			pass

		return updated

	def _prepare_local_templates_for_ui(self):
		self._sync_family_name(apply_owner_shortcut=False)
		self._prepare_fam_toggle_template()
		self._prepare_fam_script_callbacks_template()
		self._prepare_fam_panel_execute_template()
		self._prepare_custom_operator_templates()
		self._trace("Prepared local UI templates for '{}'".format(self.family_name))

	def _cleanup_native_custom_flow(self):
		removed = 0
		pattern = re.compile(r"if\s*\(\$type=='[^']+'\)\s*\n\s*exit\s*\n\s*endif\s*\n?", re.MULTILINE)
		for dat_name in ('create_node', 'node_script', 'switch_script'):
			dat_op = self._ui(dat_name)
			if dat_op is None:
				continue
			try:
				original = str(dat_op.text or '')
				cleaned, count = pattern.subn('', original)
				if cleaned != original:
					dat_op.text = cleaned
				removed += int(count)
			except Exception:
				pass
		self._trace("Native custom flow cleanup removed exit patches={}".format(removed))
		return removed

	def _configure_delete_op_execute(self):
		# The Delete_op_execute DAT lives in Settings/ inside the family COMP
		# (mirroring Custom_fam/Settings/Delete_op_execute.py on disk). Older
		# layouts kept it under Parameter/ or Parameters/, so we search those
		# too as a fallback. If this DAT is not found the Level-1 cleanup
		# never installs and the toolbar button survives a family deletion
		# (only the watcher self-destructs via Level-3 opexec1).
		delete_exec = self._parameter_dat(
			'Settings/Delete_op_execute',
			'Parameter/Delete_op_execute',
			'Parameters/Delete_op_execute',
			'Delete_op_execute'
		)
		if delete_exec is None:
			self._trace("Configure Delete_op_execute: DAT non trovato per '{}'".format(self.family_name))
			return False

		script_path = self._get_parameter_script_path('Delete_op_execute.py')
		self._trace("Configure Delete_op_execute: dat={} script={}".format(
			delete_exec.path,
			script_path if script_path else 'None'
		))

		try:
			if script_path and hasattr(delete_exec.par, 'file'):
				delete_exec.par.file = script_path
		except Exception as e:
			self._trace("Configure Delete_op_execute: file failed -> {}".format(e))

		try:
			if hasattr(delete_exec.par, 'syncfile'):
				delete_exec.par.syncfile = True
		except Exception as e:
			self._trace("Configure Delete_op_execute: syncfile failed -> {}".format(e))

		try:
			if hasattr(delete_exec.par, 'active'):
				delete_exec.par.active = True
		except Exception as e:
			self._trace("Configure Delete_op_execute: active failed -> {}".format(e))

		try:
			if hasattr(delete_exec.par, 'destroy'):
				delete_exec.par.destroy = True
		except Exception as e:
			self._trace("Configure Delete_op_execute: destroy failed -> {}".format(e))

		try:
			if hasattr(delete_exec.par, 'pathchange'):
				delete_exec.par.pathchange = True
		except Exception as e:
			self._trace("Configure Delete_op_execute: pathchange failed -> {}".format(e))

		try:
			if hasattr(delete_exec.par, 'namechange'):
				delete_exec.par.namechange = True
		except Exception as e:
			self._trace("Configure Delete_op_execute: namechange failed -> {}".format(e))

		try:
			if hasattr(delete_exec.par, 'flagchange'):
				delete_exec.par.flagchange = True
		except Exception as e:
			self._trace("Configure Delete_op_execute: flagchange failed -> {}".format(e))

		try:
			self._configure_op_execute_target(delete_exec, self.ownerComp.path)
		except Exception as e:
			self._trace("Configure Delete_op_execute: target failed -> {}".format(e))

		try:
			self._trace("Configure Delete_op_execute: DAT pronto '{}'".format(delete_exec.path))
		except Exception:
			pass

		return True

	def _configure_op_execute_target(self, exec_op, target_path):
		if exec_op is None or not target_path:
			return False

		target_expr = "op('{}')".format(str(target_path).replace("\\", "\\\\"))
		par_mode = globals().get('ParMode', None)
		target_par_name = ''

		for candidate_name in ('op', 'ops'):
			if hasattr(exec_op.par, candidate_name):
				target_par_name = candidate_name
				break

		if not target_par_name:
			return False

		for par_name in ('ops', 'fromop', 'op'):
			if not hasattr(exec_op.par, par_name):
				continue

			par_obj = getattr(exec_op.par, par_name)
			if par_name == target_par_name:
				try:
					if par_mode is not None and hasattr(par_obj, 'mode'):
						par_obj.mode = par_mode.EXPRESSION
				except Exception:
					pass

				try:
					par_obj.expr = target_expr
				except Exception:
					return False
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
				setattr(exec_op.par, par_name, '')
			except Exception:
				pass

		for par_name in ('executeloc', 'executefrom'):
			par = getattr(exec_op.par, par_name, None)
			if par is None:
				continue

			try:
				menu_names = list(par.menuNames)
			except Exception:
				menu_names = []

			desired_value = ''
			for candidate_name in ('here', 'current'):
				if candidate_name in menu_names:
					desired_value = candidate_name
					break

			if not desired_value:
				for candidate_name in menu_names:
					lowered = str(candidate_name).lower()
					if 'here' in lowered or 'this' in lowered:
						desired_value = candidate_name
						break
					if not desired_value and 'current' in lowered:
						desired_value = candidate_name
						break

			if not desired_value:
				continue

			try:
				setattr(exec_op.par, par_name, desired_value)
			except Exception:
				pass

		return True

	def _install_delete_execute_watcher(self):
		template = self._parameter_dat(
			'Parameter/Delete_op_execute',
			'Parameters/Delete_op_execute',
			'Delete_op_execute'
		)
		bookmark_bar = self._ui('bookmark_bar')
		if template is None or bookmark_bar is None:
			return False

		watcher_name = self._delete_execute_name(self.family_name)
		watcher = self._find_child_by_names(bookmark_bar, self._delete_execute_names())
		if watcher is not None and watcher.name != watcher_name:
			self._safe_destroy(watcher)
			watcher = None

		try:
			if watcher is None:
				watcher = bookmark_bar.copy(template, name=watcher_name)
			else:
				watcher.name = watcher_name
		except Exception as e:
			self._trace("Install delete watcher failed for '{}': {}".format(self.family_name, e))
			return False

		# Ensure cook is enabled immediately so callbacks fire as soon as
		# par.file / target wiring lands below.
		try:
			watcher.allowCooking = True
		except Exception:
			pass

		script_path = self._get_parameter_script_path('Delete_op_execute.py')

		try:
			if script_path and hasattr(watcher.par, 'file'):
				watcher.par.file = script_path
		except Exception:
			pass

		try:
			if hasattr(watcher.par, 'syncfile'):
				watcher.par.syncfile = True
		except Exception:
			pass

		for par_name in ('active', 'destroy', 'pathchange', 'namechange', 'flagchange'):
			try:
				if hasattr(watcher.par, par_name):
					setattr(watcher.par, par_name, True)
			except Exception:
				pass

		self._configure_op_execute_target(watcher, self.ownerComp.path)

		try:
			watcher.store('delete_target_path', self.ownerComp.path)
			watcher.store('delete_family_name', self.family_name)
		except Exception:
			pass

		return True

	def _cleanup_external_delete_helpers(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		if not family_name:
			return 0

		root_candidates = []
		main_root = self._get_main_root()
		if main_root is not None:
			root_candidates.append(main_root)
		root_op = op('/')
		if root_op is not None:
			root_candidates.append(root_op)

		candidate_names = [
			self._delete_execute_name(family_name),
			'{}_delete_execute'.format(family_name),
			'delete_cleanup_{}'.format(family_name),
			'delete_cleanup_{}_temp'.format(family_name),
		]

		removed = 0
		seen = set()

		for root in root_candidates:
			if root is None:
				continue
			for helper_name in candidate_names:
				try:
					helper = root.op(helper_name)
				except Exception:
					helper = None
				if helper is None:
					continue
				try:
					helper_path = helper.path
				except Exception:
					helper_path = str(helper)
				if helper_path in seen:
					continue
				seen.add(helper_path)
				if self._safe_destroy(helper):
					removed += 1

		if removed:
			self._trace("Removed legacy external delete helpers for '{}': {}".format(
				family_name,
				removed,
			))
		return removed

	def _owner_expr_op(self):
		try:
			shortcut = str(self.ownerComp.par.opshortcut.eval()).strip()
			if shortcut:
				return "op({})".format(repr(shortcut))
		except Exception:
			pass
		return "op({})".format(repr(self.ownerComp.path))

	def _owner_bind_expr_op(self):
		"""Return expression string in TD dot-notation for use in par.bindExpr.
		TD bindExpr uses 'op.Shortcut' syntax, not Python 'op(\"Shortcut\")' syntax.
		Uses self.family_name as primary source to avoid stale opshortcut expressions."""
		# Primary: self.family_name is always set correctly by Install(family_name=...)
		try:
			if self.family_name:
				return "op.{}".format(self.family_name)
		except Exception:
			pass
		# Fallback 1: opshortcut constant value (.val, not .eval, to avoid stale expressions)
		try:
			shortcut = str(self.ownerComp.par.opshortcut.val).strip()
			if shortcut and shortcut != 'Custom':
				return "op.{}".format(shortcut)
		except Exception:
			pass
		# Fallback 2: opshortcut evaluated
		try:
			shortcut = str(self.ownerComp.par.opshortcut.eval()).strip()
			if shortcut:
				return "op.{}".format(shortcut)
		except Exception:
			pass
		# Fallback 3: absolute path with op() call
		return "op({})".format(repr(self.ownerComp.path))

	def _wire_bookmark_toggle(self, toggle, empty_panel=None):
		if toggle is None:
			self._trace("wire bookmark toggle skipped: toggle nullo for '{}'".format(self.family_name))
			return False

		try:
			toggle.store('cf_owner_path', self.ownerComp.path)
			toggle.store('cf_family_name', self.family_name)
		except Exception:
			pass

		try:
			if empty_panel and len(toggle.inputCOMPConnectors) > 0:
				toggle.inputCOMPConnectors[0].connect(empty_panel)
		except Exception as e:
			self._trace("wire bookmark toggle empty_panel failed for '{}': {}".format(self.family_name, e))

		try:
			btn_op = None
			if hasattr(toggle, 'par') and hasattr(toggle.par, 'value0'):
				btn_op = toggle
			else:
				btn_op = toggle.op('button')
			if btn_op and hasattr(btn_op, 'par') and hasattr(btn_op.par, 'value0'):
				try:
					btn_op.par.value0.bindExpr = ''
				except Exception:
					pass
				btn_op.par.value0.bindExpr = "{}.par.Selected".format(self._owner_bind_expr_op())
				try:
					btn_op.store('cf_owner_path', self.ownerComp.path)
					btn_op.store('cf_family_name', self.family_name)
				except Exception:
					pass
		except Exception as e:
			self._trace("wire bookmark toggle button bind failed for '{}': {}".format(self.family_name, e))

		try:
			context_execute = toggle.op('panelexec1') or toggle.op('panelexec2')
			if context_execute is not None:
				try:
					context_execute.store('cf_owner_path', self.ownerComp.path)
					context_execute.store('cf_family_name', self.family_name)
				except Exception:
					pass
			self._configure_toggle_context_execute(context_execute)
		except Exception as e:
			self._trace("wire bookmark toggle context execute failed for '{}': {}".format(self.family_name, e))

		# Repair script sync paths for execute DATs inside the /ui button
		try:
			script_map = {
				'chopexec_Selected': 'Ui_inject/button_Custom/chopexec_Selected.py',
				'chopexec_Rename':   'Ui_inject/button_Custom/chopexec_Rename.py',
				'chopexec_call_menu':'Ui_inject/button_Custom/chopexec_call_menu.py',
				'panelexec1':        'Ui_inject/button_Custom/panelexec1.py',
			}
			for dat_name, rel_path in script_map.items():
				dat = toggle.op(dat_name)
				if dat is None or not hasattr(dat.par, 'file'):
					continue
				for root_dir in self._get_component_root_candidates():
					full_path = os.path.join(root_dir, rel_path)
					try:
						if os.path.isfile(full_path):
							dat.par.file = full_path
							if hasattr(dat.par, 'syncfile'):
								dat.par.syncfile = True
							break
					except Exception:
						pass
		except Exception as e:
			self._trace("wire bookmark toggle script sync repair failed for '{}': {}".format(self.family_name, e))

		self._trace("Wired bookmark button '{}'".format(toggle.name))
		return True

	def _configure_toggle_context_execute(self, panel_execute):
		if panel_execute is None or not hasattr(panel_execute, 'par'):
			return False

		panel_target = None
		try:
			parent_comp = panel_execute.parent()
		except Exception:
			parent_comp = None

		if parent_comp is not None:
			try:
				panel_target = parent_comp.op('button')
			except Exception:
				panel_target = None
			if panel_target is None:
				panel_target = parent_comp

		for par_name, value in (
			('active', True),
			('offtoon', True),
			('ontooff', False),
			('whileon', False),
			('whileoff', False),
			('valuechange', True),
		):
			try:
				if hasattr(panel_execute.par, par_name):
					setattr(panel_execute.par, par_name, value)
			except Exception:
				pass

		try:
			if hasattr(panel_execute.par, 'panelvalue'):
				panel_execute.par.panelvalue = 'rselect'
		except Exception:
			pass

		if panel_target is not None:
			try:
				panel_execute.store('cf_button_path', panel_target.path)
			except Exception:
				pass
			for par_name in ('panels', 'panel', 'component', 'op'):
				try:
					if hasattr(panel_execute.par, par_name):
						setattr(panel_execute.par, par_name, panel_target.path)
				except Exception:
					pass

		try:
			if hasattr(panel_execute.par, 'executeloc'):
				menu_names = list(panel_execute.par.executeloc.menuNames)
				if 'here' in menu_names:
					panel_execute.par.executeloc = 'here'
		except Exception:
			pass

		return True

	def _toggle_color_candidates(self, toggle):
		"""Return (toggle, toggle/button) candidates that have color pars."""
		seen = set()
		results = []
		for candidate in (toggle, toggle.op('button') if hasattr(toggle, 'op') else None):
			if candidate is None or not hasattr(candidate, 'par'):
				continue
			try:
				key = candidate.path
			except Exception:
				key = str(id(candidate))
			if key in seen:
				continue
			seen.add(key)
			results.append(candidate)
		return results

	def _apply_color_to_toggle(self, toggle, color=None):
		"""Write color as constant values (no bindExpr) to toggle and its button child.

		Using bindExpr = 'op.FamilyName.par.Colorr' breaks whenever the family is
		renamed or deleted, causing a black flash.  Constants never break — color is
		updated explicitly by _sync_button_color() when the user changes it.
		"""
		if color is None:
			color = self.color
		r = color[0] if len(color) > 0 else 0.2
		g = color[1] if len(color) > 1 else 0.2
		b = color[2] if len(color) > 2 else 0.2

		updated = False
		for candidate in self._toggle_color_candidates(toggle):
			try:
				if tuple(candidate.color) != tuple((r, g, b)):
					candidate.color = (r, g, b)
					updated = True
			except Exception:
				pass

			for par_name, val in (('colorr', r), ('colorg', g), ('colorb', b)):
				try:
					par_obj = getattr(candidate.par, par_name, None)
					if par_obj is None:
						continue
					try:
						par_obj.bindExpr = ''
					except Exception:
						pass
					try:
						par_obj.expr = ''
					except Exception:
						pass
					par_obj.val = val
					updated = True
				except Exception as e:
					self._trace("color set failed {} for '{}': {}".format(par_name, self.family_name, e))

			for par_name, val in (('Colorr', r), ('Colorg', g), ('Colorb', b)):
				try:
					par_obj = getattr(candidate.par, par_name, None)
					if par_obj is None:
						continue
					try:
						par_obj.bindExpr = ''
					except Exception:
						pass
					try:
						par_obj.expr = ''
					except Exception:
						pass
					par_obj.val = val
					updated = True
				except Exception:
					pass
		return updated

	def _prepare_bookmark_toggle_visuals(self, toggle):
		updated = self._apply_color_to_toggle(toggle)
		if updated:
			self._trace("Prepared bookmark visuals (constant color) for '{}'".format(self.family_name))
		return updated

	def _refresh_family_name_from_owner(self):
		"""Pull the current opshortcut/name off the owner COMP into self.family_name.
		Counter-acts the stale-cache scenario where a long-lived InstallerEXT
		instance (cached on ComponentEXT) keeps the pre-rename family name and
		downstream lookups by name (button_<old>, colors_table row, ...) miss.
		"""
		try:
			cur = self._sanitize_family_name(self.ownerComp.par.opshortcut.eval())
		except Exception:
			cur = ''
		if not cur:
			try:
				cur = self._sanitize_family_name(self.ownerComp.name)
			except Exception:
				cur = ''
		if cur and cur != self.family_name:
			self.family_name = cur
		return self.family_name

	def _sync_button_color(self, color=None):
		"""Update bookmark button color constants when the family color changes.

		Called by ComponentEXT.SyncInstalledColor after installer.color is updated.
		"""
		color = color or self.color
		bookmark_bar = self._ui('bookmark_bar')
		if bookmark_bar is None:
			return False
		# Cached bridge may carry a pre-rename family_name — refresh before lookup
		# so we search for the current button_<name> instead of the stale one.
		self._refresh_family_name_from_owner()
		toggle = self._find_child_by_names(bookmark_bar, self._bookmark_toggle_names())
		if toggle is None:
			return False
		updated = self._apply_color_to_toggle(toggle, color=color)
		if updated:
			self._trace("Synced button color for '{}'".format(self.family_name))
		return updated

	def _sync_ui_family_colors(self, color=None):
		"""Apply the current family color to the installed UI clones we own."""
		color = color or self.color
		rgb = (
			color[0] if len(color) > 0 else 0.2,
			color[1] if len(color) > 1 else 0.2,
			color[2] if len(color) > 2 else 0.2,
		)

		try:
			owner_path = self.ownerComp.path
		except Exception:
			owner_path = ''

		try:
			owner_id = str(self.ownerComp.id)
		except Exception:
			owner_id = ''

		updated = False
		for root in (self._ui('bookmark_bar'), self._ui('menu_op'), self._ui('node_table')):
			if root is None:
				continue
			try:
				children = root.findChildren(depth=None, maxDepth=2)
			except Exception:
				children = []
			for child in children:
				if child is None:
					continue
				try:
					child_owner_path = str(child.fetch('cf_owner_path', ''))
				except Exception:
					child_owner_path = ''
				try:
					child_owner_id = str(child.fetch('cf_owner_id', ''))
				except Exception:
					child_owner_id = ''

				if not ((owner_path and child_owner_path == owner_path) or (owner_id and child_owner_id == owner_id)):
					continue

				try:
					if tuple(child.color) != tuple(rgb):
						child.color = rgb
						updated = True
				except Exception:
					pass

				try:
					if child.name.startswith('button_') or child.name.endswith('_button'):
						if self._apply_color_to_toggle(child, color=rgb):
							updated = True
				except Exception:
					pass

		if updated:
			self._trace("Synced UI family colors for '{}'".format(self.family_name))
		return updated

	def _store_family_insert_slot(self, menu_op, upstream=None, downstream=None):
		if menu_op is None:
			return False

		try:
			menu_op.store('cf_insert_upstream_path', upstream.path if upstream is not None else '')
			menu_op.store('cf_insert_downstream_path', downstream.path if downstream is not None else '')
			return True
		except Exception:
			return False

	def _fetch_family_insert_slot(self, menu_op):
		if menu_op is None:
			return None, None

		upstream_path = ''
		downstream_path = ''
		try:
			upstream_path = str(menu_op.fetch('cf_insert_upstream_path', '')).strip()
		except Exception:
			pass
		try:
			downstream_path = str(menu_op.fetch('cf_insert_downstream_path', '')).strip()
		except Exception:
			pass

		upstream = op(upstream_path) if upstream_path else None
		downstream = op(downstream_path) if downstream_path else None
		return upstream, downstream

	def _connect_op(self, source_connector, target):
		"""Connect source_connector to target, handling baseCOMP targets correctly."""
		if getattr(target, 'isCOMP', False):
			source_connector.connect(target.inputConnectors[0])
		else:
			source_connector.connect(target)

	def _wire_family_insert(self, insert1, family_insert, menu_op=None):
		if insert1 is None or family_insert is None:
			self._trace("wire family insert skipped for '{}': insert1={} family_insert={}".format(
				self.family_name,
				insert1.path if insert1 else 'None',
				family_insert.path if family_insert else 'None'
			))
			return False

		downstream = None
		try:
			if len(family_insert.outputs) > 0 and family_insert.outputs[0] is not None:
				downstream = family_insert.outputs[0]
		except Exception:
			pass

		if downstream is None:
			try:
				if len(insert1.outputs) > 0 and insert1.outputs[0] is not None and insert1.outputs[0] != family_insert:
					downstream = insert1.outputs[0]
			except Exception:
				pass

		upstream = None
		try:
			if len(insert1.inputs) > 0 and insert1.inputs[0] is not None:
				upstream = insert1.inputs[0]
		except Exception:
			pass

		try:
			insert1.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			insert1.inputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			family_insert.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			family_insert.inputConnectors[0].disconnect()
		except Exception:
			pass

		self._store_family_insert_slot(menu_op, upstream=upstream, downstream=downstream)

		try:
			if upstream is not None:
				upstream.outputConnectors[0].disconnect()
				self._connect_op(upstream.outputConnectors[0], family_insert)
			if downstream is not None:
				family_insert.outputConnectors[0].connect(downstream)
			self._trace("Wired family insert '{}' downstream={}".format(
				family_insert.name,
				downstream.path if downstream else 'None'
			))
			return True
		except Exception as e:
			self._trace("wire family insert failed for '{}': {}".format(self.family_name, e))
			return False

	def _wire_family_insert_into_slot(self, menu_op, family_insert):
		if menu_op is None or family_insert is None:
			return False

		upstream, downstream = self._fetch_family_insert_slot(menu_op)
		if upstream is None and downstream is None:
			insert1 = self._ui('insert1')
			custom_entry = self._find_custom_menu_entry(menu_op)
			try:
				if insert1 is not None:
					upstream = insert1.inputs[0] if len(insert1.inputs) > 0 else None
					downstream = insert1.outputs[0] if len(insert1.outputs) > 0 else None
				elif custom_entry is not None and custom_entry != family_insert:
					upstream = custom_entry.inputs[0] if len(custom_entry.inputs) > 0 else None
					downstream = custom_entry.outputs[0] if len(custom_entry.outputs) > 0 else None
				if upstream is not None or downstream is not None:
					self._store_family_insert_slot(menu_op, upstream=upstream, downstream=downstream)
					self._trace(
						"Recovered insert slot for '{}': upstream={} downstream={}".format(
							self.family_name,
							upstream.path if upstream is not None else 'None',
							downstream.path if downstream is not None else 'None',
						),
						showMessage=True,
					)
			except Exception:
				pass
			if upstream is None and downstream is None:
				self._trace(
					"No insert slot available for '{}', family_insert={}".format(
						self.family_name,
						family_insert.path if family_insert is not None else 'None',
					),
					showMessage=True,
				)
				return False

		current_input = None
		current_output = None
		try:
			if len(family_insert.inputs) > 0 and family_insert.inputs[0] is not None:
				current_input = family_insert.inputs[0]
		except Exception:
			pass

		try:
			if len(family_insert.outputs) > 0 and family_insert.outputs[0] is not None:
				current_output = family_insert.outputs[0]
		except Exception:
			pass

		if current_input is not None and current_output is not None:
			self._trace("Family insert '{}' already wired in slot".format(family_insert.name))
			return True

		tail = upstream
		try:
			if downstream is not None and len(downstream.inputs) > 0 and downstream.inputs[0] is not None:
				candidate = downstream.inputs[0]
				if candidate != family_insert:
					tail = candidate
		except Exception:
			pass

		try:
			family_insert.inputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			family_insert.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if tail is not None:
				tail.outputConnectors[0].disconnect()
				self._connect_op(tail.outputConnectors[0], family_insert)
			if downstream is not None:
				family_insert.outputConnectors[0].connect(downstream)
			self._trace(
				"Wired '{}' into slot: tail={} downstream={}".format(
					family_insert.name,
					tail.path if tail is not None else 'None',
					downstream.path if downstream is not None else 'None',
				),
				showMessage=True,
			)
			return True
		except Exception as e:
			self._trace("wire family insert slot failed for '{}': {}".format(self.family_name, e))
			return False

	def _restore_family_insert_connection(self, menu_op, family_name=None):
		family_name = family_name or self.family_name
		insert1 = self._ui('insert1')
		family_insert = self._find_child_by_names(menu_op, self._family_insert_names(family_name))
		if family_insert is None and self._sanitize_family_name(family_name) == 'Custom':
			family_insert = self._find_custom_menu_entry(menu_op, managed_only=True)
		if family_insert is None:
			self._trace("restore family insert skipped for '{}' insert1={} family_insert={}".format(
				family_name,
				insert1.path if insert1 else 'None',
				family_insert.path if family_insert else 'None'
			))
			return False

		upstream = None
		downstream = None
		try:
			if len(family_insert.inputs) > 0 and family_insert.inputs[0] is not None:
				upstream = family_insert.inputs[0]
		except Exception:
			pass

		try:
			if len(family_insert.outputs) > 0 and family_insert.outputs[0] is not None:
				downstream = family_insert.outputs[0]
		except Exception:
			pass

		try:
			family_insert.inputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			family_insert.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if upstream is not None and downstream is not None:
				upstream.outputConnectors[0].disconnect()
				upstream.outputConnectors[0].connect(downstream)
			self._trace("Restored family insert chain for '{}' downstream={}".format(
				family_name,
				downstream.path if downstream else 'None'
			))
			return True
		except Exception as e:
			self._trace("restore family insert failed for '{}': {}".format(family_name, e))
			return False

	def _ensure_families_switch(self, node_table):
		return None

	def _cleanup_legacy_families_switch(self, node_table):
		if node_table is None:
			return False

		switch_op = node_table.op('switch1')
		families_op = node_table.op('families')
		in1_op = node_table.op('in1')
		if switch_op is None or families_op is None or in1_op is None:
			return False

		replacement = None
		try:
			if len(switch_op.inputs) > 1 and switch_op.inputs[1] is not None:
				replacement = switch_op.inputs[1]
		except Exception:
			pass
		if replacement is None:
			replacement = in1_op

		try:
			families_op.inputConnectors[0].disconnect()
		except Exception:
			pass
		try:
			switch_op.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if replacement is not None:
				replacement.outputConnectors[0].connect(families_op)
		except Exception as e:
			self._trace("legacy switch cleanup wire failed for '{}': {}".format(self.family_name, e))

		self._safe_destroy(switch_op)
		self._trace("Removed legacy switch1 for '{}'".format(self.family_name))
		return True

	def _get_inject_template(self):
		for path in (
			'Ui_inject/Inject_Custom',
			'Ui_inject/Inject_custom',
			'inject_Custom',
			'Inject_Custom',
			'Inject_custom',
			'Ui_templates/inject_Custom',
			'Ui_templates/Inject_Custom',
			'Ui_templates/Inject_custom',
			'Ui_scripts/inject_Custom',
			'Ui_scripts/Inject_Custom',
			'Ui_scripts/Inject_custom',
		):
			try:
				template = self.ownerComp.op(path)
			except Exception:
				template = None
			if template is not None:
				return template
		return None

	def _refresh_external_families_bypass(self, node_table):
		if node_table is None:
			return False

		families_op = node_table.op('families')
		if families_op is None:
			return False

		has_custom_inject = False
		try:
			for child in getattr(node_table, 'children', []):
				try:
					if child.isCOMP and str(child.name).startswith('inject_'):
						has_custom_inject = True
						break
				except Exception:
					pass
		except Exception:
			pass

		try:
			if hasattr(families_op.par, 'bypass'):
				families_op.par.bypass.expr = ''
				families_op.par.bypass = 1 if has_custom_inject else 0
			else:
				families_op.bypass = bool(has_custom_inject)
		except Exception:
			pass

		self._trace("External families bypass={} for '{}'".format(
			int(has_custom_inject),
			self.family_name,
		))
		return True

	def _read_synced_dat_text(self, dat_op):
		if dat_op is None:
			return ''
		try:
			path = str(dat_op.par.file.eval()).strip()
		except Exception:
			try:
				path = str(dat_op.par.file).strip()
			except Exception:
				path = ''
		if not path:
			try:
				return str(dat_op.text)
			except Exception:
				return ''
		try:
			if os.path.isfile(path):
				with open(path, 'r', encoding='utf-8') as handle:
					return handle.read()
		except Exception:
			pass
		try:
			return str(dat_op.text)
		except Exception:
			return ''

	def _plugin_source_root(self):
		try:
			installer_dat = self.ownerComp.op('InstallerEXT')
		except Exception:
			installer_dat = None
		if installer_dat is None:
			return ''
		try:
			path = str(installer_dat.par.file.eval()).strip()
		except Exception:
			try:
				path = str(installer_dat.par.file).strip()
			except Exception:
				path = ''
		if not path:
			return ''
		try:
			if os.path.isfile(path):
				return os.path.dirname(path)
		except Exception:
			pass
		return ''

	def _read_plugin_source_file(self, *relative_parts):
		root = self._plugin_source_root()
		if not root:
			return ''
		try:
			candidate = os.path.join(root, *relative_parts)
			if os.path.isfile(candidate):
				with open(candidate, 'r', encoding='utf-8') as handle:
					return handle.read()
		except Exception:
			pass
		return ''

	def _get_inject_families_callback_source_text(self):
		text = ''
		for rel_parts in (
			('Ui_inject', 'Inject_Custom', 'script1_callbacks.py'),
			('Ui_inject', 'Inject_custom', 'script1_callbacks.py'),
			('Ui_scripts', 'Inject_custom', 'script1_callbacks.py'),
			('Ui_scripts', 'inject_Custom', 'script1_callbacks.py'),
		):
			text = self._read_plugin_source_file(*rel_parts)
			if text:
				break
		for callback_path in (
			'Ui_inject/Inject_Custom/script1_callbacks',
			'Ui_inject/Inject_custom/script1_callbacks',
			'Ui_scripts/inject_Custom/script1_callbacks',
			'Ui_scripts/Inject_custom/script1_callbacks',
		):
			if text:
				break
			try:
				source_dat = self.ownerComp.op(callback_path)
			except Exception:
				source_dat = None
			if source_dat is None:
				continue
			text = self._read_synced_dat_text(source_dat)
			if text:
				break
		if not text:
			return ''
		required_tokens = (
			'def _copy_input_or_header',
			'def _input_is_operator_table',
			'def _read_current_family',
			'def cook(scriptOp):',
			'if _input_is_operator_table(scriptOp):',
		)
		if all(token in text for token in required_tokens):
			return text
		return ''

	def _prepare_inject_template_instance(self, inject_comp):
		if inject_comp is None:
			return

		inject_name = self._inject_op_name()
		family_name = self._sanitize_family_name(self.family_name)
		inner_inject = None
		callbacks_dat = None
		inner_families = None
		inner_families_callbacks = None
		try:
			for child in inject_comp.findChildren(maxDepth=2):
				if str(child.name).startswith('inject_'):
					inner_inject = child
				elif str(child.name) == 'families':
					inner_families = child
				elif str(child.name) == 'fam_script_callbacks':
					callbacks_dat = child
				elif str(child.name) == 'script1_callbacks':
					inner_families_callbacks = child
		except Exception:
			inner_inject = None
			callbacks_dat = None
			inner_families = None
			inner_families_callbacks = None

		if inner_inject is not None:
			try:
				inner_inject.name = inject_name
			except Exception:
				pass
			try:
				if hasattr(inner_inject.par, 'callbacks'):
					inner_inject.par.callbacks.expr = "op('fam_script_callbacks')"
			except Exception:
				pass
			try:
				inner_inject.store('cf_last_state', None)
			except Exception:
				pass
			try:
				inner_inject.allowCooking = True
			except Exception:
				pass
			try:
				if hasattr(inner_inject.par, 'bypass'):
					inner_inject.par.bypass.expr = ''
					inner_inject.par.bypass = 0
				else:
					inner_inject.bypass = False
			except Exception:
				pass

		if inner_families is not None:
			try:
				if hasattr(inner_families.par, 'callbacks'):
					if inner_families_callbacks is not None:
						inner_families.par.callbacks.expr = "op('script1_callbacks')"
			except Exception:
				pass
			try:
				inner_families.allowCooking = True
			except Exception:
				pass

		if inner_families_callbacks is not None:
			try:
				callback_text = self._get_inject_families_callback_source_text()
				if callback_text:
					inner_families_callbacks.text = callback_text
					try:
						inner_families_callbacks.store('cf_last_state', None)
					except Exception:
						pass
					self._trace("Refreshed internal families callback for '{}'".format(self.family_name))
				else:
					self._trace("inject families callback source missing/invalid for '{}'".format(self.family_name))
			except Exception as e:
				self._trace("inject families callback patch failed for '{}': {}".format(self.family_name, e))
			try:
				if hasattr(inner_families.par, 'bypass'):
					inner_families.par.bypass.expr = ''
					inner_families.par.bypass = 0
				else:
					inner_families.bypass = False
			except Exception:
				pass

		if callbacks_dat is not None:
			try:
				source_callbacks = self._script('fam_script_callbacks')
				callback_text = source_callbacks.text if source_callbacks is not None else callbacks_dat.text
				callback_text = re.sub(
					r"(?m)^DEFAULT_FAMILY_NAME\s*=\s*.+$",
					"DEFAULT_FAMILY_NAME = {!r}".format(family_name or self.ownerComp.name),
					callback_text,
				)
				callback_text = re.sub(
					r"(?m)^SOURCE_OPERATOR_PATH\s*=\s*.+$",
					"SOURCE_OPERATOR_PATH = {!r}".format(self.ownerComp.path),
					callback_text,
				)
				callback_text = re.sub(
					r"(?m)^CUSTOM_OPERATORS_PATH\s*=\s*.+$",
					"CUSTOM_OPERATORS_PATH = {!r}".format('../Custom_operators'),
					callback_text,
				)
				callbacks_dat.text = callback_text
				try:
					callbacks_dat.par.file = ''
				except Exception:
					pass
			except Exception as e:
				self._trace("inject template callback patch failed for '{}': {}".format(self.family_name, e))

		try:
			switch_op = inject_comp.op('switch1')
			if switch_op is not None and hasattr(switch_op.par, 'index'):
				switch_op.par.index.expr = "1 if op('/ui/dialogs/menu_op/current') is not None and op('/ui/dialogs/menu_op/current').numRows > 0 and str(op('/ui/dialogs/menu_op/current')[0,0].val).strip() == {!r} else 0".format(
					family_name or self.ownerComp.name,
				)
		except Exception as e:
			self._trace("inject template switch expr failed for '{}': {}".format(self.family_name, e))

		try:
			if hasattr(inject_comp.par, 'bypass'):
				inject_comp.par.bypass.expr = ''
				inject_comp.par.bypass = 0
			else:
				inject_comp.bypass = False
		except Exception:
			pass
		try:
			inject_comp.allowCooking = True
		except Exception:
			pass

		# Make the Compatible par expression defensive: the shipped template
		# binds it to op('../compatible')[var('menu_type'), op('in1')[0,0].val],
		# which raises when in1 is empty (dialog closed / chain dormant).
		# Returning '' in that case keeps the par silent instead of red-erroring.
		self._patch_compatible_par_defensive(inject_comp)

	def _patch_compatible_par_defensive(self, inject_comp):
		"""Wrap inject_comp.par.Compatible's expression with an empty-in1 guard
		so par evaluation doesn't error when the families chain is dormant.
		Idempotent: only rewrites the expression when the guard isn't already
		in place.
		"""
		if inject_comp is None:
			return
		try:
			par = getattr(inject_comp.par, 'Compatible', None)
		except Exception:
			par = None
		if par is None:
			return
		try:
			expr = par.expr or ''
		except Exception:
			expr = ''
		# Already guarded — bail.
		if 'op(\'in1\').numRows' in expr or 'in1.numRows' in expr:
			return
		# Only patch the known shipped expression so we don't clobber user edits.
		if "op('in1')[0,0].val" not in expr or 'compatible' not in expr:
			return
		guarded = (
			"op('../compatible')[var('menu_type'),op('in1')[0,0].val] "
			"if op('in1').numRows and op('in1').numCols else ''"
		)
		try:
			par.expr = guarded
			self._trace("Guarded Compatible par on '{}'".format(inject_comp.name))
		except Exception as e:
			self._trace("Compatible par guard failed for '{}': {}".format(inject_comp.name, e))

	def _wire_inject_family(self, families_op, inject_op):
		if families_op is None or inject_op is None:
			self._trace("wire inject skipped for '{}': families={} inject={}".format(
				self.family_name,
				families_op.path if families_op else 'None',
				inject_op.path if inject_op else 'None'
			))
			return False

		upstream = None
		try:
			if len(families_op.inputs) > 0:
				upstream = families_op.inputs[0]
		except Exception:
			upstream = None

		upstream_is_inject = upstream == inject_op
		if not upstream_is_inject and upstream is not None:
			try:
				upstream_is_inject = str(upstream.path).startswith(str(inject_op.path) + '/')
			except Exception:
				upstream_is_inject = False
		if upstream_is_inject:
			try:
				upstream = inject_op.inputs[0] if len(inject_op.inputs) > 0 else None
			except Exception:
				upstream = None

		try:
			if len(inject_op.inputs) > 0:
				inject_op.inputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if len(inject_op.outputs) > 0:
				inject_op.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if len(families_op.inputConnectors) > 0:
				families_op.inputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if upstream is not None and len(inject_op.inputConnectors) > 0:
				inject_op.inputConnectors[0].connect(upstream)
			if len(inject_op.outputConnectors) > 0:
				inject_op.outputConnectors[0].connect(families_op)
			self._layout_inject_chain(families_op)
			self._trace("Wired inject '{}' upstream={}".format(
				inject_op.name,
				upstream.path if upstream else 'None'
			))
			return True
		except Exception as e:
			self._trace("wire inject failed for '{}': {}".format(self.family_name, e))
			return False

	def _layout_inject_chain(self, families_op):
		if families_op is None:
			return False

		chain = []
		current = None
		try:
			if len(families_op.inputs) > 0:
				current = families_op.inputs[0]
		except Exception:
			current = None

		while current is not None:
			try:
				name = str(current.name)
			except Exception:
				name = ''
			if not name.startswith('inject_'):
				break
			chain.append(current)
			try:
				current = current.inputs[0] if len(current.inputs) > 0 else None
			except Exception:
				current = None

		for index, inject_comp in enumerate(chain):
			try:
				inject_comp.nodeX = families_op.nodeX - (150 * (index + 1))
				inject_comp.nodeY = families_op.nodeY
			except Exception:
				pass

		return bool(chain)

	def _restore_inject_connection(self, node_table, family_name=None):
		family_name = family_name or self.family_name
		families_op = node_table.op('families') if node_table else None
		inject_op = self._find_child_by_names(node_table, self._inject_op_names(family_name))
		if inject_op is None:
			self._trace("restore inject skipped for '{}' families={} inject={}".format(
				family_name,
				families_op.path if families_op else 'None',
				inject_op.path if inject_op else 'None'
			))
			return False

		upstream = None
		downstream = None
		try:
			if len(inject_op.inputs) > 0 and inject_op.inputs[0] is not None:
				upstream = inject_op.inputs[0]
		except Exception:
			pass

		try:
			if len(inject_op.outputs) > 0 and inject_op.outputs[0] is not None:
				downstream = inject_op.outputs[0]
		except Exception:
			pass

		if downstream is None:
			downstream = families_op

		try:
			inject_op.inputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			inject_op.outputConnectors[0].disconnect()
		except Exception:
			pass

		try:
			if upstream is not None and downstream is not None and len(downstream.inputConnectors) > 0:
				try:
					source_connector = upstream.outputConnectors[0]
				except Exception:
					source_connector = upstream
				downstream.inputConnectors[0].connect(source_connector)
			if families_op is not None:
				self._layout_inject_chain(families_op)
			self._trace("Restored inject chain for '{}' upstream={}".format(
				family_name,
				upstream.path if upstream else 'None'
			))
			return True
		except Exception as e:
			self._trace("restore inject failed for '{}': {}".format(family_name, e))
			return False

	def _destroy_ui_clones(self, family_name=None, destroy_toggle=False):
		family_name = family_name or self.family_name
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
			insert_op = self._find_custom_menu_entry(menu_op, managed_only=True) if menu_op else None
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
				self._destroy_bookmark_family_ops(family_name)
			else:
				try:
					if toggle_op is not None:
						toggle_op.allowCooking = True
				except Exception:
					pass

		if menu_op:
			self._restore_family_insert_connection(menu_op, family_name=family_name)
			self._safe_destroy(insert_op)
			self._safe_destroy(panel_execute_op)
			self._cleanup_custom_comp_runners(family_name)
			self._remove_color_row(menu_op, family_name=family_name)
			self._remove_compatible_entries(menu_op, family_name=family_name)
			self._cleanup_eval4(node_table, family_name=family_name)
			self._cleanup_launch_menu_op(menu_op)
			self._cleanup_create_node(menu_op, family_name=family_name)
			self._cleanup_native_custom_flow()
			self._cleanup_search_exec(menu_op, family_name=family_name)
			self._reset_menu_current_family(family_name=family_name)

		if node_table:
			self._restore_inject_connection(node_table, family_name=family_name)
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
			self._refresh_external_families_bypass(node_table)

		self._destroy_ui_family_ops(
			family_name,
			destroy_toggle=destroy_toggle,
		)
		self._destroy_family_residues(
			family_name=family_name,
			destroy_toggle=destroy_toggle,
		)
		self._trace("Cleanup finished for '{}'".format(family_name))

	def RebuildInstalledClones(self, previous_family=None, new_family=None):
		self._reset_trace("RebuildInstalledClones")

		previous_family = self._sanitize_family_name(previous_family or '')
		new_family = self._sanitize_family_name(new_family or self._get_family_name())

		self._trace("Rebuild installed clones: old='{}' new='{}'".format(previous_family, new_family), showMessage=True)

		if not new_family:
			self._trace("Rebuild installed clones aborted: missing new family")
			return False

		if previous_family:
			self._request_family_ui_cleanup(previous_family, comp=self.ownerComp)
			self._cleanup_external_delete_helpers(previous_family)

		if new_family:
			self._request_family_ui_cleanup(new_family, comp=self.ownerComp)
			self._cleanup_external_delete_helpers(new_family)

		try:
			self.ownerComp.par.Install = 1
			self._lastInstallParameterState = 1
		except Exception:
			pass

		result = self.Install(family_name=new_family, show_message=False, reset_trace=False)
		if result:
			self._set_recorded_installed_family(new_family)
		self._trace("Rebuild installed clones result for '{}': {}".format(new_family, result), showMessage=True)
		return result

	def DeleteCleanup(self, family_name=None, reset_trace=True):
		return self._request_family_remove(family_name=family_name, comp=self.ownerComp)

	def _is_installation_needed(self):
		try:
			menu_op = self._ui('menu_op')
			node_table = self._ui('node_table')
			insert_exists = self._find_child_by_names(menu_op, self._family_insert_names()) is not None if menu_op else False
			has_custom_defs = bool(self._iter_custom_comp_runner_defs())
			runner_exists = self._has_custom_comp_runners(self.family_name) if has_custom_defs else True
			panel_exists = self._find_child_by_names(menu_op, self._panel_execute_names()) is not None if menu_op else False
			inject_exists = self._find_child_by_names(node_table, self._inject_op_names()) is not None if node_table else False

			if panel_exists:
				return True
			if insert_exists or inject_exists:
				if self._iter_custom_comp_runner_defs() and not runner_exists:
					return True
				return False

			if node_table:
				eval4 = node_table.op('eval4')
				if eval4:
					try:
						expr = eval4.par.expr.eval()
					except Exception:
						expr = ''
					if self.family_name in str(expr):
						return False

			return True
		except Exception as e:
			debug("Installation check failed: {}".format(e))
			return True

	def HandleInstallValue(self, raw_value, source_label='external'):
		value_str, action_name = self._normalize_install_action(raw_value)
		self._sync_family_name(apply_owner_shortcut=False)

		if action_name != 'Install':
			self._trace("HandleInstallValue[{}]: installer ignores non-install value '{}'".format(
				source_label,
				raw_value,
			))
			return False

		return self._HandleInstallAction(source_label=source_label)

	def _HandleInstallAction(self, source_label='external'):
		is_auto_source = self._is_auto_source(source_label)
		is_hosted_import = self._is_hosted_auto_import(source_label)
		is_duplicate_copy = False
		is_external_tox_import = False
		external_drop_info = {}
		context_menu_guard_state = self._context_menu_toggle_guard_state()
		hosted_family = self._get_hosted_import_family() if is_auto_source else ''
		if is_auto_source:
			external_drop_info = self._peek_external_tox_drop_info_for_owner() or {}
			is_external_tox_import = bool(
				self._has_external_tox_import_marker() or
				external_drop_info
			)

		if context_menu_guard_state is not None and not is_auto_source:
			self._trace(
				"HandleInstallValue[{}]: context-menu guard active for '{}' keep={}".format(
					source_label,
					self.ownerComp.path,
					context_menu_guard_state,
				)
			)
			try:
				if hasattr(self.ownerComp.par, 'Install'):
					self.ownerComp.par.Install = int(bool(context_menu_guard_state))
			except Exception:
				pass
			self._lastInstallParameterState = int(bool(context_menu_guard_state))
			return True

		if is_auto_source and self._has_hosted_import_pending():
			if hosted_family and self._sanitize_family_name(self.family_name) != hosted_family:
				self._trace("HandleInstallValue[{}]: adopting hosted family '{}'".format(source_label, hosted_family))
				self.family_name = hosted_family
				self._set_owner_shortcut(hosted_family)
				try:
					self._apply_canonical_family_name(hosted_family)
				except Exception:
					pass
				self._clear_hosted_import_pending()

		if self._is_internal_duplicate_copy(source_label):
			is_duplicate_copy = True
			duplicate_name = self._prepare_internal_duplicate_identity()
			if duplicate_name:
				self._skipCanonicalInstall = True
				self._skipExistingFamilyReplacement = True
				self._skipPreviousFamilyCleanup = True

		should_auto_queue = False
		if not is_hosted_import:
			if self._is_inside_custom_families_base():
				should_auto_queue = False
			else:
				should_auto_queue = True

		if should_auto_queue:
			queued = self._queue_auto_install_in_custom_families()
			if queued:
				self._trace("HandleInstallValue[{}]: install delegated to Custom_families host".format(source_label))
				return True

		try:
			self.ownerComp.store('cf_hosted_import_copy', False)
		except Exception:
			pass

		if is_external_tox_import:
			self._trace("HandleInstallValue[{}]: external tox import confirmed source='{}'".format(
				source_label,
				(external_drop_info or {}).get('source', '') or self.ownerComp.fetch(self.EXTERNAL_TOX_SOURCE_KEY, ''),
			))

		self._handlingInstallValue = True
		self._currentInstallSourceLabel = source_label
		try:
			result = self.Install(show_message=(not is_auto_source), is_update=None, reset_trace=True)
		finally:
			self._handlingInstallValue = False
			self._currentInstallSourceLabel = ''
			if is_duplicate_copy:
				self._skipCanonicalInstall = False
				self._skipExistingFamilyReplacement = False
				self._skipPreviousFamilyCleanup = False
			if is_external_tox_import:
				self._clear_external_tox_import_marker()

		return result

	def HandleInstallFromOwnerState(self, source_label='external'):
		try:
			raw_value = self.ownerComp.par.Install.eval()
		except Exception as e:
			self._reset_trace("HandleInstallFromOwnerState {}".format(source_label))
			self._trace("HandleInstallFromOwnerState[{}]: errore leggendo ownerComp.par.Install -> {}".format(
				source_label,
				e
			))
			return False

		self._trace("HandleInstallFromOwnerState[{}]: ownerComp.par.Install='{}'".format(
			source_label,
			raw_value
		))
		return self.HandleInstallValue(raw_value, source_label=source_label)

	def Install(
		self,
		family_name=None,
		color=None,
		compatible_types=None,
		show_message=False,
		is_update=None,
		reset_trace=True,
	):
		if family_name is not None:
			self.family_name = str(family_name).strip()

		if color is not None:
			self.color = color

		if compatible_types is not None:
			self.compatible_types = compatible_types

		if reset_trace:
			trace_family = self.family_name if family_name is None else family_name
			self._reset_trace("Install {}".format(trace_family))

		self._sync_family_name(apply_owner_shortcut=False)

		# The imported source COMP must never install UI directly from /project1.
		# It first moves into Custom_families/Local; only that hosted copy installs
		# buttons, watchers, inserts and menu patches.
		if not self._is_inside_custom_families_local():
			# Defer install when the family is inside a Custom_families that
			# lives somewhere OTHER than the canonical /ui/Plugins/Custom_families
			# (typical: a freshly-dragged plugin .tox at /project1/Custom_families/...
			# whose own Install_window dialog hasn't been confirmed yet). The
			# plugin install pipeline will move the family into canonical Local
			# later; at that point Auto_install_execute fires again and Install
			# runs under the correct host. We must NOT defer when the family is
			# already in canonical Server (or any other canonical sub-container
			# like a future Embeded extra) — those need to install for real.
			owner_path = str(self.ownerComp.path)
			is_canonical_host = (
				owner_path == self.CUSTOM_FAMILIES_MANAGER_PATH or
				owner_path.startswith(self.CUSTOM_FAMILIES_MANAGER_PATH + '/')
			)
			if not is_canonical_host and self._is_inside_custom_families_base():
				self._trace("Install deferred: family inside non-canonical Custom_families host '{}'".format(owner_path))
				return True
			if self._queue_auto_install_in_custom_families():
				self._trace("Install delegated to Custom_families Local for '{}'".format(self.ownerComp.path))
				return True

		skip_canonical = bool(getattr(self, '_skipCanonicalInstall', False))
		canonical_family = ''
		if not skip_canonical:
			canonical_family = self._resolve_canonical_family_name(self.family_name)
			if canonical_family:
				self.family_name = canonical_family
		else:
			self._trace("Install canonicalization skipped for duplicate family '{}'".format(
				self.family_name
			))
		self._lastInstallWasUpdate = False
		if is_update is not None:
			self._lastInstallWasUpdate = bool(is_update)

		skip_existing_replacement = bool(getattr(self, '_skipExistingFamilyReplacement', False))
		skip_previous_cleanup = bool(getattr(self, '_skipPreviousFamilyCleanup', False))

		replaced_existing = False
		if not skip_canonical and not skip_existing_replacement:
			replaced_existing = self._replace_existing_family_owners(self.family_name)
			if replaced_existing:
				self._lastInstallWasUpdate = True
		elif skip_existing_replacement:
			self._trace("Install existing-family replacement skipped for duplicate family '{}'".format(
				self.family_name
			))

		previous_family_cleaned = False
		if not skip_previous_cleanup:
			previous_family_cleaned = self._cleanup_previous_family_before_install(self.family_name)
		else:
			self._trace("Install previous-family cleanup skipped for duplicate family '{}'".format(
				self.family_name
			))
		if previous_family_cleaned:
			self._lastInstallWasUpdate = True
		if canonical_family:
			self._trace("Canonical family applied in Install after replacement: '{}'".format(
				canonical_family,
			))
			self._apply_canonical_family_name(canonical_family)

		self.last_install_time = time.time()

		print("Installing {}".format(self.family_name))
		self._trace("Install start for '{}'".format(self.family_name))
		try:
			self._patch_sys_drop_route()
		except Exception:
			pass
		try:
			self._cleanup_stale_bookmark_residues_for_owner(self._ui('bookmark_bar'), self.family_name)
		except Exception:
			pass
		self._set_owner_shortcut(self.family_name)
		self._retag_family_children()
		self._prepare_local_templates_for_ui()
		self._cleanup_external_delete_helpers(self.family_name)
		self._configure_delete_op_execute()
		self._install_delete_execute_watcher()
		self._install_toggle()
		self._install_watcher()

		menu_op = self._ui('menu_op')
		node_table = self._ui('node_table')
		self._trace(
			"Install context for '{}': menu_op={} node_table={}".format(
				self.family_name,
				menu_op.path if menu_op else 'None',
				node_table.path if node_table else 'None',
			)
		)

		if not menu_op or not node_table:
			debug("Install aborted: missing menu_op or node_table")
			return False

		self._cleanup_stale_menu_op_residues_for_owner(menu_op, self.family_name)
		self._install_family_insert(menu_op)
		self._update_colors_table(menu_op)
		self._apply_component_color()
		self._prepare_fam_script_callbacks_template()
		self._install_inject_family(node_table)
		self._update_eval4(node_table)
		self._patch_launch_menu_op(menu_op)
		self._cleanup_custom_comp_runners(self.family_name)
		self._patch_create_node(menu_op)
		self._patch_search_exec(menu_op)
		self._install_panel_execute(menu_op)
		self._update_compatible_table(menu_op)
		self._trace("Install steps completed for '{}'".format(self.family_name))

		if show_message:
			self._show_message(self._get_install_message(self._lastInstallWasUpdate), delay_frames=3)

		self._set_recorded_installed_family(self.family_name)
		# Latch par.Install = 1 ONLY at the end of a successful install,
		# so par.Install is a true 'fully installed' flag rather than an
		# 'install in progress' marker. The plugin's
		# _poll_local_then_enable_server polls this par on the first Local
		# family to know when it's safe to enable Server cook.
		try:
			par_install = getattr(self.ownerComp.par, 'Install', None)
			if par_install is not None:
				try:
					par_install.expr = ''
				except Exception:
					pass
				try:
					par_install.bindExpr = ''
				except Exception:
					pass
				par_install.val = 1
		except Exception as e:
			self._trace("par.Install=1 latch failed for '{}': {}".format(self.family_name, e))
		print("{} installation complete".format(self.family_name))
		self._trace("Install finished for '{}'".format(self.family_name))
		return True

	def _retag_family_children(self):
		try:
			for child in self.ownerComp.findChildren(includeUtility=True):
				tags = list(child.tags)
				if 'Custom' in tags and self.family_name not in tags:
					tags = [self.family_name if t == 'Custom' else t for t in tags]
					child.tags = tags
				if child.name == self.CUSTOM_OPERATOR_RUNTIME_EXECUTE_NAME:
					try:
						child.destroy()
					except Exception:
						pass
		except Exception as e:
			self._trace("retag family children failed: {}".format(e))

	def Uninstall(self, family_name=None, reset_trace=True):
		if family_name is not None:
			self.family_name = str(family_name).strip()

		if reset_trace:
			self._reset_trace("Uninstall {}".format(self.family_name if family_name is None else family_name))

		print("Beginning uninstall of {}".format(self.family_name))
		self._trace("Uninstall start for '{}'".format(self.family_name))
		try:
			self.ownerComp.par.Install = 0
			self._lastInstallParameterState = 0
		except Exception:
			pass

		menu_op = self._ui('menu_op')
		node_table = self._ui('node_table')
		bookmark_bar = self._ui('bookmark_bar')
		self._trace("Uninstall context for '{}': bookmark_bar={} menu_op={} node_table={}".format(
			self.family_name,
			bookmark_bar.path if bookmark_bar else 'None',
			menu_op.path if menu_op else 'None',
			node_table.path if node_table else 'None'
		))

		if not menu_op or not node_table:
			debug("Uninstall aborted: missing menu_op or node_table")
			return False

		self._destroy_ui_clones(self.family_name)
		self._cleanup_external_delete_helpers(self.family_name)

		self._set_recorded_installed_family(self.family_name)
		print("{} uninstallation complete".format(self.family_name))
		self._trace("Uninstall finished for '{}'".format(self.family_name))
		return True

	def selfDestroy(self):
		print("Destroying {} installer component".format(self.family_name))
		self.ownerComp.destroy()
		return

	def _install_toggle(self):
		fam_toggle = self._script('fam_toggle')
		bookmark_bar = self._ui('bookmark_bar')
		empty_panel = self._ui('bookmark_empty_panel')

		if not fam_toggle or not bookmark_bar:
			self._trace("Toggle install skipped: fam_toggle={} bookmark_bar={}".format(
				fam_toggle.path if fam_toggle else 'None',
				bookmark_bar.path if bookmark_bar else 'None'
			))
			debug("Toggle install skipped: missing fam_toggle or bookmark_bar")
			return

		toggle_name = self._bookmark_toggle_name()

		# Look for an existing button: exact name first, then known variants.
		# If found with a different name (stale from rename), rename it in-place.
		# Color is stored as a constant (no bindExpr) so renaming never causes a
		# black flash — the value just stays until _apply_color_to_toggle updates it.
		try:
			existing_toggle = bookmark_bar.op(toggle_name)
		except Exception:
			existing_toggle = None

		if existing_toggle is None:
			existing_toggle = self._find_child_by_names(bookmark_bar, self._bookmark_toggle_names())

		if existing_toggle is not None and existing_toggle.name != toggle_name:
			try:
				existing_toggle.name = toggle_name
				self._trace("Renamed button in-place to '{}'".format(toggle_name))
			except Exception as e:
				self._trace("Button rename failed, will copy fresh: {}".format(e))
				self._safe_destroy(existing_toggle)
				existing_toggle = None

		try:
			if existing_toggle is None:
				toggle = bookmark_bar.copy(fam_toggle, name=toggle_name)
				self._trace("Copied bookmark button '{}'".format(toggle_name))
			else:
				toggle = existing_toggle
				self._trace("Reusing bookmark button '{}'".format(toggle.name))

			toggle.allowCooking = True

			try:
				if hasattr(toggle.par, 'opshortcut'):
					toggle.par.opshortcut = self._button_shortcut_name()
			except Exception:
				pass

			self._apply_bookmark_toggle_label(toggle, family_name=self.family_name)
			self._prepare_bookmark_toggle_visuals(toggle)
			self._wire_bookmark_toggle(toggle, empty_panel=empty_panel)

			# Fix parexec1/parexec2: update their Op parameter to ownerComp by absolute
			# path so they never reference a stale op.Custom expression after rename.
			try:
				for exec_name in ('parexec1', 'parexec2'):
					dat = toggle.op(exec_name)
					if dat is None:
						continue
					for par_name in ('Op', 'ops', 'op'):
						par_obj = getattr(dat.par, par_name, None)
						if par_obj is None:
							continue
						try:
							par_obj.bindExpr = ''
						except Exception:
							pass
						try:
							par_obj.expr = ''
						except Exception:
							pass
						try:
							par_obj.val = self.ownerComp.path
						except Exception:
							pass
					try:
						dat.store('cf_owner_path', self.ownerComp.path)
						dat.store('cf_family_name', self.family_name)
					except Exception:
						pass
					dat.allowCooking = False
					dat.allowCooking = True
			except Exception as e:
				self._trace("parexec fix failed for '{}': {}".format(self.family_name, e))

			self._trace("Installed bookmark button '{}' with opshortcut '{}'".format(
				toggle_name,
				self._button_shortcut_name()
			))
		except Exception as e:
			self._trace("Toggle install failed for '{}': {}".format(self.family_name, e), showMessage=True)
			debug("Toggle install failed: {}".format(e))

	def _install_watcher(self):
		"""Copy Watcher_Custom to bookmark_bar and bind its parameters to the family name."""
		fam_watcher = self._script('fam_watcher')
		bookmark_bar = self._ui('bookmark_bar')

		if not fam_watcher or not bookmark_bar:
			self._trace("Watcher install skipped: fam_watcher={} bookmark_bar={}".format(
				fam_watcher.path if fam_watcher else 'None',
				bookmark_bar.path if bookmark_bar else 'None',
			))
			return

		watcher_name = self._watcher_name()
		try:
			existing_watcher = bookmark_bar.op(watcher_name)
		except Exception:
			existing_watcher = None

		# If not found by name, look for a watcher this family installed previously
		# (in-place rename avoids the old watcher firing onDestroy prematurely when
		# opshortcut changes and op.OldName becomes None)
		if existing_watcher is None:
			existing_watcher = self._find_watcher_by_owner_path(bookmark_bar)

		try:
			if existing_watcher is None:
				watcher = bookmark_bar.copy(fam_watcher, name=watcher_name)
				self._trace("Copied watcher '{}'".format(watcher_name))
			else:
				if existing_watcher.name != watcher_name:
					try:
						existing_watcher.name = watcher_name
						self._trace("Renamed watcher in-place '{}' -> '{}'".format(
							existing_watcher.name, watcher_name))
					except Exception as e:
						self._trace("Watcher in-place rename failed: {}".format(e))
				watcher = existing_watcher
				self._trace("Reusing watcher '{}'".format(watcher_name))

			watcher.allowCooking = True

			# Tag the watcher with the family name so it can be found/removed later
			try:
				tags = list(watcher.tags)
				# Remove any old 'Custom' tag and the old family tag, then add current family
				tags = [t for t in tags if t not in ('Custom',)]
				if self.family_name not in tags:
					tags.append(self.family_name)
				watcher.tags = tags
			except Exception as e:
				self._trace("Watcher tag update failed: {}".format(e))

			# Store family_name and owner_path directly on the watcher so opexec1 can
			# derive them even after the family COMP is gone (Level-3 cleanup), and
			# so _find_watcher_by_owner_path can locate this watcher on the next rename.
			try:
				watcher.store('cf_family_name', self.family_name)
				watcher.store('delete_family_name', self.family_name)
				watcher.store('cf_owner_path', self.ownerComp.path)
			except Exception as e:
				self._trace("Watcher store failed: {}".format(e))

			# Bind watcher.par.Op to the family global shortcut (op.FamilyName).
			# TD OP Execute only fires onDestroy reliably with shortcut expressions —
			# not with op('/path') Python calls. The spurious rename-triggered fire is
			# prevented by _safe_destroy (allowCooking=False) properly destroying the
			# old watcher before opshortcut changes.
			try:
				if hasattr(watcher.par, 'Op'):
					watcher.par.Op.bindExpr = ''
					watcher.par.Op.expr = self._owner_bind_expr_op()
					self._trace("Watcher par.Op expr set for '{}': {}".format(
						self.family_name, self._owner_bind_expr_op()))
			except Exception as e:
				self._trace("Watcher par.Op bind failed: {}".format(e))

			# Bind opfind1: cerca dentro /ui
			# Clear bindExpr first — template uses parent().par.Namefilter which may not exist
			try:
				opfind1 = watcher.op('opfind1')
				if opfind1 is not None:
					try:
						opfind1.par.namefilter.bindExpr = ''
					except Exception:
						pass
					opfind1.par.namefilter = '*' + self.family_name
					opfind1.par.tagsfilter = self.family_name
					if hasattr(watcher.par, 'Namefilter'):
						watcher.par.Namefilter = '*' + self.family_name
					opfind1.par.component.expr = ''
					opfind1.par.component.val = '/ui'
					self._trace("Watcher opfind1 bound for '{}': namefilter=*{} component=/ui".format(
						self.family_name, self.family_name))
			except Exception as e:
				self._trace("Watcher opfind1 bind failed: {}".format(e))

			# Bind opfind2: cerca in tutto il progetto (root /)
			try:
				opfind2 = watcher.op('opfind2')
				if opfind2 is not None:
					opfind2.par.namefilter = '*' + self.family_name
					opfind2.par.tagsfilter = self.family_name
					opfind2.par.component.expr = ''
					opfind2.par.component.val = '/'
					self._trace("Watcher opfind2 bound for '{}': component=/".format(self.family_name))
			except Exception as e:
				self._trace("Watcher opfind2 bind failed: {}".format(e))

			self._trace("Installed watcher '{}' for family '{}'".format(watcher_name, self.family_name))

		except Exception as e:
			self._trace("Watcher install failed for '{}': {}".format(self.family_name, e), showMessage=True)
			debug("Watcher install failed: {}".format(e))

	def _find_custom_menu_entry(self, menu_op, managed_only=False):
		if menu_op is None:
			return None
		try:
			candidate = menu_op.op('Custom')
		except Exception:
			candidate = None
		if candidate is None:
			return None
		if managed_only:
			try:
				return candidate if bool(candidate.fetch('cf_managed_family_insert', False)) else None
			except Exception:
				return None
		return candidate

	def _cleanup_stale_menu_op_residues_for_owner(self, menu_op, new_family_name):
		"""Destroy insert_*/panel_execute_* in menu_op that this COMP installed
		under a previous family name (rename residues). Matches by cf_owner_id
		or cf_owner_path stored at install time; preserves nodes whose stored
		cf_managed_family_name equals new_family_name (the one being installed).
		"""
		if menu_op is None:
			return 0

		try:
			owner_id = str(self.ownerComp.id)
		except Exception:
			owner_id = ''
		try:
			owner_path = self.ownerComp.path
		except Exception:
			owner_path = ''
		new_family_name = self._sanitize_family_name(new_family_name)

		if not owner_id and not owner_path:
			return 0

		residue_prefixes = ('insert_', 'panel_execute_')
		residue_suffixes = ('_insert', '_panel_execute')
		removed = 0
		deferred_paths = []

		try:
			children = menu_op.findChildren(depth=None, maxDepth=2)
		except Exception:
			children = []

		for child in children:
			if child is None:
				continue
			try:
				name = str(child.name)
			except Exception:
				continue
			if not (name.startswith(residue_prefixes) or name.endswith(residue_suffixes)):
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

			if managed_family and managed_family == new_family_name:
				continue

			try:
				path = child.path
			except Exception:
				path = None

			try:
				child.allowCooking = False
			except Exception:
				pass
			try:
				child.destroy()
				removed += 1
			except Exception:
				if path:
					deferred_paths.append(path)

		if deferred_paths:
			try:
				run(
					"for p in args:\n    t = op(p)\n    t.destroy() if t is not None else None",
					*deferred_paths,
					delayFrames=2,
				)
			except Exception:
				pass

		if removed or deferred_paths:
			self._trace(
				"Stale menu_op residues cleanup for owner (new family '{}'): removed={} deferred={}".format(
					new_family_name, removed, len(deferred_paths)
				),
				showMessage=True,
			)
		return removed

	def _cleanup_stale_bookmark_residues_for_owner(self, bookmark_bar, new_family_name):
		"""Destroy bookmark clones this COMP installed under a previous family name."""
		if bookmark_bar is None:
			return 0

		try:
			owner_id = str(self.ownerComp.id)
		except Exception:
			owner_id = ''
		try:
			owner_path = self.ownerComp.path
		except Exception:
			owner_path = ''
		new_family_name = self._sanitize_family_name(new_family_name)

		if not owner_id and not owner_path:
			return 0

		residue_prefixes = ('button_', 'delete_execute_', 'watcher_')
		residue_suffixes = ('_button', '_toggle', '_delete_execute', '_watcher')
		removed = 0
		deferred_paths = []

		try:
			children = bookmark_bar.findChildren(depth=None, maxDepth=2)
		except Exception:
			children = []

		for child in children:
			if child is None:
				continue
			try:
				name = str(child.name)
			except Exception:
				continue
			if not (name.startswith(residue_prefixes) or name.endswith(residue_suffixes)):
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
					str(child.fetch('cf_family_name', ''))
				)
			except Exception:
				managed_family = ''

			if managed_family and managed_family == new_family_name:
				continue

			try:
				path = child.path
			except Exception:
				path = None

			try:
				child.allowCooking = False
			except Exception:
				pass
			try:
				child.destroy()
				removed += 1
			except Exception:
				if path:
					deferred_paths.append(path)

		if deferred_paths:
			try:
				run(
					"for p in args:\n    t = op(p)\n    t.destroy() if t is not None else None",
					*deferred_paths,
					delayFrames=2,
				)
			except Exception:
				pass

		if removed or deferred_paths:
			self._trace(
				"Stale bookmark residues cleanup for owner (new family '{}'): removed={} deferred={}".format(
					new_family_name, removed, len(deferred_paths)
				),
				showMessage=True,
			)
		return removed

	def _mark_managed_family_insert(self, family_insert, family_name=None):
		if family_insert is None:
			return False
		try:
			family_insert.store('cf_managed_family_insert', True)
			family_insert.store('cf_managed_family_name', self._sanitize_family_name(family_name or self.family_name))
			try:
				family_insert.store('cf_owner_id', str(self.ownerComp.id))
			except Exception:
				pass
			try:
				family_insert.store('cf_owner_path', self.ownerComp.path)
			except Exception:
				pass
			return True
		except Exception:
			return False

	def _install_family_insert(self, menu_op):
		family_key = self._sanitize_family_name(self.family_name)
		insert_name = self._family_insert_name()
		existing_insert = self._find_child_by_names(menu_op, self._family_insert_names())
		insert1 = self._ui('insert1')
		custom_entry = None
		self._trace(
			"Install family insert start: family='{}' key='{}' existing={} insert1={}".format(
				self.family_name,
				family_key,
				existing_insert.path if existing_insert is not None else 'None',
				insert1.path if insert1 is not None else 'None',
			),
			showMessage=True,
		)

		if family_key == 'Custom':
			# Destroy old bare insertDAT variants (legacy)
			for _old_name in ['insert_Custom', 'Custom_insert', 'Custom']:
				_old = None
				try:
					_old = menu_op.op(_old_name)
				except Exception:
					pass
				if _old is not None:
					try:
						if not getattr(_old, 'isCOMP', False):
							self._safe_destroy(_old)
					except Exception:
						pass
			custom_entry = self._find_child_by_names(menu_op, self._family_insert_names())
			insert_template = self._script('fam_insert')
			try:
				if custom_entry is None:
					if insert_template is not None:
						custom_entry = menu_op.copy(insert_template, name=insert_name)
					else:
						custom_entry = menu_op.create(insertDAT, insert_name)
			except Exception:
				custom_entry = None
			if custom_entry is not None:
				existing_insert = custom_entry
				self._trace(
					"Using Insert_Custom COMP for '{}' -> {}".format(
						self.family_name,
						custom_entry.path,
					),
					showMessage=True,
				)

		if existing_insert is not None and existing_insert.name != insert_name:
			self._trace("Replacing legacy family insert '{}' for '{}'".format(existing_insert.name, self.family_name))
			self._safe_destroy(existing_insert)
			existing_insert = None
			if family_key == 'Custom':
				custom_entry = None

		try:
			if existing_insert is None:
				insert_template = self._script('fam_insert')
				if insert_template is not None:
					family_insert = menu_op.copy(insert_template, name=insert_name)
				else:
					family_insert = menu_op.create(insertDAT, insert_name)
				if family_insert is not None:
					self._mark_managed_family_insert(family_insert, family_name=self.family_name)
			else:
				family_insert = existing_insert
				self._mark_managed_family_insert(family_insert, family_name=self.family_name)

			# Ensure cook is enabled right after the copy/create so the insert
			# starts feeding the menu_op pipeline immediately.
			try:
				if family_insert is not None:
					family_insert.allowCooking = True
			except Exception:
				pass
			# For baseCOMP wrapper (Insert_Custom), configure the inner insertDAT;
			# for a bare insertDAT, configure directly.
			# Try both cases since the inner DAT may be named 'Insert_Custom' or 'insert_Custom'.
			_inner_dat = None
			try:
				_inner_dat = (
					family_insert.op('Insert_Custom') or
					family_insert.op('insert_Custom')
				)
			except Exception:
				pass
			try:
				if _inner_dat is not None:
					new_tags = [t for t in _inner_dat.tags if t != 'Custom']
					if self.family_name not in new_tags:
						new_tags.append(self.family_name)
					_inner_dat.tags = new_tags
			except Exception:
				pass

			# Only configure the inner insertDAT, never the baseCOMP wrapper itself.
			_dat_cfg = _inner_dat if _inner_dat is not None and _inner_dat.isCOMP is False else None
			if _dat_cfg is None and not getattr(family_insert, 'isCOMP', False):
				_dat_cfg = family_insert
			if hasattr(_dat_cfg, 'par'):
				try:
					_dat_cfg.par.insert = 'col'
				except Exception:
					pass
				try:
					_dat_cfg.par.at = 'index'
				except Exception:
					pass
				try:
					_dat_cfg.par.index.expr = ''
					_dat_cfg.par.index.bindExpr = "{}.par.Index".format(self._owner_bind_expr_op())
				except Exception:
					pass
				try:
					_dat_cfg.par.contents = self.family_name
				except Exception:
					pass

			current_input = None
			current_output = None
			try:
				if len(family_insert.inputs) > 0 and family_insert.inputs[0] is not None:
					current_input = family_insert.inputs[0]
			except Exception:
				pass
			try:
				if len(family_insert.outputs) > 0 and family_insert.outputs[0] is not None:
					current_output = family_insert.outputs[0]
			except Exception:
				pass

			if family_key == 'Custom' and custom_entry is not None:
				if current_input is None or current_output is None:
					if insert1 is not None:
						self._trace(
							"Repairing Custom insert '{}' via insert1".format(family_insert.path),
							showMessage=True,
						)
						self._wire_family_insert(insert1, family_insert, menu_op=menu_op)
						self._safe_destroy(insert1)
					else:
						self._trace(
							"Repairing Custom insert '{}' via stored slot".format(family_insert.path),
							showMessage=True,
						)
						self._wire_family_insert_into_slot(menu_op, family_insert)
				else:
					stored_upstream, stored_downstream = self._fetch_family_insert_slot(menu_op)
					if stored_upstream is None and stored_downstream is None:
						self._store_family_insert_slot(menu_op, upstream=current_input, downstream=current_output)
						self._trace(
							"Stored Custom slot for '{}': upstream={} downstream={}".format(
								self.family_name,
								current_input.path if current_input is not None else 'None',
								current_output.path if current_output is not None else 'None',
							),
							showMessage=True,
						)
					if insert1 is not None:
						self._safe_destroy(insert1)
				self._trace("Using built-in Custom insert for '{}'".format(self.family_name), showMessage=True)
				return True

			if insert1 is not None and (current_input is None or current_output is None):
				self._wire_family_insert(insert1, family_insert, menu_op=menu_op)
				self._safe_destroy(insert1)
			elif current_input is None or current_output is None:
				self._wire_family_insert_into_slot(menu_op, family_insert)

			if insert1 is not None:
				family_insert.nodeX = insert1.nodeX
				family_insert.nodeY = insert1.nodeY
			self._trace(
				"Installed family insert '{}' input={} output={}".format(
					insert_name,
					family_insert.inputs[0].path if len(family_insert.inputs) > 0 and family_insert.inputs[0] is not None else 'None',
					family_insert.outputs[0].path if len(family_insert.outputs) > 0 and family_insert.outputs[0] is not None else 'None',
				),
				showMessage=True,
			)
		except Exception as e:
			self._trace("Family insert install failed for '{}': {}".format(self.family_name, e), showMessage=True)
			debug("Family insert install failed: {}".format(e))

	def _remove_legacy_insert1(self, menu_op=None):
		insert1 = self._ui('insert1')
		if insert1 is not None:
			try:
				self._safe_destroy(insert1)
			except Exception:
				pass

		if insert1 is not None:
			self._trace("Removed legacy insert nodes for '{}'".format(self.family_name))
			return True
		return False

	def _update_colors_table(self, menu_op):
		colors_table = self._ui('colors_table')
		if not colors_table:
			self._trace("Colors table missing for '{}'".format(self.family_name))
			return

		# Same stale-cache concern as _sync_button_color: the row we want to
		# update is keyed by family_name, so refresh it from the owner first.
		self._refresh_family_name_from_owner()

		try:
			family_exists = False
			for i in range(colors_table.numRows):
				if colors_table[i, 0].val == "'{}'".format(self.family_name):
					for j in range(1, min(len(self.color) + 1, colors_table.numCols)):
						colors_table[i, j] = self.color[j - 1]
					family_exists = True
					break

			if not family_exists:
				colors_table.appendRow(["'{}'".format(self.family_name)] + list(self.color))
			self._trace("Updated colors table for '{}'".format(self.family_name))
		except Exception as e:
			debug("Colors table update failed: {}".format(e))

	def _apply_component_color(self):
		try:
			for o in self.ownerComp.findChildren(maxDepth=1):
				if 'License' not in o.name and o.OPType != 'annotateCOMP':
					o.color = self.color
			self.ownerComp.color = self.color
			self._trace("Applied component color for '{}'".format(self.family_name))
		except Exception as e:
			debug("Component color application failed: {}".format(e))

	def _install_inject_family(self, node_table):
		families_op = node_table.op('families')
		# NOTE: do NOT force families.bypass = False here. The original .tox
		# ships families as a scriptDAT that errors when the inject chain is
		# the live data path (which is exactly our case once we install custom
		# families). _refresh_external_families_bypass at the end of this
		# method handles the bypass correctly: bypass=1 when any inject_ COMP
		# exists in nodetable so the chain passes through cleanly. Clearing
		# the bind expression is still useful so the value isn't driven by a
		# stale expression after our refresh sets it explicitly.
		try:
			if families_op and hasattr(families_op.par, 'bypass'):
				families_op.par.bypass.expr = ''
		except Exception:
			pass

		inject_name = self._inject_op_name()
		existing_inject = self._find_child_by_names(node_table, self._inject_op_names())
		if existing_inject is not None and existing_inject.name != inject_name:
			self._trace("Replacing legacy inject '{}' for '{}'".format(existing_inject.name, self.family_name))
			self._safe_destroy(existing_inject)
			existing_inject = None
		try:
			if existing_inject is not None and existing_inject.op('switch1') is None:
				self._trace("Replacing non-template inject '{}' for '{}'".format(existing_inject.name, self.family_name))
				self._safe_destroy(existing_inject)
				existing_inject = None
		except Exception:
			pass

		if not families_op:
			debug("Inject family skipped: missing families op")
			return

		try:
			self._cleanup_legacy_families_switch(node_table)
			template_inject = self._get_inject_template()
			if template_inject is None:
				debug("Inject family skipped: missing inject template")
				self._trace("Inject template missing for '{}'".format(self.family_name))
				return
			if existing_inject is None:
				inject_op = node_table.copy(template_inject, name=inject_name, includeDocked=True)
			else:
				inject_op = existing_inject
			# Ensure cook is enabled before wiring/templating so the inject
			# pipeline produces output as soon as it lands in node_table.
			try:
				inject_op.allowCooking = True
			except Exception:
				pass
			self._prepare_inject_template_instance(inject_op)
			tail_inject = None
			try:
				for child in getattr(node_table, 'children', []):
					try:
						if child != inject_op and child.isCOMP and str(child.name).startswith('inject_'):
							if len(child.outputs) > 0 and child.outputs[0] == families_op:
								tail_inject = child
								break
					except Exception:
						pass
			except Exception:
				tail_inject = None
			try:
				if tail_inject is None:
					inject_op.nodeX = families_op.nodeX - 150
					inject_op.nodeY = families_op.nodeY
				else:
					inject_op.nodeX = tail_inject.nodeX - 150
					inject_op.nodeY = tail_inject.nodeY
			except Exception:
				pass

			self._wire_inject_family(families_op, inject_op)
			self._refresh_external_families_bypass(node_table)

			families_op.cook(force=True)
			inject_op.cook(force=True)
			self._trace("Installed inject '{}'".format(inject_name))
		except Exception as e:
			debug("Inject family install failed: {}".format(e))

	def _compose_eval4_expr(self, family_names):
		base_expr = "[x for x in families.keys()]"
		ordered = []
		for family_name in family_names or []:
			family_name = self._sanitize_family_name(family_name)
			if family_name and family_name not in ordered:
				ordered.append(family_name)
		if not ordered:
			return base_expr
		return "{} + [{}]".format(
			base_expr,
			', '.join(["'{}'".format(name) for name in ordered])
		)

	def _read_eval4_families(self, eval4):
		if not eval4:
			return []

		expr = ''
		try:
			expr = str(eval4.par.expr.eval())
		except Exception:
			try:
				expr = str(eval4.par.expr)
			except Exception:
				expr = ''

		families = []
		for match in re.findall(r"'([^']+)'", expr):
			family_name = self._sanitize_family_name(match)
			if family_name and family_name not in families:
				families.append(family_name)
		return families

	def _update_families_bypass(self, node_table, family_names=None):
		return False

	def _update_eval4(self, node_table):
		eval4 = node_table.op('eval4') if node_table else None
		if not eval4:
			self._trace("eval4 missing for '{}'".format(self.family_name))
			return

		try:
			families = self._read_eval4_families(eval4)
			if self.family_name not in families:
				families.append(self.family_name)
			eval4.par.expr = self._compose_eval4_expr(families)
			self._update_families_bypass(node_table, families)
			self._trace("Updated eval4 for '{}' -> {}".format(self.family_name, eval4.par.expr))
		except Exception as e:
			debug("eval4 update failed: {}".format(e))

	def _cleanup_eval4(self, node_table, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		eval4 = node_table.op('eval4') if node_table else None
		if not eval4:
			self._trace("eval4 cleanup skipped for '{}': missing eval4".format(family_name))
			return False

		try:
			families = [name for name in self._read_eval4_families(eval4) if name != family_name]
			eval4.par.expr = self._compose_eval4_expr(families)
			self._update_families_bypass(node_table, families)
			self._trace("Cleaned eval4 for '{}' -> {}".format(family_name, eval4.par.expr))
			return True
		except Exception as e:
			debug("eval4 cleanup failed for '{}': {}".format(family_name, e))
			return False

	def _stable_family_uid(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		checksum = 0
		for index, char in enumerate(family_name):
			checksum += (index + 1) * ord(char)
		return -((checksum % 9000) + 1000)

	def _get_create_node_patch(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		return "if($type=='{}')\n\texit\nendif\n".format(family_name)

	def _cleanup_create_node(self, menu_op, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		create_node = self._ui('create_node')
		if not create_node:
			self._trace("create_node cleanup skipped for '{}': missing create_node".format(family_name))
			return False

		patch = self._get_create_node_patch(family_name)
		removed = 0
		try:
			cancel_patch = "run /ui/dialogs/menu_op/cancel_custom_place\n"
			while cancel_patch in create_node.text:
				create_node.text = create_node.text.replace(cancel_patch, '', 1)
				removed += 1
			while patch in create_node.text:
				create_node.text = create_node.text.replace(patch, '', 1)
				removed += 1
			self._trace("Cleaned create_node for '{}' removed={}".format(family_name, removed))
			return removed > 0
		except Exception as e:
			debug("create_node cleanup failed for '{}': {}".format(family_name, e))
			return False

	def _get_cancel_custom_place_helper_text(self):
		return (
			"clone_path = str(me.fetch('pending_clone_path', '') or '').strip()\n"
			"comp_path = str(me.fetch('pending_component_path', '') or '').strip()\n"
			"comp = op(comp_path) if comp_path else None\n"
			"_cancelled = False\n"
			"if comp is not None:\n"
			"\ttry:\n"
			"\t\text_obj = getattr(comp, 'ComponentEXT', None) or getattr(getattr(comp, 'ext', None), 'ComponentEXT', None)\n"
			"\texcept Exception:\n"
			"\t\text_obj = None\n"
			"\tif ext_obj is not None:\n"
			"\t\ttry:\n"
			"\t\t\t_cancelled = bool(ext_obj.CancelPendingPlacement(True))\n"
			"\t\texcept Exception:\n"
			"\t\t\t_cancelled = False\n"
			"if not _cancelled:\n"
			"\tclone = op(clone_path) if clone_path else None\n"
			"\tif clone is not None:\n"
			"\t\ttry:\n"
			"\t\t\tclone.destroy()\n"
			"\t\texcept Exception:\n"
			"\t\t\tpass\n"
			"me.store('pending_clone_path', '')\n"
			"me.store('pending_component_path', '')\n"
		)

	def _ensure_cancel_custom_place_helper(self, menu_op=None):
		menu_op = menu_op or self._ui('menu_op')
		if menu_op is None:
			return None

		try:
			helper = menu_op.op('cancel_custom_place')
		except Exception:
			helper = None

		try:
			if helper is None:
				helper = menu_op.create(textDAT, 'cancel_custom_place')
		except Exception as e:
			self._trace("cancel_custom_place helper create failed: {}".format(e))
			return None

		if helper is None:
			return None

		try:
			desired_text = self._get_cancel_custom_place_helper_text()
			if helper.text != desired_text:
				helper.text = desired_text
		except Exception:
			pass

		try:
			if hasattr(helper.par, 'language'):
				helper.par.language = 'python'
		except Exception:
			pass
		try:
			if not str(helper.fetch('pending_clone_path', '') or '').strip():
				helper.store('pending_component_path', '')
		except Exception:
			pass

		try:
			create_node = self._ui('create_node')
			helper.nodeX = create_node.nodeX - 140 if create_node is not None else 0
			helper.nodeY = create_node.nodeY - 60 if create_node is not None else 0
		except Exception:
			pass

		return helper

	def _cleanup_launch_menu_op(self, menu_op):
		launch_menu_op = self._ui('launch_menu_op')
		if not launch_menu_op:
			return False
		patch = "run /ui/dialogs/menu_op/cancel_custom_place\n"
		removed = 0
		try:
			while patch in launch_menu_op.text:
				launch_menu_op.text = launch_menu_op.text.replace(patch, '', 1)
				removed += 1
			return removed > 0
		except Exception:
			return False

	def _patch_launch_menu_op(self, menu_op):
		launch_menu_op = self._ui('launch_menu_op')
		if not launch_menu_op:
			return
		self._ensure_cancel_custom_place_helper(menu_op)
		patch = "run /ui/dialogs/menu_op/cancel_custom_place\n"
		try:
			while patch in launch_menu_op.text:
				launch_menu_op.text = launch_menu_op.text.replace(patch, '', 1)
			launch_menu_op.text = patch + launch_menu_op.text
		except Exception as e:
			debug("launch_menu_op patch failed: {}".format(e))

	def _patch_create_node(self, menu_op):
		create_node = self._ui('create_node')
		if not create_node:
			self._trace("create_node missing for '{}'".format(self.family_name))
			return

		insertion_key = 'set type = `tab("current",0,0)`\n'
		cancel_patch = "run /ui/dialogs/menu_op/cancel_custom_place\n"
		try:
			while cancel_patch in create_node.text:
				create_node.text = create_node.text.replace(cancel_patch, '', 1)
		except Exception:
			pass

		patch = self._get_create_node_patch(self.family_name)
		if patch in create_node.text:
			self._trace("create_node already patched for '{}'".format(self.family_name))
			return

		try:
			if insertion_key in create_node.text:
				idx = create_node.text.index(insertion_key) + len(insertion_key)
				create_node.text = create_node.text[:idx] + patch + create_node.text[idx:]
				self._trace("Patched create_node for '{}'".format(self.family_name))
		except Exception as e:
			debug("create_node patch failed: {}".format(e))

	def _get_search_exec_patch(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		unique_id = self._stable_family_uid(family_name)
		start_marker = "# CUSTOM_FAMILY_SEARCH_BEGIN:{}".format(family_name)
		end_marker = "# CUSTOM_FAMILY_SEARCH_END:{}".format(family_name)
		return (
			"\t\t\t{start_marker}\n"
			"\t\t\tif(op('/ui/dialogs/menu_op/current')[0,0].val=='{family}'):\n"
			"\t\t\t\t_family_op = getattr(op, '{family}', None)\n"
			"\t\t\t\t_op_fam = _family_op.op('OP_fam') if _family_op is not None else None\n"
			"\t\t\t\t_destil = parent.OPCREATE.op('nodetable/destil')\n"
			"\t\t\t\t_has_family_match = False\n"
			"\t\t\t\tif _op_fam is not None and _destil is not None:\n"
			"\t\t\t\t\t_family_names = [str(_op_fam[_r,'name'].val) for _r in range(1, _op_fam.numRows) if str(_op_fam[_r,'name'].val).strip()]\n"
			"\t\t\t\t\tfor _r in range(1, _destil.numRows):\n"
			"\t\t\t\t\t\tif str(_destil[_r,0].val) in _family_names:\n"
			"\t\t\t\t\t\t\t_has_family_match = True\n"
			"\t\t\t\t\t\t\tbreak\n"
			"\t\t\t\tif _has_family_match:\n"
			"\t\t\t\t\tparent.OPCREATE.op('nodetable').clickID({uid})\n"
			"\t\t\t\t\treturn\n"
			"\t\t\t{end_marker}\n"
		).format(
			family=family_name,
			uid=unique_id,
			start_marker=start_marker,
			end_marker=end_marker,
		)

	def _cleanup_search_exec(self, menu_op, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		search_exec = self._ui('search_exec')
		if not search_exec:
			self._trace("search_exec cleanup skipped for '{}': missing search_exec".format(family_name))
			return False

		try:
			old_pattern = re.compile(
				r"\t\t\tif\(op\('/ui/dialogs/menu_op/current'\)\[0,0\]\.val=='{}'\):\n\t\t\t\tparent\.OPCREATE\.op\('nodetable'\)\.clickID\(-?\d+\)\n\t\t\t\treturn\n".format(re.escape(family_name))
			)
			marker_pattern = re.compile(
				r"\t\t\t# CUSTOM_FAMILY_SEARCH_BEGIN:{}\n.*?\t\t\t# CUSTOM_FAMILY_SEARCH_END:{}\n".format(
					re.escape(family_name),
					re.escape(family_name)
				),
				re.DOTALL
			)
			new_text, old_count = old_pattern.subn('', search_exec.text)
			new_text, marker_count = marker_pattern.subn('', new_text)
			count = old_count + marker_count
			if count > 0 and new_text != search_exec.text:
				search_exec.text = new_text
			self._trace("Cleaned search_exec for '{}' removed={}".format(family_name, count))
			return count > 0
		except Exception as e:
			debug("search_exec cleanup failed for '{}': {}".format(family_name, e))
			return False

	def _reset_menu_current_family(self, family_name=None):
		family_name = self._sanitize_family_name(family_name or self.family_name)
		current_dat = op('/ui/dialogs/menu_op/current')
		family_panel = op('/ui/dialogs/menu_op/families/family')
		reset_target = 'TOP'
		panel_reset = False
		current_reset = False

		try:
			if family_panel is not None:
				family_panel.panel.cellradioid = 0
				panel_reset = True
		except Exception as e:
			self._trace("menu current reset panel failed for '{}': {}".format(family_name, e))

		try:
			if current_dat is not None and current_dat.numRows > 0 and current_dat.numCols > 0:
				current_before = str(current_dat[0, 0].val)
				if current_before == family_name or not current_before:
					current_dat[0, 0] = reset_target
					current_reset = True
				self._trace("menu current reset for '{}': before='{}' after='{}' panel_reset={} current_reset={}".format(
					family_name,
					current_before,
					current_dat[0, 0].val,
					panel_reset,
					current_reset
				))
				return panel_reset or current_reset
		except Exception as e:
			self._trace("menu current reset failed for '{}': {}".format(family_name, e))
			return panel_reset

		self._trace("menu current reset skipped for '{}': current_dat={} panel_reset={} current_reset={}".format(
			family_name,
			current_dat.path if current_dat else 'None',
			panel_reset,
			current_reset
		))
		return panel_reset or current_reset

	def _patch_search_exec(self, menu_op):
		search_exec = self._ui('search_exec')
		if not search_exec:
			self._trace("search_exec missing for '{}'".format(self.family_name))
			return

		self._cleanup_search_exec(menu_op, family_name=self.family_name)
		patch = self._get_search_exec_patch(self.family_name)
		if patch in search_exec.text:
			self._trace("search_exec already patched for '{}'".format(self.family_name))
			return

		key = "if parent.OPCREATE.op('nodetable/destil').numRows > 1:\n"
		try:
			if key in search_exec.text:
				idx = search_exec.text.index(key) + len(key)
				search_exec.text = search_exec.text[:idx] + patch + search_exec.text[idx:]
				self._trace("Patched search_exec for '{}'".format(self.family_name))
		except Exception as e:
			debug("search_exec patch failed: {}".format(e))

	def _install_panel_execute(self, menu_op):
		panel_execute_name = self._panel_execute_name()
		existing_panel_execute = self._find_child_by_names(menu_op, self._panel_execute_names())
		if existing_panel_execute is not None and existing_panel_execute.name != panel_execute_name:
			self._trace("Replacing legacy panel execute '{}' for '{}'".format(existing_panel_execute.name, self.family_name))
			self._safe_destroy(existing_panel_execute)
			existing_panel_execute = None

		template = self._script('fam_panel_execute')
		node_script = self._ui('node_script')

		if not template or not node_script:
			debug("Panel execute install skipped: missing template or node_script")
			return

		try:
			if existing_panel_execute is None:
				panel_execute = menu_op.copy(template, name=panel_execute_name)
			else:
				panel_execute = existing_panel_execute
			# Ensure cook is enabled right after the copy so the panel execute
			# starts intercepting events from menu_op immediately.
			try:
				panel_execute.allowCooking = True
			except Exception:
				pass
			try:
				panel_execute.store('cf_managed_panel_execute', True)
				panel_execute.store('cf_managed_family_name', self._sanitize_family_name(self.family_name))
				panel_execute.store('cf_owner_id', str(self.ownerComp.id))
				panel_execute.store('cf_owner_path', self.ownerComp.path)
			except Exception:
				pass
			panel_execute.nodeX = node_script.nodeX
			panel_execute.nodeY = node_script.nodeY + 100

			unique_id = self._stable_family_uid(self.family_name)

			# New structure: panel_execute_Custom is a baseCOMP wrapping a panelexecuteDAT.
			# Try to find the inner DAT first; fall back to the op itself (legacy DAT).
			inner_dat = None
			try:
				inner_dat = panel_execute.op('panel_execute_Custom')
			except Exception:
				pass
			target = inner_dat if inner_dat is not None else panel_execute
			try:
				target.text = target.text.replace('OPNAME', self.family_name).replace('Custom_family_installer', self.family_name).replace('-9999', str(unique_id))
			except Exception as e:
				debug("Panel execute text patch failed: {}".format(e))

			try:
				if inner_dat is not None:
					new_tags = [t for t in inner_dat.tags if t != 'Custom']
					if self.family_name not in new_tags:
						new_tags.append(self.family_name)
					inner_dat.tags = new_tags
			except Exception:
				pass

			self._trace("Installed panel execute '{}'".format(panel_execute_name))
		except Exception as e:
			debug("Panel execute install failed: {}".format(e))

	def _update_compatible_table(self, menu_op):
		comp_table = self._ui('compatible_table')
		if not comp_table:
			self._trace("Compatible table missing for '{}'".format(self.family_name))
			return

		# TD's OP Create Dialog uses this table to decide which operators show
		# in each tab. A blank cell at [menu_type, op_type] makes the dialog
		# think the pairing is "allowed" (no explicit incompatibility), which
		# breaks the operator list once a custom family is added. The shipped
		# 'Custom' row/col is filled entirely with 'x' to mark a custom family
		# as incompatible with every built-in family — and with any other
		# custom family. Mirror that convention here for every new family so
		# adding HOP doesn't silently leave empty cells on the HOP row, on the
		# HOP column, and on the Custom×HOP / HOP×Custom intersections.
		try:
			if not comp_table.rows(self.family_name):
				row_entry = [self.family_name] + ['x'] * (comp_table.numCols - 1)
				comp_table.appendRow(row_entry)

			if not comp_table.cols(self.family_name):
				col_entry = [self.family_name] + ['x'] * (comp_table.numRows - 1)
				comp_table.appendCol(col_entry)

			# Backfill any cell on the new row / new column that other previous
			# installs (or the legacy buggy code) left empty. Idempotent: only
			# touches cells that are currently empty so manually-tuned
			# compatibility entries are preserved.
			self._backfill_compatible_blanks(comp_table, self.family_name)

			self._trace("Updated compatible table for '{}'".format(self.family_name))
		except Exception as e:
			debug("Compatible table update failed: {}".format(e))

	def _backfill_compatible_blanks(self, comp_table, family_name):
		"""Fill empty cells on family_name's row/col with 'x' so the OP Create
		Dialog doesn't treat them as a valid compatibility entry.
		"""
		family_name = self._sanitize_family_name(family_name)
		if not family_name:
			return

		try:
			row_cells = comp_table.row(family_name)
		except Exception:
			row_cells = None
		try:
			col_cells = comp_table.col(family_name)
		except Exception:
			col_cells = None

		def _fill(cells):
			if not cells:
				return
			# Skip index 0 (the header cell carrying the family name itself).
			for cell in cells[1:]:
				try:
					if str(cell.val) == '':
						cell.val = 'x'
				except Exception:
					pass

		_fill(row_cells)
		_fill(col_cells)

	def _remove_color_row(self, menu_op, family_name=None):
		family_name = family_name or self.family_name
		colors_table = self._ui('colors_table')
		if not colors_table:
			self._trace("Color row cleanup skipped, table missing for '{}'".format(family_name))
			return

		try:
			for i in range(colors_table.numRows):
				if colors_table[i, 0].val == "'{}'".format(family_name):
					colors_table.deleteRow(i)
					self._trace("Removed color row for '{}'".format(family_name))
					break
		except Exception as e:
			debug("Color row removal failed: {}".format(e))

	def _remove_compatible_entries(self, menu_op, family_name=None):
		family_name = family_name or self.family_name
		comp_table = self._ui('compatible_table')
		if not comp_table:
			self._trace("Compatible cleanup skipped, table missing for '{}'".format(family_name))
			return

		try:
			if comp_table.rows(family_name):
				comp_table.deleteRow(family_name)
				self._trace("Removed compatible row for '{}'".format(family_name))
		except Exception as e:
			debug("Compatible row removal failed: {}".format(e))

		try:
			if comp_table.cols(family_name):
				comp_table.deleteCol(family_name)
				self._trace("Removed compatible column for '{}'".format(family_name))
		except Exception as e:
			debug("Compatible col removal failed: {}".format(e))

InstallerEXT = GenericInstallerEXT












