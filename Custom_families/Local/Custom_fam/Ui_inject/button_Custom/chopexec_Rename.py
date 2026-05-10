"""
CHOP Execute DAT - Rename
On double-click (click > 1) triggers Rename on the family Menu.
"""


def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def whileOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onOnToOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def whileOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onValueChange(channel: Channel, sampleIndex: int, val: float, prev: float):
    if val > 1:
        family_name = parent().name[len('button_'):]
        getattr(op, family_name).op('Menu').par.Rename.pulse()
    return
