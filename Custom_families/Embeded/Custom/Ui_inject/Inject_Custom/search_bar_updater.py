# CF search watch — ricucina fam_script quando cambia la search bar.
# Posizionato dentro: /ui/dialogs/menu_op/nodetable/inject_<FAM>/cf_search_watch
# Bind del par.dat: /ui/dialogs/menu_op/search/string

NODETABLE_PATH = '/ui/dialogs/menu_op/nodetable'


def _fam_script():
    """Restituisce il fam_script DAT della famiglia corrente.
    parent() = inject_<FAM>, il fam_script è il figlio scriptDAT
    con lo stesso nome del parent."""
    p = me.parent()
    if p is None:
        return None
    fs = p.op(p.name)
    if fs is not None:
        return fs
    # Fallback: primo scriptDAT figlio
    for c in p.children:
        try:
            if c.OPType == 'scriptDAT':
                return c
        except Exception:
            pass
    return None


def _recook():
    fs = _fam_script()
    if fs is not None:
        try:
            fs.cook(force=True)
        except Exception:
            pass
    nt = op(NODETABLE_PATH)
    if nt is None:
        return
    for nm in ('sort1', 'destil'):
        d = nt.op(nm)
        if d is None:
            continue
        try:
            d.cook(force=True)
        except Exception:
            pass


def onTableChange(dat): _recook()
def onRowChange(dat, rows): _recook()
def onColChange(dat, cols): _recook()
def onCellChange(dat, cells, prev): _recook()
def onSizeChange(dat): _recook()