# AEOP - After Effects side UNINSTALLER
# =====================================================================
# Callbacks file for the Parameter Execute DAT inside the Base COMP
# "Uninstaller" (inside the AEOP component). Counterpart of the
# "Installer" base / install_ae.py.
#
# SETUP (in TouchDesigner):
#   1. Base COMP "Uninstaller" gets a custom PULSE parameter named
#      "Uninstall" (par internal name: 'Uninstall').
#   2. A Parameter Execute DAT inside it, with:
#        - "Parameters" / op = the Base itself (parent())  -> "../" or "."
#        - watch the custom page (Pulse = On)
#        - DAT text synced to this file (Sync to File / Load on Start).
#   3. Press the "Uninstall" pulse -> onPulse() runs the AE uninstall.
#
# WHAT IT DOES (undoes install_ae.py, minimal):
#   - removes the CEP panel from %APPDATA%\Adobe\CEP\extensions
#   - removes AELayerSpout.aex from every detected AE version's Program
#     Files Plug-ins folder via ONE elevated cmd.exe (single UAC prompt)
#   - leaves PlayerDebugMode untouched on purpose (shared global flag;
#     removing it could break other CEP extensions). An optional removal
#     block is provided below, commented out.
#
# Does NOT delete the on-disk AEOP framework folder - that belongs to the
# Custom families uninstaller. This only reverses the AE-side hookup.
#
# Fully defensive: every step is wrapped, so a failure is logged via
# debug() and never raises out of the callback.
# =====================================================================

import os
import shutil

PANEL_NAME = 'com.aeop.nullosc'
AEX_NAME = 'AELayerSpout.aex'
UNINSTALL_PAR = 'Uninstall'


# =====================================================================
# Parameter Execute DAT callbacks (full standard set - keep all of them).
#   me   - this DAT
#   par  - the Par object that changed
#   val  - the current value of the par
#   prev - the previous value of the par
# Only onPulse is wired; the rest are required template stubs.
# =====================================================================

def onValueChange(par, prev):
	return

def onPulse(par):
	if par.name == UNINSTALL_PAR:
		_uninstall_after_effects()
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return


# =====================================================================
# Uninstall implementation
# =====================================================================

def _uninstall_after_effects():
	"""Remove the After Effects side of AEOP. Never raises."""
	try:
		removed_any = False

		# 1) CEP panel -> remove from per-user extensions (no elevation).
		appdata = os.environ.get('APPDATA')
		if appdata:
			dest = os.path.join(appdata, 'Adobe', 'CEP', 'extensions', PANEL_NAME)
			if os.path.isdir(dest):
				try:
					shutil.rmtree(dest, ignore_errors=True)
					if not os.path.isdir(dest):
						removed_any = True
						debug('[AEOP uninstall] panel removed -> ' + dest)
					else:
						debug('[AEOP uninstall] panel still present: ' + dest)
				except Exception as exc:
					debug('[AEOP uninstall] panel remove failed: {}'.format(exc))

		# 2) Effect .aex -> remove from each AE Plug-ins (Program Files: 1 UAC).
		plug_dirs = _ae_plugin_dirs()
		present = [d for d in plug_dirs
		          if os.path.isfile(os.path.join(d, AEX_NAME))]
		if present:
			try:
				_elevate_delete_from_plugins(present)
			except Exception as exc:
				debug('[AEOP uninstall] elevated delete failed: {}'.format(exc))
			remaining = []
			for d in present:
				if os.path.isfile(os.path.join(d, AEX_NAME)):
					remaining.append(d)
					debug('[AEOP uninstall] NOT removed: ' + os.path.join(d, AEX_NAME))
				else:
					removed_any = True
					debug('[AEOP uninstall] effect removed -> ' + d)
			if remaining:
				nlc = chr(10)
				_message(
					"Non sono riuscito a rimuovere " + AEX_NAME + " da:" + nlc + nlc +
					nlc.join(remaining) + nlc + nlc +
					"Chiudi After Effects (potrebbe tenere il file in uso) e riprova.")
				return

		# 3) PlayerDebugMode -> left in place on purpose (shared global). To
		#    also reset it, uncomment this block:
		# try:
		# 	import winreg
		# 	for v in (9, 10, 11, 12):
		# 		try:
		# 			winreg.DeleteValue(
		# 				winreg.OpenKey(winreg.HKEY_CURRENT_USER,
		# 				               'Software\\Adobe\\CSXS.{}'.format(v), 0,
		# 				               winreg.KEY_SET_VALUE),
		# 				'PlayerDebugMode')
		# 		except FileNotFoundError:
		# 			pass
		# 	debug('[AEOP uninstall] PlayerDebugMode removed (CSXS 9-12)')
		# except Exception as exc:
		# 	debug('[AEOP uninstall] registry cleanup failed: {}'.format(exc))

		if removed_any:
			_message("Plugin di After Effects rimosso.\n"
			         "Riavvia After Effects per applicare la rimozione.")
		else:
			_message("Niente da rimuovere: il plugin di After Effects non risulta installato.")
		debug('[AEOP uninstall] done.')
	except Exception as exc:
		try:
			debug('[AEOP uninstall] uninstall error (ignored): {}'.format(exc))
		except Exception:
			pass


