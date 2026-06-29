# AEOP - menu builder (TD node side)
# =====================================================================
# Parameter Execute DAT for the AEOP node. Keeps the node's selection menus
# in sync with the layers streamed from After Effects:
#   - Type  -> filters which layers are eligible (shape / solid / text / ...)
#   - Comp  -> the comps that contain at least one layer of that Type
#   - Layer -> the layers of that Type inside the selected Comp
#
# The menus are built from the RECEIVED-LAYER table (the data the CEP panel /
# query streams as /ae/layer, /ae/layer_bake), so every layer is listed BEFORE
# any Spout effect is applied. Applying the effect is handled separately by
# aeSpout_exec.py (it fires on the Comp/Layer change this script reacts to).
#
# CONFIGURE (TODO - point these at the node's actual data):
#   DATA_TABLE   : a Table DAT with one row per known layer and columns
#                  project, comp, layer, type, index (header row).
#   The custom pars are assumed named Type, Comp, Layer (menus).
# =====================================================================

DATA_TABLE = 'layers'        # TODO: name/path of the received-layer Table DAT
TYPE_PAR = 'Type'
COMP_PAR = 'Comp'
LAYER_PAR = 'Layer'
COL_COMP = 'comp'
COL_LAYER = 'layer'
COL_TYPE = 'type'
COL_INDEX = 'index'


def _table():
	return parent().op(DATA_TABLE)


def _rows():
	"""List of dict rows from the data table, or [] if missing/empty."""
	t = _table()
	out = []
	if t is None or t.numRows < 2:
		return out
	for r in range(1, t.numRows):
		out.append({
			'comp':  t[r, COL_COMP].val if t[r, COL_COMP] else '',
			'layer': t[r, COL_LAYER].val if t[r, COL_LAYER] else '',
			'type':  t[r, COL_TYPE].val if t[r, COL_TYPE] else '',
			'index': t[r, COL_INDEX].val if t[r, COL_INDEX] else '',
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
			# menu value = AE layer index (what aeSpout_exec sends); label = name
			names.append(str(row['index']))
			labels.append(row['layer'])
	_set_menu(LAYER_PAR, names, labels)


def Rebuild():
	"""Full rebuild (call from a DAT/CHOP Execute when fresh data arrives)."""
	_rebuild_comps()
	_rebuild_layers()


# ----- Parameter Execute DAT callbacks (full standard set) -----

def onValueChange(par, prev):
	if par.name == TYPE_PAR:
		_rebuild_comps()
		_rebuild_layers()
	elif par.name == COMP_PAR:
		_rebuild_layers()
	return

def onPulse(par):
	return

def onExpressionChange(par, val, prev):
	return

def onExportChange(par, val, prev):
	return

def onEnableChange(par, val, prev):
	return

def onModeChange(par, val, prev):
	return
