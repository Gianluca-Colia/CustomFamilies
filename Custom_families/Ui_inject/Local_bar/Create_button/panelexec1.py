# panelValue - the PanelValue object that changed
# Make sure the corresponding toggle is enabled in the Panel Execute DAT.

CUSTOM_FAMILIES_PATH = '/ui/Plugins/Custom_families'


def onOffToOn(panelValue: PanelValue):
	"""
	Called when the Create_button is pressed.

	Pulses the `Createfamily` par on the Custom_families root COMP.
	That par is exported via par1 → chopexec1 inside
	/ui/Plugins/Custom_families/Create_family, which then runs the
	Createfamily extension's Create() method to spawn the new family.
	"""
	root = op(CUSTOM_FAMILIES_PATH)
	if root is None:
		debug('[Create_button] Custom_families root missing at {}'.format(CUSTOM_FAMILIES_PATH))
		return
	if not hasattr(root.par, 'Createfamily'):
		debug('[Create_button] Createfamily par missing on {}'.format(root.path))
		return
	root.par.Createfamily.pulse()
	return


def onValueChange(panelValue):
	parent().par.value0 = panelValue
	return