def onSelect(info):
    item = str(info.get('item', '') or '').strip()

    if item == 'Edit':
        try:
            parent(2).par.Edit.pulse()
            return
        except Exception:
            debug('[popMenu] pulse failed: Edit')

    if item == 'View':
        try:
            parent(2).par.View.pulse()
            return
        except Exception:
            debug('[popMenu] pulse failed: View')

    if item == 'Release notes':
        try:
            menu = info.get('menu', None)
        except Exception:
            menu = None
        if menu is None or not hasattr(menu, 'OpenSubMenu'):
            return

        try:
            menu.OpenSubMenu()
        except Exception as e:
            debug(f'[popMenu] OpenSubMenu failed: {e}')
        return
    
    action_map = {
        'Edit':                  'Edit_Releasenotes',
        'View':                  'View_Releasenotes',
        'Rename':                'Rename',
        'Duplicate':             'Duplicate',
        'Change color':          'Changecolor',
        'Edit operators':        'Editoperators',
        'Go to family':          'Gotofamily',
        'Update':                'Update',
        'Export family':         'Exportfamily',
        'Delete':                'Delete',
    }
    
    par_name = action_map.get(item)
    if par_name:
        par_names = [par_name]
        if par_name == 'Update':
            par_names.append('Manualupdate')
        if par_name == 'Editoperators':
            par_names.append('Editcustomoperators')

        targets = []
        for depth in (2, 3):
            try:
                target = parent(depth)
            except Exception:
                target = None
            if target is not None and target not in targets:
                targets.append(target)

        for target in targets:
            for candidate_name in par_names:
                try:
                    par = getattr(target.par, candidate_name, None)
                except Exception:
                    par = None
                if par is not None:
                    par.pulse()
                    return

        debug(f'[popMenu] Parametro non trovato: {par_names}')
    else:
        debug(f'[popMenu] Voce non mappata: {item}')


def onRollover(info):
    item = str(info.get('item', '') or '').strip()
    if item != 'Release notes':
        return

    try:
        menu = info.get('menu', None)
    except Exception:
        menu = None
    if menu is None or not hasattr(menu, 'OnSelect'):
        return

    try:
        cell = int(info.get('index', -1))
    except Exception:
        cell = -1
    if cell < 0:
        return

    try:
        menu.OnSelect(cell, doautoClose=False)
    except Exception as e:
        debug(f'[popMenu] OnSelect rollover failed: {e}')

def onOpen(info):
    pass

def onClose(info):
    pass

def onMouseDown(info):
    pass

def onMouseUp(info):
    pass

def onClick(info):
    pass

def onLostFocus(info):
    pass
