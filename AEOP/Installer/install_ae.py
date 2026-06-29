# AEOP - After Effects side INSTALLER (with live progress window)
# =====================================================================
# Callbacks file for the Parameter Execute DAT inside the Base COMP
# "Installer" (inside the AEOP component).
#
# SETUP (in TouchDesigner):
#   1. Base COMP "Installer" gets a custom PULSE parameter named "Install".
#   2. A Parameter Execute DAT inside it, watching the Base (op = "..") with
#      Pulse = On, DAT text synced to this file (Sync to File / Load on Start).
#   3. Press "Install" -> onPulse() runs the AE install and opens a live
#      progress window (progress bar + current action + final friendly recap).
#
# WHAT IT DOES: copies the CEP panel (per-user), sets PlayerDebugMode (HKCU),
# copies AELayerSpout.aex into every detected AE Program Files Plug-ins folder
# via ONE elevated cmd.exe. Reads sources from
# {app.preferencesFolder}\Custom families\AEOP\AE plugins.
#
# Fully defensive: never raises out of the callback; if the window can't be
# built it falls back to a messageBox recap.
# =====================================================================

import os
import shutil

SCRIPTS_DISK_ROOT = os.path.join(app.preferencesFolder, 'Custom families')
PLUGINS_SRC = os.path.join(SCRIPTS_DISK_ROOT, 'AEOP', 'AE plugins')
AEX_NAMES = ('AELayerSpout.aex',)   # AE plugins to install (effect for the TOP)
PANEL_NAME = 'com.aeop.nullosc'
INSTALL_PAR = 'Install'
WINDOW_TITLE = 'AEOP - Installazione After Effects'

# --- runtime state (module globals persist between deferred frames) ---
_DAT_PATH = ''
_BASE_PATH = ''
_WIN = None
_STEPS = []
_RESULTS = []
_PLUG_DIRS = []
_BLOCKED = []
_RUNNING = False


# =====================================================================
# Parameter Execute DAT callbacks (full standard set - keep all of them).
#   me / par / val / prev.  Only onPulse is wired.
# =====================================================================

def onValueChange(par, prev):
	return

def onPulse(par):
	if par.name == INSTALL_PAR:
		_start()
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
# Orchestration (one step per frame so the window repaints live)
# =====================================================================

def _start():
	global _DAT_PATH, _BASE_PATH, _WIN, _STEPS, _RESULTS, _PLUG_DIRS, _BLOCKED, _RUNNING
	if _RUNNING:
		return
	_RUNNING = True
	_DAT_PATH = me.path
	_BASE_PATH = me.parent().path
	_RESULTS = []
	_PLUG_DIRS = []
	_BLOCKED = []
	_STEPS = [
		('Controllo di After Effects', _step_detect),
		('Installazione del pannello', _step_panel),
		('Configurazione di After Effects', _step_registry),
		("Copia dell'effetto (conferma di Windows)", _step_effect),
	]
	try:
		_WIN = _ProgressWindow(WINDOW_TITLE, len(_STEPS))
	except Exception as exc:
		debug('[AEOP install] window build failed (fallback to messagebox): {}'.format(exc))
		_WIN = None
	_show_step(0)


def _show_step(i):
	try:
		if _WIN:
			_WIN.set_doing(_STEPS[i][0], i)
	except Exception:
		pass
	run("op({!r}).module._do_step({})".format(_DAT_PATH, i), delayFrames=2)


def _do_step(i):
	label, fn = _STEPS[i]
	ok, note = True, ''
	try:
		ok, note = fn()
	except Exception as exc:
		ok, note = False, 'errore imprevisto'
		debug('[AEOP install] step "{}" error: {}'.format(label, exc))
	try:
		if _WIN:
			_WIN.mark(label, ok, note, i + 1)
	except Exception:
		pass
	_RESULTS.append((label, ok, note))
	debug('[AEOP install] {} -> {}{}'.format(label, 'OK' if ok else 'FAIL',
	                                          (' (' + note + ')') if note else ''))
	last = (i + 1) >= len(_STEPS)
	abort = (i == 0 and not ok)   # no AE found -> stop early
	if last or abort:
		run("op({!r}).module._finish()".format(_DAT_PATH), delayFrames=1)
	else:
		run("op({!r}).module._show_step({})".format(_DAT_PATH, i + 1), delayFrames=1)


