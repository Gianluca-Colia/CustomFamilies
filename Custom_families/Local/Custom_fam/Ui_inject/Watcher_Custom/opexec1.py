"""
OP Execute DAT — Level-3 cleanup bridge.

When the watched family component is destroyed, this DAT is the last
resort: it independently scans /ui/panes/panebar/pane1/Local_bar and
/ui/dialogs/menu_op for all ops that belong to this family and
destroys them, then self-destructs.

It does NOT call UninstallerEXT (that is Level 2, handled by
Delete_op_execute).  It works even if the family COMP is already gone,
because it derives the family name from its own stored data / tags.
"""

import re
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_op(path):
    try:
        return op(path)
    except Exception:
        return None


def _sanitize_name(name):
    name = '' if name is None else str(name).strip().replace(' ', '')
    name = re.sub(r'[^A-Za-z0-9_]', '', name)
    return '_' + name if name and name[0].isdigit() else name


def _get_watcher():
    try:
        return parent()
    except Exception:
        return None


def _get_family_name():
    """Derive family name without relying on the family COMP (may be gone)."""
    watcher = _get_watcher()
    if watcher is None:
        return ''

    # 1) stored cf_family_name (set by _install_watcher)
    try:
        name = str(watcher.fetch('cf_family_name', '')).strip()
        if name:
            return _sanitize_name(name)
    except Exception:
        pass

    # 2) stored delete_family_name (set by _install_delete_execute_watcher)
    try:
        name = str(watcher.fetch('delete_family_name', '')).strip()
        if name:
            return _sanitize_name(name)
    except Exception:
        pass

    # 3) watcher tags — _install_watcher appends family_name to tags
    try:
        for tag in watcher.tags:
            cleaned = _sanitize_name(tag)
            if cleaned and cleaned != 'Custom':
                return cleaned
    except Exception:
        pass

    # 4) derive from watcher name (watcher_FamilyName)
    try:
        wname = watcher.name
        if wname.startswith('watcher_'):
            candidate = _sanitize_name(wname[len('watcher_'):])
            if candidate:
                return candidate
    except Exception:
        pass

    return ''


def _get_owner_path():
    watcher = _get_watcher()
    if watcher is None:
        return ''
    try:
        return str(watcher.fetch('cf_owner_path', '')).strip()
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Direct bookmark_bar scan — independent of opfind1
# ---------------------------------------------------------------------------

def _bookmark_bar_family_ops(family_name):
    """Return all ops in bookmark_bar that belong to family_name."""
    if not family_name:
        return []
    bookmark_bar = _safe_op('/ui/panes/panebar/pane1/Local_bar')
    if bookmark_bar is None:
        return []

    watcher = _get_watcher()
    watcher_path = ''
    owner_path = _get_owner_path()
    try:
        watcher_path = watcher.path if watcher is not None else ''
    except Exception:
        pass

    patterns = {
        'button_{}'.format(family_name),
        '{}_toggle'.format(family_name),
        '{}_button'.format(family_name),
        'delete_execute_{}'.format(family_name),
        '{}_delete_execute'.format(family_name),
        'watcher_{}'.format(family_name),
        '{}_watcher'.format(family_name),
        family_name,
    }

    found = []
    seen = set()

    # Pass 1: direct name lookup
    for name in patterns:
        try:
            target = bookmark_bar.op(name)
        except Exception:
            target = None
        if target is None:
            continue
        try:
            path = target.path
        except Exception:
            continue
        if path in seen:
            continue
        seen.add(path)
        found.append(target)

    # Pass 2: scan all children for any remaining matches.  Installed family
    # buttons store cf_family_name, so use that as the stable identity instead
    # of relying only on button names.
    try:
        children = bookmark_bar.findChildren(depth=None, maxDepth=2)
    except Exception:
        children = []
    for child in children:
        if child is None:
            continue
        try:
            path = child.path
            name = child.name
        except Exception:
            continue
        if path in seen:
            continue
        try:
            stored_family = _sanitize_name(child.fetch('cf_family_name', ''))
        except Exception:
            stored_family = ''
        try:
            stored_delete_family = _sanitize_name(child.fetch('delete_family_name', ''))
        except Exception:
            stored_delete_family = ''
        try:
            stored_owner_path = str(child.fetch('cf_owner_path', '')).strip()
        except Exception:
            stored_owner_path = ''
        if (
            name in patterns
            or stored_family == family_name
            or stored_delete_family == family_name
            or (owner_path and stored_owner_path == owner_path)
        ):
            seen.add(path)
            found.append(child)

    # Sort: button first, watcher last (watcher self-destructs separately)
    def sort_key(t):
        try:
            n = t.name
        except Exception:
            n = ''
        if n == watcher_path.split('/')[-1] or t.path == watcher_path:
            return 2   # watcher last
        if n.startswith('button_') or n.endswith('_button') or n.endswith('_toggle'):
            return 0   # button first
        return 1

    found.sort(key=sort_key)
    return found


