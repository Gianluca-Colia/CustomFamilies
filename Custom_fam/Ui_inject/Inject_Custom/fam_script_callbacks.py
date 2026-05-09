# me - questo DAT
# scriptOp - l'OP che sta cuocendo

DEFAULT_FAMILY_NAME = 'Custom'
SOURCE_OPERATOR_PATH = '/project1/Custom'
CUSTOM_OPERATORS_PATH = '../Custom_operators'
CURRENT_TABLE_PATH = '/ui/dialogs/menu_op/current'
SEARCH_STRING_PATH = '/ui/dialogs/menu_op/search/string'
OP_FAM_TABLE_NAME = 'OP_fam'

TABLE_HEADER = [
    'name', 'label', 'type', 'subtype', 'mininputs', 'maxinputs',
    'ordering', 'level', 'lictype', 'os', 'score', 'family', 'opType'
]


def _safe_op(path):
    try:
        return op(path)
    except Exception:
        return None


def _family_name_from_context():
    """Derive family name from the inject COMP name (always inject_<FamilyName>)."""
    for depth in range(1, 4):
        try:
            p = parent(depth)
            if p is None:
                continue
            pname = str(p.name)
            if pname.startswith('inject_'):
                return pname[len('inject_'):]
        except Exception:
            continue
    return None


def _source_operator():
    # Priority 1: derive from inject COMP name in the hierarchy.
    # Reliable even after file reload because it reads from the actual network context.
    fam = _family_name_from_context()
    if fam:
        for candidate in (
            getattr(op, fam, None),
            _safe_op('/project1/{}'.format(fam)),
            _safe_op(fam),
        ):
            if candidate is None:
                continue
            try:
                if candidate.op('InstallerEXT') is not None or candidate.op('ComponentEXT') is not None:
                    return candidate
            except Exception:
                pass

    # Priority 2: walk parents directly (works when script runs inside the family COMP).
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

    # Priority 3: configured/hardcoded fallbacks.
    for candidate in (
        getattr(op, str(SOURCE_OPERATOR_PATH).strip(), None) if SOURCE_OPERATOR_PATH else None,
        _safe_op(SOURCE_OPERATOR_PATH) if SOURCE_OPERATOR_PATH else None,
        getattr(op, DEFAULT_FAMILY_NAME, None),
        _safe_op('/{}'.format(DEFAULT_FAMILY_NAME)),
        _safe_op(DEFAULT_FAMILY_NAME),
    ):
        if candidate is not None:
            return candidate
    return None


def _family_name():
    source_op = _source_operator()
    if source_op is not None:
        try:
            value = str(source_op.par.opshortcut.eval()).strip()
            if value:
                return value
        except Exception:
            pass

    try:
        parent_op = parent(2)
        if hasattr(parent_op.par, 'opshortcut'):
            value = str(parent_op.par.opshortcut.eval()).strip()
            if value:
                return value
    except Exception:
        pass
    return DEFAULT_FAMILY_NAME


def _current_family():
    current_table = _safe_op(CURRENT_TABLE_PATH)
    if current_table is None:
        return ''
    try:
        return str(current_table[0, 0].val).strip()
    except Exception:
        return ''


def _op_fam_table():
    source_op = _source_operator()
    if source_op is None:
        return None

    try:
        table_op = source_op.op(OP_FAM_TABLE_NAME)
        if table_op is not None:
            return table_op
    except Exception:
        pass

    try:
        found = source_op.findChildren(name=OP_FAM_TABLE_NAME, maxDepth=3)
        return found[0] if found else None
    except Exception:
        return None


def _copy_header(scriptOp):
    scriptOp.clear()
    scriptOp.appendRow(TABLE_HEADER)


def _copy_input_or_header(scriptOp):
    if len(scriptOp.inputs) > 0 and scriptOp.inputs[0] is not None:
        try:
            scriptOp.copy(scriptOp.inputs[0])
            return
        except Exception:
            pass
    _copy_header(scriptOp)


def _copy_table(scriptOp, table_op):
    if table_op is None:
        _copy_header(scriptOp)
        return False
    try:
        scriptOp.copy(table_op)
        return True
    except Exception:
        _copy_header(scriptOp)
        return False


def _input_family(scriptOp):
    if len(scriptOp.inputs) == 0 or scriptOp.inputs[0] is None:
        return ''

    input_table = scriptOp.inputs[0]
    for row_index, col_index in ((0, 0), (1, 0), (0, 1), (1, 1)):
        try:
            value = str(input_table[row_index, col_index].val).strip()
            if value and value.lower() != 'name':
                return value
        except Exception:
            pass
    return ''