def _finish():
	global _RUNNING
	try:
		if not _PLUG_DIRS:
			headline = 'After Effects non trovato'
			footer = ("Non risulta installato After Effects, quindi non c'e' nulla da "
			          "installare.\nInstalla After Effects e premi di nuovo Install.")
		elif _BLOCKED:
			headline = "ATTENZIONE - l'effetto e' stato bloccato"
			footer = ("Pannello e configurazione sono a posto, ma l'antivirus ha "
			          "impedito la copia dell'effetto.\n"
			          "Come risolvere:\n"
			          "  1) Apri l'antivirus e metti in PAUSA gli scudi per ~10 minuti\n"
			          "  2) Premi di nuovo il pulsante Install\n"
			          "Cartelle interessate:\n  " + "\n  ".join(_BLOCKED))
		else:
			headline = 'TUTTO OK - installazione completata!'
			footer = ("Il plugin per After Effects e' pronto.\n"
			          "Chiudi e riapri After Effects: troverai l'effetto 'AELayerSpout'.")
		if _WIN:
			_WIN.finish(headline, footer)
		else:
			_message(headline + "\n\n" + footer)
		debug('[AEOP install] DONE - ' + headline)
	finally:
		_RUNNING = False


# =====================================================================
# Steps (each returns (ok: bool, note: str))
# =====================================================================

def _step_detect():
	global _PLUG_DIRS
	_PLUG_DIRS = _ae_plugin_dirs()
	if not _PLUG_DIRS:
		return False, 'non installato'
	return True, ', '.join(_ae_version_label(d) for d in _PLUG_DIRS)


def _step_panel():
	appdata = os.environ.get('APPDATA')
	panel_src = os.path.join(PLUGINS_SRC, 'AE Panel', PANEL_NAME)
	if not appdata or not os.path.isdir(panel_src):
		return False, 'sorgente del pannello mancante'
	dest = os.path.join(appdata, 'Adobe', 'CEP', 'extensions', PANEL_NAME)
	os.makedirs(os.path.dirname(dest), exist_ok=True)
	if os.path.isdir(dest):
		shutil.rmtree(dest, ignore_errors=True)
	shutil.copytree(panel_src, dest)
	return True, ''


def _step_registry():
	import winreg
	for v in (9, 10, 11, 12):
		k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 'Software\\Adobe\\CSXS.{}'.format(v))
		winreg.SetValueEx(k, 'PlayerDebugMode', 0, winreg.REG_SZ, '1')
		winreg.CloseKey(k)
	return True, ''


def _step_effect():
	global _BLOCKED
	present_names = [n for n in AEX_NAMES if os.path.isfile(os.path.join(PLUGINS_SRC, n))]
	if not present_names:
		return False, 'file effetto mancanti'
	try:
		_elevate_copy_to_plugins(present_names, _PLUG_DIRS)
	except Exception:
		return False, 'copia non autorizzata'
	import time
	try:
		time.sleep(2)   # give a real-time antivirus a moment to act, if it will
	except Exception:
		pass
	# A folder is "blocked" if it is missing ANY of the effects we tried to copy.
	_BLOCKED = [d for d in _PLUG_DIRS
	            if any(not os.path.isfile(os.path.join(d, n)) for n in present_names)]
	if _BLOCKED:
		return False, "bloccato dall'antivirus"
	return True, ''


# =====================================================================
# Helpers
# =====================================================================

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


