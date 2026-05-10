"""
Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the Execute DAT.
"""

import os
import ssl
import shutil
import urllib.request
import urllib.error
import zipfile

ASSETS_REPO_ZIP_URL = 'https://github.com/Gianluca-Colia/CustomFamilies/archive/refs/heads/main.zip'
# app.preferencesFolder is the TD prefs folder, cross-platform.
ASSETS_DISK_ROOT = os.path.join(app.preferencesFolder, 'Custom families')
ASSETS_PREFETCH_DIRS = ('Font', 'Images')


def onStart():
	"""
	Called when the project starts.
	"""
	return

def onCreate():
	"""
	Called when the DAT is created.

	Flow:
	  1. Resolve the host (Custom_families root = parent(3)).
	  2. If the host is NOT yet inside /ui/Plugins:
	       - get or create /ui/Plugins as a base COMP under /ui
	       - copy the host into it
	       - destroy the original (deferred, so this script completes safely)
	     The copy's own Install_window/execute1.onCreate will fire from the
	     new location and fall into branch (3) below.
	  3. If the host IS inside /ui/Plugins: cook + pulse Winopen to open dialog.
	"""
	target = parent()       # Install_window
	host = parent(3)        # Custom_families root
	if host is None:
		return

	ui_root = op('/ui')
	if ui_root is None:
		return

	plugins = ui_root.op('Plugins')
	if plugins is None:
		plugins = ui_root.create(baseCOMP, 'Plugins')
	if plugins is None:
		return

	try:
		host_parent = host.parent()
	except Exception:
		host_parent = None

	if host_parent != plugins:
		# Host is outside /ui/Plugins: relocate.
		# If a copy already lives at /ui/Plugins/Custom_families (previous install),
		# don't duplicate — just destroy this stray instance.
		existing = plugins.op('Custom_families')
		if existing is not None:
			run("args[0].destroy() if args[0] is not None else None", host, delayFrames=2)
			return
		try:
			copied = plugins.copy(host, name='Custom_families')
			if copied is not None:
				copied.nodeX = host.nodeX
				copied.nodeY = host.nodeY
		except Exception as e:
			debug('[Install_window.onCreate] copy to /ui/Plugins failed:', e)
			return
		# Destroy source after the current callstack unwinds; otherwise we
		# would tear down our own DAT mid-execution.
		run("args[0].destroy() if args[0] is not None else None", host, delayFrames=2)
		return

	# Branch (3): already in /ui/Plugins → open the dialog.
	# Make sure the Font and Images folders are on disk BEFORE opening the
	# window, otherwise the dialog renders without its fonts/images. The
	# full Custom_families install (which Install.Run drives) will later
	# overwrite this prefetch — this is just the minimum viable boot for
	# the dialog to look right.
	_prefetch_install_window_assets()

	try:
		target.cook(force=True)
	except Exception:
		pass
	try:
		for child in target.findChildren(depth=None):
			try:
				child.cook(force=True)
			except Exception:
				pass
	except Exception:
		pass
	run("args[0].par.Winopen.pulse()", target, delayFrames=15)
	return


def _prefetch_install_window_assets():
	"""Ensure Font/ and Images/ exist at LOCALAPPDATA before the install
	dialog opens. Idempotent: skip when both folders are already on disk.

	Strategy: download the repo zip, extract only the Font/ and Images/
	subtrees, drop the zip. Same SSL fallback as Install._download_zip
	(verified context first, unverified retry on SSL error, User-Agent
	header to avoid GitHub 403 on UA-less requests).
	"""
	if all(os.path.isdir(os.path.join(ASSETS_DISK_ROOT, name))
	       for name in ASSETS_PREFETCH_DIRS):
		return

	try:
		os.makedirs(ASSETS_DISK_ROOT, exist_ok=True)
	except Exception as exc:
		debug('[Install_window prefetch] mkdir failed: {}'.format(exc))
		return

	zip_path = os.path.join(ASSETS_DISK_ROOT, '_assets.zip')
	try:
		_download_to(ASSETS_REPO_ZIP_URL, zip_path)
	except Exception as exc:
		debug('[Install_window prefetch] download failed: {}: {}'.format(
			type(exc).__name__, exc))
		return

	try:
		_extract_subdirs(zip_path, ASSETS_DISK_ROOT, ASSETS_PREFETCH_DIRS)
	except Exception as exc:
		debug('[Install_window prefetch] extract failed: {}: {}'.format(
			type(exc).__name__, exc))
	finally:
		try:
			os.remove(zip_path)
		except Exception:
			pass


def _download_to(url, dest_path):
	req = urllib.request.Request(url, headers={'User-Agent': 'Custom_families-installer'})
	try:
		response = urllib.request.urlopen(req, timeout=30)
	except (ssl.SSLError, urllib.error.URLError) as ssl_exc:
		# Retry with unverified SSL only on SSL-class failures.
		is_ssl = isinstance(ssl_exc, ssl.SSLError) or (
			isinstance(ssl_exc, urllib.error.URLError)
			and isinstance(ssl_exc.reason, ssl.SSLError)
		)
		if not is_ssl:
			raise
		ctx = ssl._create_unverified_context()
		response = urllib.request.urlopen(req, timeout=30, context=ctx)

	with response, open(dest_path, 'wb') as out:
		while True:
			chunk = response.read(64 * 1024)
			if not chunk:
				break
			out.write(chunk)


def _extract_subdirs(zip_path, dest_root, allowed_top_dirs):
	"""Extract entries whose path under the repo root starts with one of
	`allowed_top_dirs` into `dest_root`, stripping the GitHub-zip top-level
	folder (`CustomFamilies-main/`) so the layout matches a normal install.
	"""
	allowed_prefixes = tuple(d.rstrip('/') + '/' for d in allowed_top_dirs)

	with zipfile.ZipFile(zip_path, 'r') as archive:
		for name in archive.namelist():
			# GitHub zips wrap everything in `<repo>-<branch>/`; strip it.
			parts = name.split('/', 1)
			if len(parts) < 2:
				continue
			rel = parts[1]
			if not rel:
				continue
			if not rel.startswith(allowed_prefixes):
				continue

			target = os.path.join(dest_root, rel)
			if name.endswith('/'):
				os.makedirs(target, exist_ok=True)
				continue
			os.makedirs(os.path.dirname(target), exist_ok=True)
			with archive.open(name) as src, open(target, 'wb') as dst:
				shutil.copyfileobj(src, dst)


def onExit():
	"""
	Called when the project exits.
	"""
	return

def onFrameStart(frame: int):
	"""
	Called at the start of each frame.
	
	Args:
		frame: The current frame number
	"""
	return

def onFrameEnd(frame: int):
	"""
	Called at the end of each frame.
	
	Args:
		frame: The current frame number
	"""
	return

def onPlayStateChange(state: bool):
	"""
	Called when the play state changes.
	
	Args:
		state: False if the timeline was just paused
	"""
	return

def onDeviceChange():
	"""
	Called when a device change occurs.
	"""
	return

def onProjectPreSave():
	"""
	Called before the project is saved.
	"""
	return

def onProjectPostSave():
	"""
	Called after the project is saved.
	"""
	return
