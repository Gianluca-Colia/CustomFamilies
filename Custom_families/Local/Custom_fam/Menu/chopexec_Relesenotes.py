"""
CHOP Execute DAT
Menu action bridge - Relese_notes.
"""

def onValueChange(channel, sampleIndex, val, prev):
	if val == 1 and prev == 0:
		run("op('/Custom_families/Custom/Menu/Relese_notes').par.Open.pulse()", delayFrames=1)

def onOffToOn(channel, sampleIndex, val, prev):
	return

def whileOn(channel, sampleIndex, val, prev):
	return

def onOnToOff(channel, sampleIndex, val, prev):
	return

def whileOff(channel, sampleIndex, val, prev):
	return