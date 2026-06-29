# AEOP - After Effects side installer
# =====================================================================
# This is the callbacks file for a Parameter Execute DAT living inside the
# Base COMP named "Installer" (inside the AEOP component).
#
# SETUP (in TouchDesigner):
#   1. Base COMP "Installer" gets a custom PULSE parameter named "Install"
#      (par internal name: 'Install').
#   2. A Parameter Execute DAT inside it, with:
#        - "Parameters" / op = the Base itself (parent())  -> "../" or "."
#        - watch the custom page (Pulse = On)
#        - DAT text synced to this file.
#   3. Press the "Install" pulse -> onPulse() runs the AE install.
#
# WHAT IT DOES (minimal, no antivirus assistant):
#   - copies the CEP panel to %APPDATA%\Adobe\CEP\extensions  (per-user)
#   - sets PlayerDebugMode=1 in HKCU (CSXS 9-12) so the unsigned panel loads
#   - copies AELayerSpout.aex into every detected AE version's Program Files
#     Plug-ins folder via ONE elevated cmd.exe (single UAC prompt)
#   - if antivirus blocks the unsigned .aex, shows a static message naming
#     the folders to whitelist (then re-press Install)
#
# Source files are read from the on-disk install:
#   {app.preferencesFolder}\Custom families\AEOP\AE plugins\
# (cross-platform prefs folder; the user name is never hardcoded).
#
# Fully defensive: every step is wrapped, so a failure is logged via debug()
# and never raises out of the callback.
# =====================================================================

import os
import shutil

SCRIPTS_DISK_ROOT = os.path.join(app.preferencesFolder, 'Custom families')
PLUGINS_SRC = os.path.join(SCRIPTS_DISK_ROOT, 'AEOP', 'AE plugins')
AEX_NAME = 'AELayerSpout.aex'
PANEL_NAME = 'com.aeop.nullosc'
INSTALL_PAR = 'Install'


def onPulse(par):
	if par.name == INSTALL_PAR:
		_install_after_effects()
	return


def _install_after_effects():
	"""Install the After Effects side of AEOP. Never raises."""
	try:
		import winreg, time
		aex_src = os.path.join(PLUGINS_SRC, AEX_NAME)
		panel_src = os.path.join(PLUGINS_SRC, 'AE Panel', PANEL_NAME)

		# GUARD: do nothing unless a real After Effects install is present.
		plug_dirs = _ae_plugin_dirs()
		if not plug_dirs:
			_message("After Effects non trovato: niente da installare.")
			debug('[AEOP install] After Effects not found; skipping.')
			return

		appdata = os.environ.get('APPDATA')

		# 1) CEP panel -> per-user extensions (no elevation).
		if appdata and os.path.isdir(panel_src):
			try:
				ext_dir = os.path.join(appdata, 'Adobe', 'CEP', 'extensions')
				dest = os.path.join(ext_dir, PANEL_NAME)
				os.makedirs(ext_dir, exist_ok=True)
				if os.path.isdir(dest):
					shutil.rmtree(dest, ignore_errors=True)
				shutil.copytree(panel_src, dest)
				debug('[AEOP install] panel -> ' + dest)
			except Exception as exc:
				debug('[AEOP install] panel copy failed: {}'.format(exc))

		# 2) PlayerDebugMode=1 (HKCU) so the unsigned CEP panel can load.
		try:
			for v in (9, 10, 11, 12):
				k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Software\\Adobe\\CSXS.{}'.format(v))
				winreg.SetValueEx(k, 'PlayerDebugMode', 0, winreg.REG_SZ, '1')
				winreg.CloseKey(k)
			debug('[AEOP install] PlayerDebugMode=1 (CSXS 9-12)')
		except Exception as exc:
			debug('[AEOP install] registry failed: {}'.format(exc))

		# 3) Effect .aex -> each AE version's Plug-ins (Program Files: 1 UAC).
		if not os.path.isfile(aex_src):
			_message("File effetto mancante:\n" + aex_src + "\nReinstalla Custom families.")
			return
		try:
			_elevate_copy_to_plugins(aex_src, plug_dirs)
		except Exception as exc:
			debug('[AEOP install] elevated copy failed: {}'.format(exc))
		try:
			time.sleep(2)   # give a real-time antivirus a moment to act, if it will
		except Exception:
			pass

		blocked = []
		for d in plug_dirs:
			if os.path.isfile(os.path.join(d, AEX_NAME)):
				debug('[AEOP install] effect -> ' + d)
			else:
				blocked.append(d)
				debug('[AEOP install] BLOCKED (antivirus?): ' + d)

		if blocked:
			nlc = chr(10)
			_message(
				"Il plugin di After Effects (" + AEX_NAME + ") e' stato bloccato "
				"dall'antivirus e non e' stato installato in:" + nlc + nlc +
				nlc.join(blocked) + nlc + nlc +
				"Aggiungi un'eccezione per queste cartelle (o metti in pausa "
				"gli scudi dell'antivirus), poi premi di nuovo Install.")
		else:
			_message("Plugin di After Effects installato correttamente.\n"
			         "Riavvia After Effects per caricarlo.")
		debug('[AEOP install] done (restart After Effects to load).')
	except Exception as exc:
		try:
			debug('[AEOP install] install error (ignored): {}'.format(exc))
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
		debug('[AEOP install] plugin-dir scan failed: {}'.format(exc))
	return dirs


def _elevate_copy_to_plugins(aex_src, plug_dirs):
	"""Copy aex_src into each plug dir via ONE elevated cmd.exe (UAC), waiting
	for it to finish (ShellExecuteEx 'runas', hidden window)."""
	import ctypes
	from ctypes import wintypes
	parts = []
	for d in plug_dirs:
		dst = os.path.join(d, AEX_NAME)
		parts.append('copy /Y "{}" "{}"'.format(aex_src, dst))
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


# ---- Parameter Execute DAT stubs (required signatures) ----

def onValueChange(par, prev):
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return
