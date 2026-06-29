# AEOP - Spout effect control (TD node side)
# =====================================================================
# Parameter Execute DAT for the AEOP node. Drives the AELayerSpout effect
# in After Effects WITHOUT the user ever applying it by hand:
#   - on Comp/Layer selection change -> apply the effect to the new layer
#     (and remove it from the previously targeted layer)
#   - on the optional "Detach" pulse  -> remove it from the current layer
#
# The menus themselves are populated independently (see aeMenu_exec.py), so
# every layer is listed BEFORE any effect is applied.
#
# Transport: an OSC Out DAT inside the node, pointing at the CEP panel's
# command channel (UDP 127.0.0.1:7001). The panel maps these to
# AEOP_applySpout / AEOP_removeSpout in aeQuery.jsx.
#
# Wiring:
#   - OSC Out DAT named OSC_DAT below: Protocol "Messaging" (UDP),
#     Network Address 127.0.0.1, Port 7001.
#   - This Parameter Execute watches the node (op = "..") custom page,
#     with Value Change + Pulse on.
#   - The node has custom pars: Comp (string/menu) and Layer (menu whose
#     value is the AE layer INDEX, 1-based), plus an optional Detach pulse.
# =====================================================================

OSC_DAT = 'oscout1'          # name of the OSC Out DAT inside the node
MENU_DAT = 'aeMenu_exec'     # CHOP Execute DAT that owns the menu rebuild
TARGET_KEY = 'aeop_spout_target'   # stored [compName, layerIndex] currently applied
TYPE_PAR = 'Type'
COMP_PAR = 'Comp'
LAYER_PAR = 'Layer'
DETACH_PAR = 'Detach'

# Layer types that DON'T render pixels -> they never need the Spout effect
# (a null has nothing to send; cameras/lights can't take an effect at all).
NO_EFFECT_TYPES = ('null', 'camera', 'light')


def _rebuild_menus():
	"""Ask aeMenu_exec to refilter the Comp/Layer menus (Type/Comp changed)."""
	m = parent().op(MENU_DAT)
	if m is not None:
		try:
			m.module.Rebuild()
		except Exception as exc:
			debug('[AEOP node] menu rebuild failed: {}'.format(exc))


def _osc():
	return parent().op(OSC_DAT)


def _send(address, comp, idx):
	o = _osc()
	if o is not None and comp and idx:
		try:
			o.sendOSC(address, [comp, int(idx)])
		except Exception as exc:
			debug('[AEOP node] OSC send failed: {}'.format(exc))


def _current_target():
	"""(compName, layerIndex) from the node's menus. layerIndex = AE 1-based."""
	n = parent()
	try:
		comp = n.par[COMP_PAR].eval()
		idx = int(n.par[LAYER_PAR].eval())
		return comp, idx
	except Exception:
		return None, None


def _apply():
	"""Move the effect to the current selection: remove from the previous
	target (if different), apply to the new one, remember the new one.
	Layer types that don't render (null/camera/light) get NO effect."""
	n = parent()
	try:
		ltype = n.par[TYPE_PAR].eval()
	except Exception:
		ltype = ''
	comp, idx = _current_target()
	old = n.fetch(TARGET_KEY, None)

	# No-pixel types: never apply; clean up any leftover effect and bail.
	if ltype in NO_EFFECT_TYPES:
		if old:
			_send('/ae/spout/remove', old[0], old[1])
			try:
				n.unstore(TARGET_KEY)
			except Exception:
				pass
		return

	if not comp or not idx:
		return
	if old and list(old) != [comp, idx]:
		_send('/ae/spout/remove', old[0], old[1])
	_send('/ae/spout/apply', comp, idx)
	n.store(TARGET_KEY, [comp, idx])


def _detach():
	"""Remove the effect from whatever layer we last applied it to."""
	n = parent()
	old = n.fetch(TARGET_KEY, None)
	if old:
		_send('/ae/spout/remove', old[0], old[1])
		try:
			n.unstore(TARGET_KEY)
		except Exception:
			pass


# ----- Parameter Execute DAT callbacks (full standard set) -----

def onValueChange(par, prev):
	# Type/Comp changed -> refilter the dependent menus first.
	if par.name in (TYPE_PAR, COMP_PAR):
		_rebuild_menus()
	# Comp/Layer changed -> move the Spout effect to the new target.
	if par.name in (COMP_PAR, LAYER_PAR):
		_apply()
	return

def onPulse(par):
	if par.name == DETACH_PAR:
		_detach()
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return
