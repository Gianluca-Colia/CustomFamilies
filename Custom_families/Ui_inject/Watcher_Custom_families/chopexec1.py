"""
CHOP Execute DAT

me - this DAT
"""


def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
	_check_watcher()
	return


def whileOn(channel: Channel, sampleIndex: int, val: float, prev: float):
	_check_watcher()
	return


def onOnToOff(channel: Channel, sampleIndex: int, val: float, prev: float):
	return


def whileOff(channel: Channel, sampleIndex: int, val: float, prev: float):
	return


def onValueChange(channel: Channel, sampleIndex: int, val: float, prev: float):
	_check_watcher()
	return


def _check_watcher():
	op('opfind1').cook(force=True)
	return
