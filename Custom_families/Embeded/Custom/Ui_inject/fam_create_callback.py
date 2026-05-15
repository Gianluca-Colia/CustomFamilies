# me - this DAT
# scriptOp - the OP which is cooking

CUSTOM_ROOT_NAMES = ('custom_operators', 'Custom_operators')
GROUP_FALLBACK_NAME = 'Other'
LAYOUT_ROOT_TEMPLATE = 'layouts/{family}'
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

def _source_op():
    for depth in range(1, 7):
        try:
            candidate = parent(depth)
        except Exception:
            candidate = None
        if candidate is None:
            continue
        try:
            if candidate.op('InstallerEXT') is not None or candidate.op('ComponentEXT') is not None:
                return candidate
        except Exception:
            pass

    try:
        ref = str(iop.Internal_reference.par.Globalshortcut.eval()).strip()
    except Exception:
        ref = ''

    if not ref:
        return None

    for candidate in (ref, '/{}'.format(ref)):
        try:
            o = op(candidate)
            if o is not None:
                return o
        except Exception:
            pass

    try:
        return getattr(op, ref, None)
    except Exception:
        return None

def _family_name(source_op):
    if source_op is None:
        return ''
    try:
        return str(source_op.par.opshortcut.eval()).strip()
    except Exception:
        return ''

def _custom_root(source_op):
    if source_op is None:
        return None
    for child_name in CUSTOM_ROOT_NAMES:
        try:
            root = source_op.op(child_name)
            if root is not None:
                return root
        except Exception:
            pass
    return None

def _component_ext(source_op):
    if source_op is None:
        return None

    for attr_name in ('ComponentEXT', 'componentExt'):
        try:
            ext_obj = getattr(source_op, attr_name, None)
            if ext_obj is not None:
                return ext_obj
        except Exception:
            pass

    try:
        namespace = getattr(source_op, 'ext', None)
    except Exception:
        namespace = None

    for attr_name in ('ComponentEXT', 'componentExt'):
        try:
            ext_obj = getattr(namespace, attr_name, None) if namespace is not None else None
            if ext_obj is not None:
                return ext_obj
        except Exception:
            pass
    return None

def _installer(source_op):
    component_ext = _component_ext(source_op)
    if component_ext is None or not hasattr(component_ext, '_GetInstallerBridge'):
        return None
    try:
        return component_ext._GetInstallerBridge()
    except Exception:
        return None

def _storage_mode(custom_op):
    if custom_op is None:
        return
    for setter in (
        lambda: setattr(custom_op, 'allowCooking', False),
        lambda: setattr(custom_op, 'bypass', True),
        lambda: setattr(custom_op.par, 'bypass', 1) if hasattr(custom_op, 'par') and hasattr(custom_op.par, 'bypass') else None,
    ):
        try:
            setter()
        except Exception:
            pass

def _finalize_custom_operator(custom_op_path):
    custom_op = op(custom_op_path) if custom_op_path else None
    if custom_op is None:
        return

    try:
        custom_op.store('custom_template_finalize_pending', False)
    except Exception:
        pass

    installer = _installer(_source_op())
    if installer is not None and hasattr(installer, 'RefreshCustomOperatorTemplate'):
        try:
            installer.RefreshCustomOperatorTemplate(custom_op)
        except Exception:
            pass

    _storage_mode(custom_op)

def _schedule_finalize(custom_op):
    if custom_op is None:
        return

    try:
        if custom_op.fetch('custom_template_finalize_pending', False):
            return
        custom_op.store('custom_template_finalize_pending', True)
    except Exception:
        pass

    try:
        run(
            "op(args[0]).module._finalize_custom_operator(args[1])",
            me.path,
            custom_op.path,
            delayFrames=2,
            delayRef=op.TDResources
        )
    except Exception:
        try:
            custom_op.store('custom_template_finalize_pending', False)
        except Exception:
            pass

def _refresh_runtime(source_op, ops):
    installer = _installer(source_op)
    if installer is None or not hasattr(installer, 'RefreshCustomOperatorTemplate'):
        return

    for custom_op in ops:
        try:
            if custom_op is None or custom_op.family != 'COMP':
                continue
        except Exception:
            continue

        try:
            installer.RefreshCustomOperatorTemplate(custom_op)
        except Exception:
            continue

        _storage_mode(custom_op)
        _schedule_finalize(custom_op)

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
    def_name = 'defGenerator' if len(o.inputConnectors) == 0 else 'defFilter'
    return _layout_path(family_name, def_name)

def _max_inputs(o):
    return 9999 if o.name == 'composite' else len(o.inputConnectors)

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    source_op = _source_op()
    custom_root = _custom_root(source_op)

    scriptOp.clear()
    scriptOp.appendRow(TABLE_HEADER)
    if custom_root is None:
        return

    try:
        _ = custom_root.numChildren
        _ = [c.name for c in custom_root.children]
    except Exception:
        pass

    family_name = _family_name(source_op)

    try:
        ops = sorted([o for o in custom_root.children if o is not None], key=_sort_key)
    except Exception:
        ops = []

    _refresh_runtime(source_op, ops)

    current_group = None
    for operator_comp in ops:
        group_name = _group_name(operator_comp)
        if group_name != current_group:
            current_group = group_name
            scriptOp.appendRow(['', current_group, _layout_path(family_name, 'defLabel')])

        name = operator_comp.name
        scriptOp.appendRow([
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

