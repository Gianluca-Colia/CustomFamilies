# me - this DAT
# Callback module for the datexecuteDAT that watches the search-bar Text
# DAT in /ui/dialogs/menu_op. TouchDesigner does NOT propagate edits of
# that Text DAT as a cooking dependency to script DATs that read it, so
# deleting characters in the search bar wouldn't refresh the filtered
# table until a focus-loss event finally triggered a cook. This module
# closes the gap: any change to the watched DAT forces every
# inject_<family> Script DAT in the nodetable to re-cook with the fresh
# search string.

NODETABLE_PATH = '/ui/dialogs/menu_op/nodetable'


def _safe_op(path):
    try:
        return op(path)
    except Exception:
        return None


def _force_recook_injects():
    parent_comp = _safe_op(NODETABLE_PATH)
    if parent_comp is None:
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


def onTableChange(dat):
    _force_recook_injects()


def onRowChange(dat, rows):
    _force_recook_injects()


def onColChange(dat, cols):
    _force_recook_injects()


def onCellChange(dat, cells, prev):
    _force_recook_injects()


def onSizeChange(dat):
    _force_recook_injects()
