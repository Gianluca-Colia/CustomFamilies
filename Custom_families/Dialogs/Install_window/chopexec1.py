"""
CHOP Execute DAT — Install_window State driver.

Listens to the par.State value of Install_window (via par1 → math1 → null1)
and runs the matching State<N> DAT to flip the dialog UI between its
phases (1 = idle, 2 = installing, 3 = installed).
"""


def onOffToOn(channel: Channel, sampleIndex: int, val: float,
              prev: float):
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
	state_index = int(val)
	state_dat = op('State' + str(state_index))
	if state_dat is not None:
		state_dat.run()
	return