def _ae_version_label(plug_dir):
	try:
		ae_folder = os.path.dirname(os.path.dirname(plug_dir))
		name = os.path.basename(ae_folder)
		short = name.replace('Adobe After Effects', '').strip()
		return short or name
	except Exception:
		return '?'


def _elevate_copy_to_plugins(names, plug_dirs):
	"""Copy each effect (names) into every plug dir via ONE elevated cmd.exe
	(single UAC), waiting for it to finish."""
	parts = []
	for name in names:
		src = os.path.join(PLUGINS_SRC, name)
		for d in plug_dirs:
			parts.append('copy /Y "{}" "{}"'.format(src, os.path.join(d, name)))
	if not parts:
		raise OSError('no effect files to copy')
	_elevate_and_wait('cmd.exe', '/c ' + ' & '.join(parts))


def _elevate_and_wait(file, params, timeout_ms=120000):
	import ctypes
	from ctypes import wintypes

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
	sei.lpFile = file
	sei.lpParameters = params
	sei.nShow = 0            # SW_HIDE
	if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
		raise OSError('ShellExecuteExW runas failed')
	if sei.hProcess:
		ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, timeout_ms)
		ctypes.windll.kernel32.CloseHandle(sei.hProcess)


def _message(text):
	"""Fallback (no window): deferred message box."""
	run("ui.messageBox('Custom families - After Effects', {!r})".format(text), delayFrames=1)


# =====================================================================
# Live progress window (a Text DAT shown in a floating viewer; monospace)
# =====================================================================

class _ProgressWindow:
	BAR_W = 26

	def __init__(self, title, total):
		self.title = title
		self.total = max(1, total)
		self.frac = 0.0
		self.current = ''
		self.headline = ''
		self.footer = ''
		self.log = []          # list of [text, status]
		self.dat = self._build()
		self._render()
		try:
			self.dat.openViewer(unique=True, borders=True)
		except Exception as exc:
			debug('[AEOP ui] openViewer failed: {}'.format(exc))

	def _build(self):
		host = op(_BASE_PATH)
		old = host.op('aeop_progress')
		if old:
			try:
				old.closeViewer()
			except Exception:
				pass
			try:
				old.destroy()
			except Exception:
				pass
		return host.create(textDAT, 'aeop_progress')

	def set_doing(self, label, idx):
		self.current = label
		self.frac = float(idx) / self.total
		self.log.append([label, 'doing'])
		self._render()

	def mark(self, label, ok, note, done_count):
		for entry in reversed(self.log):
			if entry[1] == 'doing':
				entry[0] = label + (' - ' + note if note else '')
				entry[1] = 'ok' if ok else 'fail'
				break
		self.frac = float(done_count) / self.total
		self.current = ''
		self._render()

	def finish(self, headline, footer):
		self.frac = 1.0
		self.current = ''
		self.headline = headline
		self.footer = footer
		self._render()

	def _render(self):
		f = int(round(self.frac * self.BAR_W))
		f = max(0, min(self.BAR_W, f))
		bar = '#' * f + '-' * (self.BAR_W - f)
		pct = int(round(self.frac * 100))
		L = ['']
		L.append('  ' + self.title)
		L.append('  ' + '=' * 50)
		L.append('')
		L.append('  [' + bar + ']  ' + str(pct) + '%')
		L.append('')
		if self.headline:
			L.append('  ' + self.headline)
			L.append('')
		elif self.current:
			L.append('  In corso: ' + self.current)
			L.append('')
		marks = {'ok': '  [ OK ] ', 'fail': '  [ X  ] ',
		         'doing': '  [ .. ] ', 'pending': '  [    ] '}
		for txt, st in self.log:
			L.append(marks.get(st, '        ') + txt)
		if self.footer:
			L.append('')
			L.append('  ' + '-' * 50)
			for fl in self.footer.split('\n'):
				L.append('  ' + fl)
		L.append('')
		try:
			self.dat.text = '\n'.join(L) + '\n'
		except Exception:
			pass
