"""
CHOP Execute DAT - Rename
On a true left-click double (select count > 1) triggers Rename on the
family Menu. Right-click and mixed left/right rapid clicks must NOT
trigger rename — only the dedicated left-click channel counts.
"""

# Channels emitted by the upstream click CHOP that we accept as a true
# left-click. Anything else (rselect, mselect, ...) is ignored, even when
# its sample value crosses the >1 threshold during a fast left+right or
# right+left sequence.
LEFT_CLICK_CHANNELS = ('select',)


def _is_left_click(channel) -> bool:
    try:
        name = str(getattr(channel, 'name', '') or '')
    except Exception:
        name = ''
    return name in LEFT_CLICK_CHANNELS


def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def whileOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onOnToOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def whileOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    return

def onValueChange(channel: Channel, sampleIndex: int, val: float, prev: float):
    if not _is_left_click(channel):
        return
    if val > 1:
        family_name = parent().name[len('button_'):]
        getattr(op, family_name).op('Menu').par.Rename.pulse()
    return
