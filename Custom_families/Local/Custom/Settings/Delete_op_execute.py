"""
Level-1 + Level-2 delete bridge.

onDestroy() sequence:
  1. Directly destroy button_{family_name} in bookmark_bar          (Level 1)
  2. Call UninstallerEXT.RemoveFamily() for full UI cleanup          (Level 2)

Level 3 (watcher opexec1.py) handles any residue that survives both.
"""
import re


def _safe_op(path):
    try:
        return op(path)
    except Exception:
        return None


def _sanitize_name(name):
    name = '' if name is None else str(name).strip().replace(' ', '')
    name = re.sub(r'[^A-Za-z0-9_]', '', name)
    return '_' + name if name and name[0].isdigit() else name


def _get_stored_family_name():
    """Read family_name from the delete_execute DAT's own stored data."""
    try:
        stored = me.fetch('delete_family_name', '')
        if stored:
            return _sanitize_name(stored)
    except Exception:
        pass
    return ''


def _destroy_button_direct(family_name):
    """Level 1: brute-force destroy every button variant in bookmark_bar."""
    if not family_name:
        return 0
    bookmark_bar = _safe_op('/ui/panes/panebar/pane1/Local_bar')
    if bookmark_bar is None:
        return 0
    removed = 0
    seen = set()
    for btn_name in (
        'button_{}'.format(family_name),
        '{}_toggle'.format(family_name),
        '{}_button'.format(family_name),
        family_name,
    ):
        try:
            target = bookmark_bar.op(btn_name)
        except Exception:
            target = None
        if target is None:
            continue
        try:
            path = target.path
        except Exception:
            path = None
        if path in seen:
            continue
        if path:
            seen.add(path)
        try:
            target.allowCooking = False
        except Exception:
            pass
        try:
            target.destroy()
            removed += 1
        except Exception:
            pass

    # Scan pass: catch any remnant the name lookup missed
    try:
        children = bookmark_bar.findChildren(depth=None, maxDepth=1)
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
        if (
            name == 'button_{}'.format(family_name)
            or name == '{}_toggle'.format(family_name)
            or name == '{}_button'.format(family_name)
            or name == family_name
        ):
            seen.add(path)
            try:
                child.allowCooking = False
            except Exception:
                pass
            try:
                child.destroy()
                removed += 1
            except Exception:
                pass

    return removed


def _get_target():
    # 1) target from DAT Execute parameter
    for par_name in ('ops', 'fromop', 'op'):
        try:
            par = getattr(me.par, par_name, None)
        except Exception:
            par = None
        if par is None:
            continue
        try:
            target = par.eval()
            if target is not None:
                return target
        except Exception:
            pass
        try:
            raw_path = str(par.eval()).strip()
        except Exception:
            raw_path = ''
        if raw_path:
            target = _safe_op(raw_path)
            if target is not None:
                return target

    # 2) stored path
    try:
        stored_path = str(me.fetch('delete_target_path', '')).strip()
        if stored_path:
            target = _safe_op(stored_path)
            if target is not None:
                return target
    except Exception:
        pass

    # 3) walk parents
    current = parent()
    depth = 0
    while current is not None and depth < 6:
        try:
            if hasattr(current, 'par') and hasattr(current.par, 'Install'):
                return current
        except Exception:
            pass
        try:
            current = current.parent()
        except Exception:
            current = None
        depth += 1

    return None


def _get_uninstaller(target):
    if target is None:
        return None

    for attr_name in ('UninstallerEXT', 'Uninstaller', 'GenericUninstallerEXT'):
        try:
            ext_obj = getattr(target, attr_name, None)
            if ext_obj is not None and hasattr(ext_obj, 'RemoveFamily'):
                return ext_obj
        except Exception:
            pass

    try:
        ext_ns = getattr(target, 'ext', None)
    except Exception:
        ext_ns = None
    if ext_ns is not None:
        for attr_name in ('UninstallerEXT', 'Uninstaller', 'GenericUninstallerEXT'):
            try:
                ext_obj = getattr(ext_ns, attr_name, None)
                if ext_obj is not None and hasattr(ext_obj, 'RemoveFamily'):
                    return ext_obj
            except Exception:
                pass

    for dat_name in ('UninstallerEXT', 'uninstallerext'):
        try:
            dat_op = target.op(dat_name)
            if dat_op is None:
                continue
            module = dat_op.module
            cls = getattr(module, 'UninstallerEXT', None) or getattr(module, 'GenericUninstallerEXT', None)
            if cls is None:
                continue
            return cls(target, auto_init=False, enable_runtime_hooks=False)
        except Exception:
            pass

    return None


def onPreCook(changeOp):
    return


def onPostCook(changeOp):
    return


def onFlagChange(changeOp, flag, value):
    return


def onWireChange(changeOp):
    return


def onNameChange(changeOp):
    return


def onPathChange(changeOp):
    return


def onUIChange(changeOp):
    return


def onDestroy(changeOp=None):
    family_name = _get_stored_family_name()

    # Level 1: destroy button directly in bookmark_bar
    _destroy_button_direct(family_name)

    # Level 2: full UninstallerEXT cleanup (RemoveFamily, not RemoveInstalledUi)
    target = _get_target()
    uninstaller = _get_uninstaller(target)
    if uninstaller is not None:
        try:
            uninstaller.RemoveFamily(family_name=family_name or None)
        except Exception:
            pass

    return True
