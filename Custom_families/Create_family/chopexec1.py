"""
CHOP Execute DAT — Create_family pulse bridge.

Listens on the `Createfamily` channel exported from the parent
Custom_families COMP (via par1). When the user pulses the par,
the channel transitions Off→On and we call the Createfamily
extension's Create() method to spawn a new family in Local.
"""


def onOffToOn(channel: Channel, sampleIndex: int, val: float,
			  prev: float):
	parent().ext.Create_family.Create()
	return


def whileOn(channel: Channel, sampleIndex: int, val: float,
			prev: float):
	return


def onOnToOff(channel: Channel, sampleIndex: int, val: float,
			  prev: float):
	return


def whileOff(channel: Channel, sampleIndex: int, val: float,
			 prev: float):
	return


def onValueChange(channel: Channel, sampleIndex: int, val: float,
				  prev: float):
	return
