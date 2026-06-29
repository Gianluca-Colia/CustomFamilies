# AEOP - menu builder (TD node side)  --  CHOP Execute DAT
# =====================================================================
# Rebuilds the node's Type / Comp / Layer selection menus from the layers
# streamed by After Effects, so every layer is listed BEFORE any Spout effect
# is applied. Applying the effect is handled by aeSpout_exec.py.
#
# DAT TYPE: this is a *CHOP Execute DAT* - attach it to the CHOP that carries
# the incoming AE layer signal (e.g. the OSC In CHOP / a count). Any change
# triggers a GUARDED rebuild (only when the comp/layer/type STRUCTURE actually
# changed, so frequent transform updates don't rebuild the menus every frame).
#
# The Type/Comp PARAMETER cascade (user picks a different type/comp) is driven
# by aeSpout_exec.py (Parameter Execute), which calls Rebuild() here.
#
# CONFIGURE (TODO - point these at the node's actual data):
#   DATA_TABLE : a Table DAT (one row per known layer) with columns
#                comp, layer, type, index (header row).
#   Custom pars assumed named Type, Comp, Layer (menus); the Layer menu's
#   VALUE is the AE layer index, its LABEL is the layer name.
# =====================================================================

DATA_TABLE = 'layers'        # TODO: name/path of the received-layer Table DAT
TYPE_PAR = 'Type'
COMP_PAR = 'Comp'
LAYER_PAR = 'Layer'
COL_COMP = 'comp'
COL_LAYER = 'layer'
COL_TYPE = 'type'
COL_INDEX = 'index'

_last_sig = ['']             # persists between cooks (module stays loaded)


def _table():
	return parent().op(DATA_TABLE)


def _rows():
	"""List of dict rows from the data table, or [] if missing/empty."""
	t = _table()
	out = []
	if t is None or t.numRows < 2:
		return out
	def cell(r, c):
		x = t[r, c]
		return x.val if x is not None else ''
	for r in range(1, t.numRows):
		out.append({
			'comp':  cell(r, COL_COMP),
			'layer': cell(r, COL_LAYER),
			'type':  cell(r, COL_TYPE),
			'index': cell(r, COL_INDEX),
		})
	return out


def _set_menu(par_name, names, labels=None):
	"""Set a custom menu par's items, keeping the current value if still valid."""
	try:
		p = parent().par[par_name]
	except Exception:
		return
	if not names:
		names = ['']
	p.menuNames = names
	p.menuLabels = labels if labels else names
	if p.eval() not in names:
		p.val = names[0]


def _rebuild_comps():
	wanted = parent().par[TYPE_PAR].eval()
	seen = []
	for row in _rows():
		if row['type'] == wanted and row['comp'] and row['comp'] not in seen:
			seen.append(row['comp'])
	_set_menu(COMP_PAR, seen)


def _rebuild_layers():
	wanted = parent().par[TYPE_PAR].eval()
	comp = parent().par[COMP_PAR].eval()
	names, labels = [], []
	for row in _rows():
		if row['type'] == wanted and row['comp'] == comp and row['layer']:
			names.append(str(row['index']))   # value = AE layer index
			labels.append(row['layer'])       # label = layer name
	_set_menu(LAYER_PAR, names, labels)


def Rebuild():
	"""Full menu rebuild from the current Type/Comp selection."""
	try:
		_rebuild_comps()
		_rebuild_layers()
	except Exception as exc:
		debug('[AEOP menu] rebuild failed: {}'.format(exc))


def _structure_sig():
	"""A compact string of the comp/type/layer structure (NOT transforms), so
	we only rebuild when the set of selectable layers actually changes."""
	parts = []
	for r in _rows():
		parts.append(r['type'] + '/' + r['comp'] + '/' + str(r['index']) + '/' + r['layer'])
	return '|'.join(parts)


def _maybe_rebuild():
	sig = _structure_sig()
	if sig != _last_sig[0]:
		_last_sig[0] = sig
		Rebuild()


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
	_maybe_rebuild()
	return
