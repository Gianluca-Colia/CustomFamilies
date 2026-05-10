# me - this DAT

FAMILY_NAME = 'RSA'
CURRENT_TABLE_PATH = '/ui/dialogs/menu_op/current'
MENU_VAR_PATHS = (
    '/ui/dialogs/menu_op/local/set_variables',
    '/ui/dialogs/menu_op/set_variables',
)
OP_FAM_TABLE_NAME = 'OP_fam'
PLACEMENT_SENTINEL = (-36109.0, -36109.0)

def _safe_op(path):
    try:
        return op(path)
    except Exception:
        return None

def _active_family_name():
    current_dat = _safe_op(CURRENT_TABLE_PATH)
    if current_dat is not None:
        try:
            value = str(current_dat[0, 0].val).strip()
            if value:
                return value
        except Exception:
            pass
    return str(FAMILY_NAME).strip()

def _looks_like_family(comp):
    if comp is None:
        return False
    try:
        if comp.op(OP_FAM_TABLE_NAME) is not None:
            return True
    except Exception:
        pass
    try:
        return bool(comp.findChildren(name=OP_FAM_TABLE_NAME, maxDepth=3))
    except Exception:
        return False

def _family_op(family_name=None):
    family_name = str(family_name or _active_family_name()).strip()
    if not family_name:
        return None

    candidates = []
    try:
        candidates.append(getattr(op, family_name, None))
    except Exception:
        pass
    candidates.append(_safe_op('/{}'.format(family_name)))

    project_root = _safe_op('/')
    if project_root is not None:
        try:
            candidates.extend(project_root.findChildren(maxDepth=6))
        except Exception:
            pass

    seen = set()
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            candidate_path = candidate.path
        except Exception:
            candidate_path = str(id(candidate))
        if candidate_path in seen:
            continue
        seen.add(candidate_path)
        if not _looks_like_family(candidate):
            continue
        try:
            if candidate.name == family_name:
                return candidate
        except Exception:
            pass
        try:
            if hasattr(candidate.par, 'opshortcut') and str(candidate.par.opshortcut.eval()).strip() == family_name:
                return candidate
        except Exception:
            pass
    return None

def _op_fam_table(family_op):
    if family_op is None:
        return None
    try:
        table_op = family_op.op(OP_FAM_TABLE_NAME)
        if table_op is not None:
            return table_op
    except Exception:
        pass
    try:
        found = family_op.findChildren(name=OP_FAM_TABLE_NAME, maxDepth=3)
        return found[0] if found else None
    except Exception:
        return None

def _custom_root(family_op):
    if family_op is None:
        return None
    for child_name in ('custom_operators', 'Custom_operators'):
        try:
            root_op = family_op.op(child_name)
            if root_op is not None:
                return root_op
        except Exception:
            pass
    try:
        found = family_op.findChildren(name='custom_operators', maxDepth=4)
        if found:
            return found[0]
    except Exception:
        pass
    try:
        found = family_op.findChildren(name='Custom_operators', maxDepth=4)
        return found[0] if found else None
    except Exception:
        return None

def _family_method(family_op, method_name):
    if family_op is None:
        return None

    for owner in (
        family_op,
        getattr(family_op, 'ComponentEXT', None),
        getattr(getattr(family_op, 'ext', None), 'ComponentEXT', None),
    ):
        try:
            method = getattr(owner, method_name, None) if owner is not None else None
            if callable(method):
                return method
        except Exception:
            pass
    return None

def _menu_var_table():
    for path in MENU_VAR_PATHS:
        table_op = _safe_op(path)
        if table_op is not None:
            return table_op
    return None

def _placement_parent():
    try:
        pane = ui.panes.current
        if pane is not None and getattr(pane, 'owner', None) is not None:
            return pane.owner
    except Exception:
        pass
    return None

def _placement_position():
    table_op = _menu_var_table()
    if table_op is not None:
        try:
            return (float(table_op['xpos', 1].val), float(table_op['ypos', 1].val))
        except Exception:
            pass
    return (0.0, 0.0)

def _clone_name(parent_comp, base_name):
    base_name = str(base_name).replace(' ', '_')
    index = 1
    while True:
        candidate = '{}{}'.format(base_name, index)
        try:
            if parent_comp.op(candidate) is None:
                return candidate
        except Exception:
            return candidate
        index += 1

def _hide_clone(clone):
    for attr_name, value in (('allowCooking', True), ('bypass', False), ('expose', False)):
        try:
            setattr(clone, attr_name, value)
        except Exception:
            pass

def _reveal_clone(clone):
    for attr_name, value in (('allowCooking', True), ('bypass', False), ('expose', True)):
        try:
            setattr(clone, attr_name, value)
        except Exception:
            pass
    try:
        clone.viewer = ui.preferences['network.viewer']
    except Exception:
        pass

def _schedule_finalize(clone, start_x, start_y):
    try:
        run(
            "op(args[0]).module._finalize_clone(args[1], args[2], args[3])",
            me.path,
            clone.path,
            float(start_x),
            float(start_y),
            delayFrames=2,
            delayRef=op.TDResources
        )
    except Exception:
        pass

def _finalize_clone(clone_path, start_x, start_y):
    clone = _safe_op(clone_path) if clone_path else None
    if clone is None:
        return False

    try:
        current_x = float(clone.nodeX)
        current_y = float(clone.nodeY)
    except Exception:
        current_x = start_x
        current_y = start_y

    if current_x == float(start_x) and current_y == float(start_y):
        _schedule_finalize(clone, start_x, start_y)
        return False

    _reveal_clone(clone)
    return True

