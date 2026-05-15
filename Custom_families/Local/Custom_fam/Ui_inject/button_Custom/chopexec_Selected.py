"""
CHOP Execute DAT - Selected
Sets par.Selected on the button and on the family COMP based on focusselect channel state.
Derives family name from the button name (button_FamilyName -> FamilyName).
"""


def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    if channel.name == 'focusselect' and parent().par.Cursor == 'pointer':
        family_name = parent().name[len('button_'):]
        try:
            getattr(op, family_name).par.Selected = 1
        except Exception:
            pass
        parent().par.Selected = 1
    return

def whileOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onOnToOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    if channel.name == 'focusselect':
        family_name = parent().name[len('button_'):]
        try:
            getattr(op, family_name).par.Selected = 0
        except Exception:
            pass
        parent().par.Selected = 0
    return

def whileOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onValueChange(channel: Channel, sampleIndex: int, val: float, prev: float):
    return