def _ae_plugin_dirs():
	"""Support Files/Plug-ins folder of every real AE install in Program Files."""
	dirs = []
	try:
		pf = os.environ.get('ProgramFiles', r'C:\Program Files')
		adobe = os.path.join(pf, 'Adobe')
		if os.path.isdir(adobe):
			for name in os.listdir(adobe):
				if name.lower().startswith('adobe after effects'):
					plug = os.path.join(adobe, name, 'Support Files', 'Plug-ins')
					if os.path.isdir(plug):
						dirs.append(plug)
	except Exception as exc:
		debug('[AEOP uninstall] plugin-dir scan failed: {}'.format(exc))
	return dirs


def _elevate_delete_from_plugins(plug_dirs):
	"""Delete AELayerSpout.aex from each plug dir via ONE elevated cmd.exe
	(UAC), waiting for it to finish (ShellExecuteEx 'runas', hidden window)."""
	import ctypes
	from ctypes import wintypes
	parts = []
	for d in plug_dirs:
		dst = os.path.join(d, AEX_NAME)
		parts.append('del /F /Q "{}"'.format(dst))
	params = '/c ' + ' & '.join(parts)

	class SHELLEXECUTEINFO(ctypes.Structure):
		_fields_ = [('cbSize', wintypes.DWORD), ('fMask', ctypes.c_ulong),
		            ('hwnd', wintypes.HWND), ('lpVerb', wintypes.LPCWSTR),
		            ('lpFile', wintypes.LPCWSTR), ('lpParameters', wintypes.LPCWSTR),
		            ('lpDirectory', wintypes.LPCWSTR), ('nShow', ctypes.c_int),
		            ('hInstApp', wintypes.HINSTANCE), ('lpIDList', ctypes.c_void_p),
		            ('lpClass', wintypes.LPCWSTR), ('hkeyClass', wintypes.HKEY),
		            ('dwHotKey', wintypes.DWORD), ('hIcon', wintypes.HANDLE),
		            ('hProcess', wintypes.HANDLE)]
	sei = SHELLEXECUTEINFO()
	sei.cbSize = ctypes.sizeof(sei)
	sei.fMask = 0x00000040   # SEE_MASK_NOCLOSEPROCESS
	sei.lpVerb = 'runas'
	sei.lpFile = 'cmd.exe'
	sei.lpParameters = params
	sei.nShow = 0            # SW_HIDE
	if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
		raise OSError('ShellExecuteExW runas failed')
	if sei.hProcess:
		ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 30000)
		ctypes.windll.kernel32.CloseHandle(sei.hProcess)


def _message(text):
	"""Deferred message box so the callback stack unwinds first."""
	run("ui.messageBox('Custom families - After Effects', {!r})".format(text), delayFrames=1)
