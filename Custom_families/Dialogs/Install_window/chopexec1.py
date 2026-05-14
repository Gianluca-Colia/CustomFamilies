"""
CHOP Execute DAT — Install_window State driver.

Listens to the par.State value of Install_window (via par1 → math1 → null1)
and runs the matching State<N> DAT to flip the dialog UI between its
phases (1 = idle, 2 = installing, 3 = installed).

When entering State 2 we first realign every par.Font listed in the
Installer's `Text` table so the loadbar/progress widgets render with the
correct typeface as soon as the install state takes over.
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

	# Before transitioning into the install state, push the canonical Font
	# expressions onto every operator listed in Installer/Text. Done here so
	# the dialog widgets pick up the right typeface as soon as State2 runs.
	if state_index == 2:
		try:
			parent(3).op('Installer').ext.Install.RealignFonts()
		except Exception as exc:
			debug('[Install_window chopexec1] RealignFonts failed: {}'.format(exc))

	state_dat = op('State' + str(state_index))
	if state_dat is not None:
		state_dat.run()
	return
