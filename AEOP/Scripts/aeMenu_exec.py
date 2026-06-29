# AEOP - menu mirror (TD node side)  --  CHOP Execute DAT
# =====================================================================
# The C++ "AE Layer" CHOP (cplusplus1) builds the cascading dynamic menus
# natively: Layertype -> Project -> Comp -> Layer, from the layers it receives
# over OSC. The wrapper exposes its OWN custom menus with the SAME names, but
# they are NOT bound to the CHOP. This script keeps them in sync:
#   - mirrors each level's menu items (names/labels) from the CHOP -> wrapper
#   - auto-selects the first valid entry where the current one is empty/invalid
#     so the cascade starts on its own
#   - pushes the wrapper selections back into the CHOP so its dynamic menus
#     filter correctly (Layertype/Project gate Comp, etc.)
#
# DAT TYPE: CHOP Execute DAT - attach to the CHOP carrying the AE layer signal
# (fires on data change -> Sync()). aeSpout_exec (Parameter Execute on the
# wrapper) also calls Sync() when the user changes a menu.
# =====================================================================

SRC_CHOP = 'cplusplus1'           # the C++ AE Layer CHOP with the dynamic menus
LAYERTYPE_PAR = 'Layertype'
CASCADE = ('Project', 'Comp', 'Layer')

_SYNCING = [False]                # re-entrancy guard (setting .val fires execs)


def is_syncing():
	return _SYNCING[0]


def _set_menu(par, names, labels):
	if not names:
		names, labels = [''], ['']
	if len(labels) != len(names):
		labels = names
	if list(par.menuNames) != names:
		par.menuNames = names
		par.menuLabels = labels


def Sync():
	"""Mirror the CHOP's cascading menus onto the wrapper and drive the CHOP's
	selection so the cascade flows. Cheap when nothing changed (compare-before-
	set), so it is safe to call often."""
	if _SYNCING[0]:
		return
	n = parent()
	c = n.op(SRC_CHOP)
	if c is None:
		return
	_SYNCING[0] = True
	try:
		# Layertype gates everything downstream: push wrapper -> CHOP.
		try:
			if c.par.Layertype.eval() != n.par.Layertype.eval():
				c.par.Layertype.val = n.par.Layertype.eval()
		except Exception:
			pass

		# Project -> Comp -> Layer. Each level's CHOP menu is filtered by the
		# levels above, so we set each value before reading the next level.
		for name in CASCADE:
			cpar = getattr(c.par, name, None)
			wpar = getattr(n.par, name, None)
			if cpar is None or wpar is None:
				continue
			try:
				names = list(cpar.menuNames)
				labels = list(cpar.menuLabels)
			except Exception:
				names, labels = [], []
			_set_menu(wpar, names, labels)
			cur = wpar.eval()
			newval = cur if (cur in names) else (names[0] if names else '')
			if wpar.eval() != newval:
				wpar.val = newval
			try:
				if cpar.eval() != newval:
					cpar.val = newval
			except Exception:
				pass
	except Exception as exc:
		debug('[AEOP menu] sync failed: {}'.format(exc))
	finally:
		_SYNCING[0] = False


# ----- CHOP Execute DAT callbacks (full standard set) -----

def onOffToOn(channel, sampleIndex, val, prev):
	return

def whileOn(channel, sampleIndex, val, prev):
	return

def onOnToOff(channel, sampleIndex, val, prev):
	return

def whileOff(channel, sampleIndex, val, prev):
	return

def onValueChange(channel, sampleIndex, val, prev):
	Sync()
	return
