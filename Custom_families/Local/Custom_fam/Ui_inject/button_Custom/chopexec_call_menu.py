"""
CHOP Execute DAT - call_menu
On rselect (right-click) opens the popMenu inside the family COMP.
"""


def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    if channel.name != 'rselect':
        return
    try:
        family_name = parent().name[len('button_'):]
        family_op = getattr(op, family_name)
        pop_menu = family_op.op('Menu/popMenu')
        pop_menu.Open(subMenuItems=['Release notes'])
        debug('[call_menu] opened: {}'.format(pop_menu.path))
    except Exception as e:
        debug('[call_menu] failed: {}'.format(e))
    return

def whileOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onOnToOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def whileOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onValueChange(channel: Channel, sampleIndex: int, val: float, prev: float):
    return
