"""
CHOP Execute DAT — Devepment mode auto-switch.

Watches the `Developmentmode` channel exported from the
Custom_families root COMP (Parameter CHOP `par2` feeds this script).
When the user flips the toggle, fire the same download path used by
the install flow. `_download_repo_to_appdata` already auto-detects
branch mismatch via the DEVELOP_MODE.txt marker, so it will swap
the on-disk copy to the branch the toggle just selected.

me     - this DAT
parent() = Installer COMP (host of the Install extension)
"""


def onValueChange(channel: Channel, sampleIndex: int, val: float,
				  prev: float):
	"""Fires every time the watched par value changes (Off→On AND On→Off)."""
	if channel.name != 'Developmentmode':
		return
	installer = parent()
	if installer is None or not hasattr(installer, 'ext'):
		return
	try:
		installer.ext.Install._download_repo_to_appdata()
	except Exception as exc:
		debug('[devmode auto-switch] download failed:', exc)
	return


def onOffToOn(channel: Channel, sampleIndex: int, val: float,
			  prev: float):
	"""Not used — onValueChange catches both transitions."""
	return


def whileOn(channel: Channel, sampleIndex: int, val: float,
			prev: float):
	return


def onOnToOff(channel: Channel, sampleIndex: int, val: float,
			  prev: float):
	"""Not used — onValueChange catches both transitions."""
	return


def whileOff(channel: Channel, sampleIndex: int, val: float,
			 prev: float):
	return
