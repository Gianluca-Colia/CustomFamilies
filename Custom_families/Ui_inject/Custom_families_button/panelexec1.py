# panelValue - the PanelValue object that changed
# Make sure the corresponding toggle is enabled in the Panel Execute DAT.

def onOffToOn(panelValue: PanelValue):
	"""
	Called when a panel value changes from 0 to non-zero.
	"""
	op('popMenu').Open()
	
	return
	
def onValueChange(panelValue):
	parent().par.value0 = panelValue
	return