def _menu_op_family_ops(family_name):
    """Return all ops in menu_op and node_table that belong to family_name."""
    if not family_name:
        return []

    roots = [
        _safe_op('/ui/dialogs/menu_op'),
        _safe_op('/ui/dialogs/menu_op/nodetable'),
    ]

    patterns = {
        'insert_{}'.format(family_name),
        '{}_insert'.format(family_name),
        'panel_execute_{}'.format(family_name),
        '{}_panel_execute'.format(family_name),
        'inject_{}_fam'.format(family_name),
        'inject_{}'.format(family_name),
        '{}_fam'.format(family_name),
    }

    found = []
    seen = set()
    for root in roots:
        if root is None:
            continue
        for name in patterns:
            try:
                target = root.op(name)
            except Exception:
                target = None
            if target is None:
                continue
            try:
                path = target.path
            except Exception:
                continue
            if path in seen:
                continue
            seen.add(path)
            found.append(target)

    return found


# ---------------------------------------------------------------------------
# Rewire helpers (kept from original for insert/inject rewiring)
# ---------------------------------------------------------------------------

def _first_input_op(target):
    try:
        inputs = getattr(target, 'inputs', None)
        if inputs:
            for current in inputs:
                if current is not None:
                    return current
    except Exception:
        pass
    for attr_name in ('inputConnectors', 'inputCOMPConnectors'):
        try:
            connectors = getattr(target, attr_name, None)
        except Exception:
            connectors = None
        if not connectors:
            continue
        for connector in connectors:
            try:
                connections = getattr(connector, 'connections', None)
            except Exception:
                connections = None
            if not connections:
                continue
            for connection in connections:
                for owner_attr in ('owner', 'ownerOP', 'OP', 'op'):
                    try:
                        upstream = getattr(connection, owner_attr, None)
                    except Exception:
                        upstream = None
                    if upstream is not None and upstream != target:
                        return upstream
    return None


# ---------------------------------------------------------------------------
# Colors table cleanup
# ---------------------------------------------------------------------------

def _cleanup_colors_table(family_name):
    if not family_name:
        return
    try:
        colors_table = _safe_op('/ui/dialogs/menu_op/colors')
        if colors_table is None:
            return
        target_val = "'{}'".format(family_name)
        for row_i in range(colors_table.numRows - 1, -1, -1):
            try:
                if colors_table[row_i, 0].val == target_val:
                    colors_table.deleteRow(row_i)
                    break
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main delayed-destroy runner
# ---------------------------------------------------------------------------

