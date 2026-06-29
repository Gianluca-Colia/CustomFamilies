# AEOP - After Effects side UNINSTALLER (with live progress window)
# =====================================================================
# Callbacks file for the Parameter Execute DAT inside the Base COMP
# "Uninstaller" (inside the AEOP component). Twin of install_ae.py.
#
# SETUP (in TouchDesigner):
#   1. Base COMP "Uninstaller" gets a custom PULSE parameter named "Uninstall".
#   2. A Parameter Execute DAT inside it, watching the Base (op = "..") with
#      Pulse = On, DAT text synced to this file (Sync to File / Load on Start).
#   3. Press "Uninstall" -> onPulse() removes the AE side and opens a live
#      progress window (progress bar + current action + final friendly recap).
#
# WHAT IT DOES: removes the CEP panel (per-user) and deletes AELayerSpout.aex
# from every AE Program Files Plug-ins folder via ONE elevated cmd.exe. Leaves
# PlayerDebugMode in place (shared global). Does NOT delete the on-disk
# framework folder (that belongs to the Custom families uninstaller).
#
# Fully defensive: never raises out of the callback; if the window can't be
# built it falls back to a messageBox recap.
# =====================================================================

import os
import shutil

PANEL_NAME = 'com.aeop.nullosc'
AEX_NAMES = ('AELayerSpout.aex',)   # AE plugins to remove (effect for the TOP)
UNINSTALL_PAR = 'Uninstall'
WINDOW_TITLE = 'AEOP - Disinstallazione After Effects'

# --- runtime state ---
_DAT_PATH = ''
_BASE_PATH = ''
_WIN = None
_STEPS = []
_RESULTS = []
_REMAIN = []
_REMOVED_ANY = False
_RUNNING = False


# =====================================================================
# Parameter Execute DAT callbacks (full standard set - keep all of them).
#   me / par / val / prev.  Only onPulse is wired.
# =====================================================================

def onValueChange(par, prev):
	return

def onPulse(par):
	if par.name == UNINSTALL_PAR:
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
	global _DAT_PATH, _BASE_PATH, _WIN, _STEPS, _RESULTS, _REMAIN, _REMOVED_ANY, _RUNNING
	if _RUNNING:
		return
	_RUNNING = True
	_DAT_PATH = me.path
	_BASE_PATH = me.parent().path
	_RESULTS = []
	_REMAIN = []
	_REMOVED_ANY = False
	_STEPS = [
		('Rimozione del pannello', _step_panel),
		("Rimozione dell'effetto (conferma di Windows)", _step_effect),
	]
	try:
		_WIN = _ProgressWindow(WINDOW_TITLE, len(_STEPS))
	except Exception as exc:
		debug('[AEOP uninstall] window build failed (fallback to messagebox): {}'.format(exc))
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
		debug('[AEOP uninstall] step "{}" error: {}'.format(label, exc))
	try:
		if _WIN:
			_WIN.mark(label, ok, note, i + 1)
	except Exception:
		pass
	_RESULTS.append((label, ok, note))
	debug('[AEOP uninstall] {} -> {}{}'.format(label, 'OK' if ok else 'FAIL',
	                                            (' (' + note + ')') if note else ''))
	if (i + 1) >= len(_STEPS):
		run("op({!r}).module._finish()".format(_DAT_PATH), delayFrames=1)
	else:
		run("op({!r}).module._show_step({})".format(_DAT_PATH, i + 1), delayFrames=1)


def _finish():
	global _RUNNING
	try:
		if _REMAIN:
			headline = 'ATTENZIONE - alcuni file sono in uso'
			footer = ("Non sono riuscito a rimuovere l'effetto da:\n  " +
			          "\n  ".join(_REMAIN) + "\n"
			          "Chiudi After Effects (tiene il file aperto) e premi di nuovo Uninstall.")
		elif not _REMOVED_ANY:
			headline = 'Niente da rimuovere'
			footer = ("Il plugin per After Effects non risultava installato.\n"
			          "Non e' stato modificato nulla.")
		else:
			headline = 'TUTTO OK - plugin rimosso'
			footer = ("Il plugin per After Effects e' stato rimosso.\n"
			          "Riavvia After Effects per applicare la rimozione.")
		if _WIN:
			_WIN.finish(headline, footer)
		else:
			_message(headline + "\n\n" + footer)
		debug('[AEOP uninstall] DONE - ' + headline)
	finally:
		_RUNNING = False


# =====================================================================
# Steps (each returns (ok: bool, note: str))
# =====================================================================

def _step_panel():
	global _REMOVED_ANY
	appdata = os.environ.get('APPDATA')
	if not appdata:
		return True, 'niente da fare'
	dest = os.path.join(appdata, 'Adobe', 'CEP', 'extensions', PANEL_NAME)
	if not os.path.isdir(dest):
		return True, 'gia assente'
	shutil.rmtree(dest, ignore_errors=True)
	if os.path.isdir(dest):
		return False, 'non rimosso'
	_REMOVED_ANY = True
	return True, ''


def _step_effect():
	global _REMAIN, _REMOVED_ANY
	plug_dirs = _ae_plugin_dirs()
	present = [d for d in plug_dirs
	          if any(os.path.isfile(os.path.join(d, n)) for n in AEX_NAMES)]
	if not present:
		return True, 'gia assente'
	try:
		_elevate_delete_from_plugins(present)
	except Exception:
		return False, 'rimozione non autorizzata'
	import time
	try:
		time.sleep(1)
	except Exception:
		pass
	_REMAIN = [d for d in present
	           if any(os.path.isfile(os.path.join(d, n)) for n in AEX_NAMES)]
	if _REMAIN:
		return False, 'file in uso (AE aperto?)'
	_REMOVED_ANY = True
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
		debug('[AEOP uninstall] plugin-dir scan failed: {}'.format(exc))
	return dirs


def _elevate_delete_from_plugins(plug_dirs):
	"""Delete every effect (AEX_NAMES) from each plug dir via ONE elevated
	cmd.exe (single UAC)."""
	parts = []
	for name in AEX_NAMES:
		for d in plug_dirs:
			parts.append('del /F /Q "{}"'.format(os.path.join(d, name)))
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
