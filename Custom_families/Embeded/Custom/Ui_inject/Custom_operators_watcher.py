"""
OP Execute DAT — Custom_operators_watcher

Watches the Custom_operators COMP of the family. Rebuilds the sibling
table `Custom_operator_list` whenever something structural changes
(child added/removed/renamed, watched COMP recooks, etc.).

This replaces the side-effect-laden `fam_create` Script DAT pattern.
Here the callbacks are event-driven: no cooking loop, no per-frame
re-build, no refresh of operator templates from inside cook.

The watcher's `Monitor OPs` parameter must point to the family's
Custom_operators COMP (e.g. `parent(2).op('Custom_operators')`).

`me`        — this DAT (the opexec).
`changeOp`  — the operator that triggered the event (the watched COMP).
"""

from typing import Any

# --------------------------------------------------------------------------
# Configuration

TARGET_TABLE_NAME = 'Custom_operator_list'
LAYOUT_ROOT_TEMPLATE = 'layouts/{family}'
GROUP_FALLBACK_NAME = 'Other'

TABLE_HEADER = [
    'name', 'label', 'type', 'subtype', 'mininputs', 'maxinputs',
    'ordering', 'level', 'lictype', 'os', 'score', 'family', 'opType'
]

DEFAULTS = {
    'subtype': '2',
    'mininputs': '0',
    'level': '1',
    'lictype': 'TouchDesigner Non-Commercial',
    'os': '1',
    'score': '3',
}


# --------------------------------------------------------------------------
# Lookups

def _family_comp():
    """Return the family COMP that owns this watcher.

    The watcher lives at <family>/Ui_inject/Custom_operators_watcher, so
    `me.parent(2)` is the family COMP. Falls back to walking parents
    looking for one with `InstallerEXT` or `ComponentEXT`.
    """
    try:
        return me.parent(2)
    except Exception:
        pass
    for depth in range(1, 7):
        try:
            candidate = me.parent(depth)
        except Exception:
            candidate = None
        if candidate is None:
            continue
        try:
            if candidate.op('InstallerEXT') is not None or candidate.op('ComponentEXT') is not None:
                return candidate
        except Exception:
            pass
    return None


def _family_name(family_comp):
    if family_comp is None:
        return ''
    try:
        value = str(family_comp.par.opshortcut.eval()).strip()
        if value:
            return value
    except Exception:
        pass
    try:
        return str(family_comp.name)
    except Exception:
        return ''


def _custom_root(family_comp):
    if family_comp is None:
        return None
    for child_name in ('Custom_operators', 'custom_operators'):
        try:
            root = family_comp.op(child_name)
            if root is not None:
                return root
        except Exception:
            pass
    return None


def _target_table():
    try:
        return me.parent().op(TARGET_TABLE_NAME)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Row building helpers (same conventions as the old fam_create_callback)

def _layout_path(family_name, def_name):
    return '{}/{}'.format(LAYOUT_ROOT_TEMPLATE.format(family=family_name), def_name)


def _group_name(o):
    try:
        tags = list(o.tags)
        return str(tags[0]) if tags else GROUP_FALLBACK_NAME
    except Exception:
        return GROUP_FALLBACK_NAME


def _label(name):
    return ' '.join(word.capitalize() for word in name.split('_'))


def _sort_key(o):
    return (_group_name(o), _label(o.name).lower())


def _type_layout(o, family_name):
    try:
        def_name = 'defGenerator' if len(o.inputConnectors) == 0 else 'defFilter'
    except Exception:
        def_name = 'defFilter'
    return _layout_path(family_name, def_name)


def _max_inputs(o):
    try:
        if o.name == 'composite':
            return 9999
        return len(o.inputConnectors)
    except Exception:
        return 1


# --------------------------------------------------------------------------
# Core: rebuild the Custom_operator_list table

def _rebuild_table():
    """Recompute and write the operator list table from scratch."""
    target = _target_table()
    if target is None:
        return

    family_comp = _family_comp()
    custom_root = _custom_root(family_comp)
    family_name = _family_name(family_comp)

    target.clear()
    target.appendRow(TABLE_HEADER)
    if custom_root is None:
        return

    try:
        ops = sorted([o for o in custom_root.children if o is not None], key=_sort_key)
    except Exception:
        ops = []

    current_group = None
    for operator_comp in ops:
        group_name = _group_name(operator_comp)
        if group_name != current_group:
            current_group = group_name
            target.appendRow(['', current_group, _layout_path(family_name, 'defLabel')])

        name = operator_comp.name
        target.appendRow([
            name,
            _label(name),
            _type_layout(operator_comp, family_name),
            DEFAULTS['subtype'],
            DEFAULTS['mininputs'],
            _max_inputs(operator_comp),
            True,
            DEFAULTS['level'],
            DEFAULTS['lictype'],
            DEFAULTS['os'],
            DEFAULTS['score'],
            family_name,
            name + family_name,
        ])


# Public alias — can be called from anywhere to force a rebuild.
def rebuild():
    _rebuild_table()


# --------------------------------------------------------------------------
# OP Execute callbacks
#
# All structural events rebuild the table. Other events (UI change, flag
# change, ecc.) are intentionally left as no-ops because they don't
# affect the rows we produce — keeping them quiet means zero work when
# nothing meaningful changed.

def onPreCook(changeOp: OP):
    return


def onPostCook(changeOp: OP):
    # Useful for the initial population when the watched COMP first cooks.
    _rebuild_table()


def onDestroy():
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
    # New operator added or removed inside Custom_operators.
    _rebuild_table()


def onChildRename(changeOp: OP):
    # A custom operator was renamed — label/name in the table change.
    _rebuild_table()


def onCurrentChildChange(changeOp: OP):
    return


def onExtensionChange(changeOp: OP, extension: Any):
    return
