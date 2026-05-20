"""
Execute DAT — Install_window onCreate hook.

Relocates the host Custom_families COMP under /ui/Plugins on first
insertion, then opens the install dialog. Images are baked directly
into the .tox, so they need no network fetch. The Font folder still
has to live on disk (TouchDesigner can't render fonts from embedded
.tox assets) — we prefetch only that single folder before opening the
dialog so its text labels render correctly.

Make sure the corresponding toggle is enabled in the Execute DAT.
"""

import os
import ssl
import shutil
import urllib.request
import urllib.error
import zipfile


# Prefetch limited to Font/ only. Images and the rest of the plugin are
# either embedded in the .tox or downloaded later by Installer/Install
# when the user clicks Install.
ASSETS_REPO_ZIP_URL = 'https://github.com/Gianluca-Colia/CustomFamilies/archive/refs/heads/main.zip'
ASSETS_DISK_ROOT = os.path.join(app.preferencesFolder, 'Custom families')
ASSETS_PREFETCH_DIRS = ('Font',)


def onStart():
	return


def onCreate():
	"""
	Flow:
	  1. Resolve the host (Custom_families root = parent(3)).
	  2. If the host is NOT yet inside /ui/Plugins:
	       - get or create /ui/Plugins as a base COMP under /ui
	       - copy the host into it
	       - destroy the original (deferred, so this script completes safely)
	     The copy's own Install_window/execute1.onCreate will fire from the
	     new location and fall into branch (3) below.
	  3. If the host IS inside /ui/Plugins: prefetch Font/, cook + pulse
	     Winopen to open the dialog.
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

	# Branch (3): already in /ui/Plugins → make sure Font/ is on disk, then
	# open the dialog. The prefetch is idempotent: if Font/ already exists
	# it returns immediately, so the window opens instantly on subsequent
	# inserts.
	_prefetch_font_assets()

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


def _prefetch_font_assets():
	"""Ensure Font/ exists at LOCALAPPDATA before the install dialog opens.

	Idempotent: skip when Font/ is already on disk. Strategy: download the
	repo zip, extract only the Font/ subtree, drop the zip. Same SSL
	fallback as Installer/Install._download_zip (verified context first,
	unverified retry on SSL error, User-Agent header to avoid GitHub 403).
	"""
	if all(os.path.isdir(os.path.join(ASSETS_DISK_ROOT, name))
	       for name in ASSETS_PREFETCH_DIRS):
		return

	try:
		os.makedirs(ASSETS_DISK_ROOT, exist_ok=True)
	except Exception as exc:
		debug('[Install_window prefetch] mkdir failed: {}'.format(exc))
		return

	zip_path = os.path.join(ASSETS_DISK_ROOT, '_font_assets.zip')
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
	return


def onFrameStart(frame: int):
	return


def onFrameEnd(frame: int):
	return


def onPlayStateChange(state: bool):
	return


def onDeviceChange():
	return


def onProjectPreSave():
	return


def onProjectPostSave():
	return
