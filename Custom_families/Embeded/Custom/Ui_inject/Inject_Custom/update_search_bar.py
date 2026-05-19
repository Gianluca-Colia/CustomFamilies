# me - this DAT
# Callback DAT for a datexecuteDAT that watches
# /ui/dialogs/menu_op/search/string. TouchDesigner does NOT propagate
# Text DAT edits as a cooking dependency to script DATs that read them,
# so deleting characters in the search bar wouldn't refresh the filtered
# table until the user clicked outside (focus loss event triggered the
# delayed cook). This datexecute closes that gap: any change to the
# search text forces every inject_<family> Script DAT in menu_op to
# re-cook with the fresh search string.

NODETABLE_PATH = '/ui/dialogs/menu_op/nodetable'


def _safe_op(path):
    try:
        return op(path)
    except Exception:
        return None


CF_DEBUG = True  # set False once verified


def _dbg(*args):
    if not CF_DEBUG:
        return
    try:
        print('[update_search_bar]', *args)
    except Exception:
        pass


def _force_recook_injects():
    _dbg('fire')
    parent_comp = _safe_op(NODETABLE_PATH)
    if parent_comp is None:
        _dbg('no nodetable, abort')
        return
    try:
        children = list(parent_comp.children)
    except Exception:
        return

    for child in children:
        try:
            if not str(child.name).startswith('inject_'):
                continue
        except Exception:
            continue

        # Each inject_<family> COMP wraps a Script DAT with the same name.
        inner = None
        try:
            inner = child.op(child.name)
        except Exception:
            inner = None
        if inner is None:
            # Fallback: find any Script DAT child.
            try:
                for c in child.children:
                    if 'script' in (getattr(c, 'type', '') or '').lower():
                        inner = c
                        break
            except Exception:
                pass
        if inner is None:
            continue

        try:
            inner.store('cf_last_state', None)
        except Exception:
            pass
        try:
            inner.cook(force=True)
        except Exception:
            pass


def _watched_value(dat):
    if dat is None:
        return '<dat=None>'
    try:
        if dat.numRows == 1 and dat.numCols == 1:
            return repr(str(dat[0, 0].val))
        return repr(str(dat.text))
    except Exception as e:
        return '<err: {}>'.format(e)


def onTableChange(dat):
    _dbg('onTableChange  watched={}  value={}'.format(dat.path if dat else None, _watched_value(dat)))
    _force_recook_injects()


def onRowChange(dat, rows):
    _dbg('onRowChange    watched={}  rows={}  value={}'.format(dat.path if dat else None, rows, _watched_value(dat)))
    _force_recook_injects()


def onColChange(dat, cols):
    _dbg('onColChange    watched={}  cols={}  value={}'.format(dat.path if dat else None, cols, _watched_value(dat)))
    _force_recook_injects()


def onCellChange(dat, cells, prev):
    _dbg('onCellChange   watched={}  prev={!r}  value={}'.format(dat.path if dat else None, prev, _watched_value(dat)))
    _force_recook_injects()


def onSizeChange(dat):
    _dbg('onSizeChange   watched={}  value={}'.format(dat.path if dat else None, _watched_value(dat)))
    _force_recook_injects()