def _search_string(scriptOp):
    try:
        value = str(scriptOp.par.Search.eval()).strip()
        if value:
            return value
    except Exception:
        pass

    search_op = _safe_op(SEARCH_STRING_PATH)
    try:
        return str(search_op.text).strip() if search_op is not None else ''
    except Exception:
        return ''


def _row_values(table_op, row_index):
    values = []
    for col_index in range(table_op.numCols):
        try:
            values.append(str(table_op[row_index, col_index].val))
        except Exception:
            values.append('')
    return values


def _row_matches(table_op, row_index, query):
    if not query:
        return True
    for column_name in ('name', 'label'):
        try:
            value = str(table_op[row_index, column_name].val).strip().lower()
        except Exception:
            value = ''
        if value.startswith(query):
            return True
    return False


def _copy_filtered_op_fam(scriptOp, table_op, query):
    if table_op is None:
        _copy_header(scriptOp)
        return False

    query = str(query).strip().lower()
    if not query:
        return _copy_table(scriptOp, table_op)

    rows = [_row_values(table_op, 0)]
    group_row = None
    group_added = False
    match_count = 0

    for row_index in range(1, table_op.numRows):
        try:
            row_type = str(table_op[row_index, 'type'].val)
        except Exception:
            row_type = ''

        if row_type.endswith('defLabel'):
            group_row = _row_values(table_op, row_index)
            group_added = False
            continue

        if not _row_matches(table_op, row_index, query):
            continue

        if group_row is not None and not group_added:
            rows.append(group_row)
            group_added = True

        rows.append(_row_values(table_op, row_index))
        match_count += 1

    scriptOp.clear()
    for row in rows:
        scriptOp.appendRow(row)
    return match_count > 0


def _dat_stamp(dat):
    if dat is None:
        return ('', 0, 0, '', '')

    rows = 0
    cols = 0
    first_name = ''
    last_name = ''

    try:
        rows = int(dat.numRows)
    except Exception:
        rows = 0
    try:
        cols = int(dat.numCols)
    except Exception:
        cols = 0

    try:
        if rows > 1:
            first_name = str(dat[1, 'name'].val)
            last_name = str(dat[rows - 1, 'name'].val)
    except Exception:
        first_name = ''
        last_name = ''

    try:
        path = str(dat.path)
    except Exception:
        path = ''

    return (path, rows, cols, first_name, last_name)


def _state_key(scriptOp, current_family, family_name, search_string, op_fam):
    active = (current_family == family_name)
    source_stamp = _dat_stamp(op_fam if active else (scriptOp.inputs[0] if len(scriptOp.inputs) > 0 else None))
    return (active, current_family, family_name, str(search_string or ''), source_stamp)


def _same_state(scriptOp, state_key):
    try:
        return scriptOp.fetch('cf_last_state', None) == state_key
    except Exception:
        return False


def _store_state(scriptOp, state_key):
    try:
        scriptOp.store('cf_last_state', state_key)
    except Exception:
        pass


def setupParameters(scriptOp):
    page = scriptOp.appendCustomPage('Operators')
    for append_name, label, fn in (
        ('Rows', 'Rows', page.appendInt),
        ('Append', 'Append Nodes', page.appendToggle),
        ('Compatible', 'Compatible OPs', page.appendStr),
        ('Search', 'Search String', page.appendStr),
        ('Source', 'Source', page.appendStr),
        ('Connectto', 'Connect To', page.appendStr),
        ('All', 'Display All', page.appendToggle),
        ('Experimental', 'Display Experimental', page.appendToggle),
        ('Limitcustom', 'Limit Custom', page.appendStr),
    ):
        fn(append_name, label=label)


def onPulse(par):
    return


def cook(scriptOp):
    current_family = _current_family() or _input_family(scriptOp)
    family_name = _family_name()
    op_fam = _op_fam_table()
    search_string = _search_string(scriptOp)
    state_key = _state_key(scriptOp, current_family, family_name, search_string, op_fam)

    if _same_state(scriptOp, state_key):
        return

    if current_family == family_name:
        if search_string and not _copy_filtered_op_fam(scriptOp, op_fam, search_string):
            _copy_input_or_header(scriptOp)
            _store_state(scriptOp, state_key)
            return

        if search_string:
            _copy_filtered_op_fam(scriptOp, op_fam, search_string)
        else:
            _copy_table(scriptOp, op_fam)
        _store_state(scriptOp, state_key)
        return

    _copy_input_or_header(scriptOp)
    _store_state(scriptOp, state_key)