def _destroy_ops_later(bookmark_ops, menu_ops, family_name):
    watcher = _get_watcher()
    watcher_path = ''
    try:
        watcher_path = watcher.path if watcher is not None else ''
    except Exception:
        pass

    # Collect paths, excluding the watcher itself AND any of its descendants.
    # The watcher self-destructs at the very end (inner deferred run); destroying
    # our own opexec1 DAT mid-loop raises "Operator has been deleted" and aborts
    # the rest of the iteration before menu_op residues are processed.
    watcher_prefix = watcher_path + '/' if watcher_path else ''
    paths = []
    host_candidates = []
    for target in bookmark_ops + menu_ops:
        try:
            target_path = target.path
        except Exception:
            continue
        try:
            is_watcher = (watcher is not None and target == watcher)
        except Exception:
            is_watcher = False
        if is_watcher:
            continue
        if watcher_prefix and target_path.startswith(watcher_prefix):
            continue
        paths.append(target_path)
        try:
            parent_path = target.parent().path
        except Exception:
            parent_path = ''
        if parent_path and parent_path not in host_candidates:
            host_candidates.append(parent_path)

    run(
        """
def _first_input(target):
    try:
        inputs = getattr(target, 'inputs', None)
        if inputs:
            for current in inputs:
                if current is not None:
                    return current
    except Exception:
        pass
    for attr_name in ('inputConnectors', 'inputCOMPConnectors'):
        try:
            connectors = getattr(target, attr_name, None)
        except Exception:
            connectors = None
        if not connectors:
            continue
        for connector in connectors:
            try:
                connections = getattr(connector, 'connections', None)
            except Exception:
                connections = None
            if not connections:
                continue
            for connection in connections:
                for owner_attr in ('owner', 'ownerOP', 'OP', 'op'):
                    try:
                        upstream = getattr(connection, owner_attr, None)
                    except Exception:
                        upstream = None
                    if upstream is not None and upstream != target:
                        return upstream
    return None

def _downstream_inputs(target):
    results = []
    seen = set()
    try:
        outputs = getattr(target, 'outputs', None)
        if outputs:
            for downstream in outputs:
                if downstream is None:
                    continue
                try:
                    key = downstream.path
                except Exception:
                    key = str(id(downstream))
                if key in seen:
                    continue
                seen.add(key)
                results.append((downstream, 0))
    except Exception:
        pass
    for attr_name in ('outputConnectors', 'outputCOMPConnectors'):
        try:
            connectors = getattr(target, attr_name, None)
        except Exception:
            connectors = None
        if not connectors:
            continue
        for connector in connectors:
            try:
                connections = getattr(connector, 'connections', None)
            except Exception:
                connections = None
            if not connections:
                continue
            for connection in connections:
                downstream = None
                for owner_attr in ('owner', 'ownerOP', 'OP', 'op'):
                    try:
                        candidate = getattr(connection, owner_attr, None)
                    except Exception:
                        candidate = None
                    if candidate is not None and candidate != target:
                        downstream = candidate
                        break
                if downstream is None:
                    continue
                input_index = 0
                for index_attr in ('inputIndex', 'index'):
                    try:
                        value = getattr(connection, index_attr, None)
                    except Exception:
                        value = None
                    if isinstance(value, int):
                        input_index = value
                        break
                try:
                    key = '{}:{}'.format(downstream.path, input_index)
                except Exception:
                    key = '{}:{}'.format(id(downstream), input_index)
                if key in seen:
                    continue
                seen.add(key)
                results.append((downstream, input_index))
    return results

def _rewire_around(target):
    upstream = _first_input(target)
    if upstream is None:
        return False
    restore_families_link = False
    for downstream, input_index in _downstream_inputs(target):
        try:
            downstream.inputConnectors[input_index].connect(upstream)
            try:
                if getattr(upstream, 'name', '') == 'in1' and getattr(downstream, 'name', '') == 'families':
                    restore_families_link = True
            except Exception:
                pass
            continue
        except Exception:
            pass
        try:
            downstream.inputCOMPConnectors[input_index].connect(upstream)
            try:
                if getattr(upstream, 'name', '') == 'in1' and getattr(downstream, 'name', '') == 'families':
                    restore_families_link = True
            except Exception:
                pass
        except Exception:
            pass
    return restore_families_link

watcher_path = args[-2] if len(args) > 1 else ''
host_candidates = list(args[-1].split('|')) if args and args[-1] else []
paths = list(args[:-2]) if len(args) > 1 else []
restore_families = False
for raw_path in paths:
    target = op(raw_path)
    if target is None:
        continue
    try:
        if _rewire_around(target):
            restore_families = True
    except Exception:
        pass
    # Unlock + disable cooking before destroy: bookmark_bar children are
    # often locked, which makes destroy() silently no-op.
    for attr_name in ('lock', 'allowCooking'):
        try:
            setattr(target, attr_name, False)
        except Exception:
            pass
    try:
        if hasattr(target, 'par') and hasattr(target.par, 'lock'):
            target.par.lock = 0
    except Exception:
        pass
    try:
        target.destroy()
    except Exception as destroy_err:
        debug('opexec1 destroy raised for {}: {}'.format(raw_path, destroy_err))
    # Verify: if op still exists, force destroy via parent + warn.
    survivor = op(raw_path)
    if survivor is not None:
        try:
            survivor_parent = survivor.parent()
        except Exception:
            survivor_parent = None
        try:
            survivor.lock = False
        except Exception:
            pass
        try:
            survivor.destroy()
        except Exception as e2:
            debug('opexec1 second destroy raised for {}: {}'.format(raw_path, e2))
        if op(raw_path) is not None:
            debug('opexec1 FAILED to destroy {} (parent={})'.format(
                raw_path,
                survivor_parent.path if survivor_parent is not None else 'None'))
host = None
for candidate_path in host_candidates:
    try:
        candidate = op(candidate_path)
    except Exception:
        candidate = None
    try:
        families = candidate.op('families') if candidate is not None else None
    except Exception:
        families = None
    try:
        in1 = candidate.op('in1') if candidate is not None else None
    except Exception:
        in1 = None
    if families is not None and in1 is not None:
        host = candidate
        break
if host is not None:
    if restore_families:
        try:
            if hasattr(families, 'allowCooking'):
                families.allowCooking = True
            if hasattr(families, 'bypass'):
                families.bypass = False
            if hasattr(families.par, 'bypass'):
                families.par.bypass = 0
        except Exception:
            pass
if watcher_path:
    run(
        "target = op(args[0]); target.destroy() if target is not None else None",
        watcher_path,
        delayFrames=1
    )
""",
        *paths,
        watcher_path,
        '|'.join(host_candidates),
        delayFrames=2
    )
    return True


def onDestroy(changeOp=None):
    """
    Level 3 — last-resort cleanup.

    Called when the watched family COMP is destroyed.  At this point the
    family COMP may no longer exist, so we derive everything from stored
    data on the watcher itself.
    """
    family_name = _get_family_name()

    # Clean up colors table immediately (can be done synchronously)
    _cleanup_colors_table(family_name)

    # Collect all UI residues via direct scan (independent of opfind1)
    bookmark_ops = _bookmark_bar_family_ops(family_name)
    menu_ops = _menu_op_family_ops(family_name)

    return _destroy_ops_later(bookmark_ops, menu_ops, family_name)


def onPreCook(changeOp: OP):
    return


def onPostCook(changeOp: OP):
    return


def onFlagChange(changeOp: OP, flag: str):
    return


def onWireChange(changeOp: OP):
    return


def onNameChange(changeOp: OP):
    return


def onPathChange(changeOp: OP):
    return


def onUIChange(changeOp: OP):
    return


def onNumChildrenChange(changeOp: OP):
    return


def onChildRename(changeOp: OP):
    return


def onCurrentChildChange(changeOp: OP):
    return


def onExtensionChange(changeOp: OP, extension: Any):
    return
