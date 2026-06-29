# AEOP - menu mirror (TD node side)  --  CHOP Execute DAT
# =====================================================================
# Both C++ operators carry the SAME cascading dynamic menus
# (Layertype -> Project -> Comp -> Layer):
#   - cplusplus1 : the "AE Layer" CHOP   (transform of the selected layer)
#   - cplusplus2 : the Spout In TOP      (pixels of the selected layer)
# The wrapper exposes its own same-named menus, NOT bound to either op. This
# script keeps everything in lock-step:
#   - mirrors the menu items (names/labels) from MENU_SRC -> wrapper
#   - auto-selects the first valid entry per level so the cascade starts
#   - pushes the wrapper selection into BOTH C++ ops (TARGETS) so the CHOP and
#     the TOP always point at the same layer and update together
#
# DAT TYPE: CHOP Execute DAT - attach to a CHOP that changes when AE data
# arrives (e.g. cplusplus1) so it re-syncs live. aeSpout_exec (Parameter
# Execute on the wrapper) also calls Sync() when the user changes a menu.
# =====================================================================

MENU_SRC = 'cplusplus1'                    # read the menu lists from here
TARGETS = ('cplusplus1', 'cplusplus2')     # push the SELECTION to BOTH (CHOP + TOP)
LAYERTYPE_PAR = 'Layertype'
CASCADE = ('Project', 'Comp', 'Layer')

_SYNCING = [False]                          # re-entrancy guard


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


def _push(parname, value):
	"""Set parname=value on EVERY target op (CHOP + TOP), if different."""
	n = parent()
	for name in TARGETS:
		o = n.op(name)
		if o is None:
			continue
		p = getattr(o.par, parname, None)
		if p is None:
			continue
		try:
			if p.eval() != value:
				p.val = value
		except Exception:
			pass


def Sync():
	"""Mirror MENU_SRC's cascading menus onto the wrapper and drive BOTH C++ ops'
	selection so CHOP and TOP follow the same layer. Compare-before-set, so it is
	cheap to call often."""
	if _SYNCING[0]:
		return
	n = parent()
	src = n.op(MENU_SRC)
	if src is None:
		return
	_SYNCING[0] = True
	try:
		# Layertype gates everything: push wrapper value to both ops first.
		try:
			_push(LAYERTYPE_PAR, n.par.Layertype.eval())
		except Exception:
			pass
		# Project -> Comp -> Layer. Set each level before reading the next, since
		# the lower menus are filtered by the higher selections.
		for name in CASCADE:
			spar = getattr(src.par, name, None)
			wpar = getattr(n.par, name, None)
			if spar is None or wpar is None:
				continue
			try:
				names = list(spar.menuNames)
				labels = list(spar.menuLabels)
			except Exception:
				names, labels = [], []
			_set_menu(wpar, names, labels)
			cur = wpar.eval()
			newval = cur if (cur in names) else (names[0] if names else '')
			if wpar.eval() != newval:
				wpar.val = newval
			_push(name, newval)   # -> both CHOP and TOP
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
