"""
CHOP Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the CHOP Execute DAT.
"""

def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    Button = parent()
    if Button.par.Editmode == 'editable':
        Button.par.Editmode = 0
        Button.par.Clickthrough = 1
        Button.par.Cursor = 0
    else:
        pass
    return


    """
    Called when a channel changes from 0 to non-zero.

    Args:
        channel: The Channel object which has changed
        sampleIndex: The index of the changed sample
        val: The numeric value of the changed sample
        prev: The previous sample value
    """

def whileOn(channel: Channel, sampleIndex: int, val: float, prev: float):
    """
    Called every frame while a channel is non-zero.

    Args:
        channel: The Channel object which has changed
        sampleIndex: The index of the changed sample
        val: The numeric value of the changed sample
        prev: The previous sample value
    """
    return

def onOnToOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    """
    Called when a channel changes from non-zero to 0.

    Args:
        channel: The Channel object which has changed
        sampleIndex: The index of the changed sample
        val: The numeric value of the changed sample
        prev: The previous sample value
    """
    return

def whileOff(channel: Channel, sampleIndex: int, val: float, prev: float):
    """
    Called every frame while a channel is 0.

    Args:
        channel: The Channel object which has changed
        sampleIndex: The index of the changed sample
        val: The numeric value of the changed sample
        prev: The previous sample value
    """
    return

def onValueChange(channel: Channel, sampleIndex: int, val: float, prev: float):
    """
    Called when a channel value changes.

    Args:
        channel: The Channel object which has changed
        sampleIndex: The index of the changed sample
        val: The numeric value of the changed sample
        prev: The previous sample value
    """
    return
