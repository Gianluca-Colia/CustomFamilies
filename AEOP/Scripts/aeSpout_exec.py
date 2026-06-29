# AEOP - Spout effect control (TD node side)  --  Parameter Execute DAT
# =====================================================================
# Watches the wrapper's selection menus (Layertype / Project / Comp / Layer).
# On any change it:
#   1) lets aeMenu_exec re-sync the cascading menus (so Comp/Layer refilter),
#   2) drives the AELayerSpout effect in After Effects to follow the selected
#      layer - apply on the new layer, remove from the previous one - so the
#      user never applies the effect by hand.
#
# No effect for layer types that don't render pixels (null/camera/light).
#
# Identifiers: the wrapper's Comp par value is the COMP NAME and the Layer par
# value is the LAYER NAME (that's what the C++ dynamic menu stores), so the
# effect is applied/removed BY NAME.
#
# Transport: an OSC Out DAT (OSC_DAT) -> CEP panel command channel
# (UDP 127.0.0.1:7001) -> AEOP_applySpout / AEOP_removeSpout in aeQuery.jsx.
# =====================================================================

OSC_DAT = 'oscout1'          # OSC Out DAT inside the node
MENU_DAT = 'aeMenu_exec'     # CHOP Execute DAT that owns the menu sync
TARGET_KEY = 'aeop_spout_target'   # stored [compName, layerName] currently applied
LAYERTYPE_PAR = 'Layertype'
PROJECT_PAR = 'Project'
COMP_PAR = 'Comp'
LAYER_PAR = 'Layer'
DETACH_PAR = 'Detach'

# Layer types that DON'T render pixels -> they never need the Spout effect
# (a null has nothing to send; cameras/lights can't take an effect at all).
NO_EFFECT_TYPES = ('null', 'camera', 'light')

WATCHED = (LAYERTYPE_PAR, PROJECT_PAR, COMP_PAR, LAYER_PAR)


def _menu():
	return parent().op(MENU_DAT)


def _sync_menus():
	m = _menu()
	if m is not None:
		try:
			m.module.Sync()
		except Exception as exc:
			debug('[AEOP node] menu sync failed: {}'.format(exc))


def _osc():
	return parent().op(OSC_DAT)


def _send(address, comp, layer):
	o = _osc()
	if o is not None and comp and layer:
		try:
			o.sendOSC(address, [comp, layer])   # both strings (comp name, layer name)
		except Exception as exc:
			debug('[AEOP node] OSC send failed: {}'.format(exc))


def _current_target():
	"""(compName, layerName) from the wrapper menus."""
	n = parent()
	try:
		return n.par.Comp.eval(), n.par.Layer.eval()
	except Exception:
		return None, None


def _apply():
	"""Move the effect to the current selection (remove from previous, apply to
	new). Layer types that don't render (null/camera/light) get NO effect."""
	n = parent()
	try:
		ltype = n.par.Layertype.eval()
	except Exception:
		ltype = ''
	comp, layer = _current_target()
	old = n.fetch(TARGET_KEY, None)

	if ltype in NO_EFFECT_TYPES:
		if old:
			_send('/ae/spout/remove', old[0], old[1])
			try:
				n.unstore(TARGET_KEY)
			except Exception:
				pass
		return

	if not comp or not layer:
		return
	if old and list(old) != [comp, layer]:
		_send('/ae/spout/remove', old[0], old[1])
	_send('/ae/spout/apply', comp, layer)
	n.store(TARGET_KEY, [comp, layer])


def _detach():
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
	# Ignore changes the menu sync makes itself (avoids recursion / stray applies).
	m = _menu()
	if m is not None:
		try:
			if m.module.is_syncing():
				return
		except Exception:
			pass
	if par.name in WATCHED:
		_sync_menus()   # refilter the cascade for the new selection
		_apply()        # follow it with the effect
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
