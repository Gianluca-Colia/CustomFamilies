"""
OP Execute bridge for family rename detection.

Responsibility:
- observe the family component name change
- call RenameEXT with previous and new family names
- keep a small local baseline to avoid false positives and loops
"""

import re


LAST_NAME_KEY = 'cf_last_family_name'
RENAME_GUARD_KEY = 'cf_rename_exec_guard'


def _safe_store(owner, key, value):
	try:
		owner.store(key, value)
		return True
	except Exception:
		return False


def _safe_fetch(owner, key, default=''):
	try:
		return owner.fetch(key, default)
	except Exception:
		return default


def _sanitize_name(name):
	name = '' if name is None else str(name).strip().replace(' ', '')
	name = re.sub(r'[^A-Za-z0-9_]', '', name)
	return '_' + name if name and name[0].isdigit() else name


def _get_target():
	try:
		return parent(2)
	except Exception:
		return None


def _get_observed_name(target):
	if target is None:
		return ''

	try:
		value = str(target.name).strip()
		if value:
			return _sanitize_name(value)
	except Exception:
		pass

	return ''


def _remember_name(target, name=None):
	target_name = _sanitize_name(name) if name is not None else _get_observed_name(target)
	if not target_name:
		return ''
	_safe_store(me, LAST_NAME_KEY, target_name)
	return target_name


def _rename_guard_enabled():
	return bool(_safe_fetch(me, RENAME_GUARD_KEY, False))


def _set_rename_guard(state):
	_safe_store(me, RENAME_GUARD_KEY, bool(state))


def _get_rename_ext(target):
	if target is None:
		return None

	for attr_name in ('RenameEXT', 'Rename', 'GenericRenameEXT'):
		try:
			ext_obj = getattr(target, attr_name, None)
			if ext_obj is not None and hasattr(ext_obj, 'HandleObservedNameChange'):
				return ext_obj
		except Exception:
			pass

	try:
		ext_ns = getattr(target, 'ext', None)
	except Exception:
		ext_ns = None

	if ext_ns is not None:
		for attr_name in ('RenameEXT', 'Rename', 'GenericRenameEXT'):
			try:
				ext_obj = getattr(ext_ns, attr_name, None)
				if ext_obj is not None and hasattr(ext_obj, 'HandleObservedNameChange'):
					return ext_obj
			except Exception:
				pass

	for dat_name in ('RenameEXT', 'renameext'):
		try:
			dat_op = target.op(dat_name)
			if dat_op is None:
				continue

			module = dat_op.module
			cls = getattr(module, 'GenericRenameEXT', None) or getattr(module, 'RenameEXT', None)
			if cls is None:
				continue

			return cls(target, auto_init=False, enable_runtime_hooks=False)
		except Exception:
			pass

	return None


def onNameChange(changeOp: OP):
	target = _get_target()
	if target is None or changeOp is None:
		return False

	try:
		if changeOp.path != target.path:
			return False
	except Exception:
		return False

	new_name = _get_observed_name(target)
	previous_name = _sanitize_name(_safe_fetch(me, LAST_NAME_KEY, ''))

	if not previous_name:
		_remember_name(target, new_name)
		return False

	if not new_name or new_name == previous_name:
		_remember_name(target, new_name)
		return False

	if _rename_guard_enabled():
		_remember_name(target, new_name)
		return False

	rename_ext = _get_rename_ext(target)
	if rename_ext is None:
		_remember_name(target, new_name)
		debug("Rename_op_exec: RenameEXT not found for '{}'".format(target.path))
		return False

	_set_rename_guard(True)
	try:
		result = bool(rename_ext.HandleObservedNameChange(previous_name, new_name, show_message=False))
	finally:
		_set_rename_guard(False)
		_remember_name(target, _get_observed_name(target))

	return result


def onPathChange(changeOp: OP):
	return False


_remember_name(_get_target())