def _try_native_place(clone):
    try:
        pane = ui.panes.current
    except Exception:
        return False
    if pane is None:
        return False

    candidates = (
        ('placeOPs', [clone]),
        ('placeOPs', clone),
        ('placeOP', clone),
        ('dropOPs', [clone]),
        ('dropOPs', clone),
        ('dropOP', clone),
    )
    for method_name, args in candidates:
        try:
            method = getattr(pane, method_name, None)
            if callable(method):
                method(args)
                return True
        except Exception:
            pass
    return False

def _apply_license(clone, family_op, master):
    try:
        license_op = family_op.op('License')
        if license_op is None or master.family != 'COMP':
            return
    except Exception:
        return

    try:
        existing = clone.op('License')
        if existing is not None:
            try:
                if existing.par.Bodytext.eval() == license_op.par.Bodytext.eval():
                    return
                existing.destroy()
            except Exception:
                pass
        clone.copy(license_op)
    except Exception:
        pass

def _place_fallback(family_op, master, display_name):
    target_parent = _placement_parent()
    if target_parent is None:
        return False

    try:
        clone = target_parent.copy(master, name=_clone_name(target_parent, display_name))
    except Exception:
        return False

    _apply_license(clone, family_op, master)
    _hide_clone(clone)

    start_x, start_y = PLACEMENT_SENTINEL
    try:
        clone.nodeX = start_x
        clone.nodeY = start_y
    except Exception:
        pass

    if _try_native_place(clone):
        _schedule_finalize(clone, start_x, start_y)
        return True

    _reveal_clone(clone)
    x, y = _placement_position()
    try:
        clone.nodeX = x
        clone.nodeY = y
    except Exception:
        pass
    return True

def _close_menu(op_create):
    try:
        run(
            "o = op(args[0]); o.par.winclose.pulse() if o is not None else None",
            op_create.path,
            delayFrames=1,
            delayRef=op.TDResources
        )
    except Exception:
        try:
            op_create.par.winclose.pulse()
        except Exception:
            pass

def _deferred_place(family_path, display_name, panel_value):
    family_op = _safe_op(family_path)
    if family_op is None:
        return False

    place_handler = _family_method(family_op, 'PlaceOp')
    if place_handler is not None:
        try:
            return bool(place_handler(panel_value, display_name))
        except Exception:
            return False

    custom_root = _custom_root(family_op)
    if custom_root is None:
        return False

    try:
        masters = custom_root.findChildren(name=display_name, maxDepth=1)
        master = masters[0] if masters else None
    except Exception:
        master = None
    if master is None:
        return False

    return _place_fallback(family_op, master, display_name)

def _schedule_place(family_op, display_name, panel_value):
    try:
        run(
            "op(args[0]).module._deferred_place(args[1], args[2], args[3])",
            me.path,
            family_op.path,
            str(display_name),
            int(panel_value),
            delayFrames=1,
            delayRef=op.TDResources
        )
        return True
    except Exception:
        return False

def _target_index(op_fam, nodetable, panel_value, search_string, op_create):
    rows_per_col = nodetable.par.tablerows.eval()

    group_starts = []
    group_sizes = []
    current_group = -1
    operator_count = 0
    for row_index in range(op_fam.numRows):
        if op_fam[row_index, 'type'].val.endswith('defLabel'):
            if current_group >= 0:
                group_sizes.append(operator_count)
            group_starts.append(row_index)
            current_group += 1
            operator_count = 0
        elif op_fam[row_index, 'name'].val:
            operator_count += 1
    group_sizes.append(operator_count)

    if search_string or panel_value == -934:
        destil = op_create.op('nodetable/destil')
        row_clicked = 1 if panel_value == -934 else panel_value
        if destil is not None and destil.numRows > row_clicked:
            selected_name = destil[row_clicked, 0].val
            matches = [i for i in range(op_fam.numRows) if op_fam[i, 'name'].val == selected_name]
            return matches[0] if matches else -1
        return -1

    columns_per_group = [2 if size == rows_per_col else (size + rows_per_col - 1) // rows_per_col for size in group_sizes]
    col_number = panel_value // rows_per_col
    cols_counted = 0
    actual_group = 0
    for group_index, cols in enumerate(columns_per_group):
        if col_number < cols_counted + cols:
            actual_group = group_index
            break
        cols_counted += cols

    cols_into_group = col_number - cols_counted
    pos_in_group = (panel_value % rows_per_col) - 1 if cols_into_group == 0 else (rows_per_col - 1) + (panel_value % rows_per_col)
    if pos_in_group < group_sizes[actual_group]:
        return group_starts[actual_group] + 1 + pos_in_group
    return -1

def onValueChange(panelValue, prev):
    if panelValue == -1:
        return

    current_family = _active_family_name()
    family_op = _family_op(current_family)
    op_fam = _op_fam_table(family_op)
    op_create = parent.OPCREATE
    nodetable = op_create.op('nodetable') if op_create is not None else None
    if family_op is None or op_fam is None or nodetable is None:
        return

    try:
        search_string = op_create.op('search/string').text
    except Exception:
        search_string = ''

    target_index = _target_index(op_fam, nodetable, panelValue, search_string, op_create)
    if target_index < 0 or target_index >= op_fam.numRows:
        return

    display_name = op_fam[target_index, 'name'].val
    if not display_name:
        return

    _close_menu(op_create)
    if not _schedule_place(family_op, display_name, panelValue):
        _deferred_place(family_op.path, display_name, panelValue)
