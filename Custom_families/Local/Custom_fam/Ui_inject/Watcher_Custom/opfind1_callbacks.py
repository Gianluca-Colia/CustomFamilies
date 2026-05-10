"""
Op Find DAT Callbacks — opfind1 (Watcher_Custom)

Monitors operators inside the family's Ui_inject component whose name matches
the pattern '*FamilyName'.  The component parameter is bound at install time to
op('FamilyName').op('Ui_inject'), so the search is always scoped to the correct
family component.

me   - this DAT
dat  - the DAT that is querying
curOp - the OP being queried
row  - the table row index
"""

from typing import Any, Dict, List


def onFindOPGetInclude(dat, curOp: 'OP', row: int) -> bool:
	"""
	Include only operators that are direct children of the search root
	(Ui_inject) and are not the Watcher itself.  This avoids picking up
	deeply-nested helpers or the source template accidentally.
	"""
	try:
		search_root = dat.par.component.eval()
		if search_root is None:
			return True
		# Only include direct children of the search root
		if curOp.parent() != search_root:
			return False
		# Exclude the watcher comp itself (lives in bookmark_bar, not here,
		# but guard just in case)
		if curOp is dat.parent():
			return False
	except Exception:
		pass
	return True


def onOPFound(dat, curOp: 'OP', row: int, results: Dict[str, Any]) -> None:
	"""
	Called for every operator included by onFindOPGetInclude.
	Stores the operator path on the ownerComp so other scripts can query
	what family operators are currently installed without an additional search.

	The accumulated list is stored under the key 'watcher_found_ops' and is
	reset at the start of each cook cycle by onInitGetColumnNames if needed.
	Currently used read-only by external scripts via:
	    op('watcher_FamilyName').fetch('found_ops', [])
	"""
	try:
		owner = dat.parent()
		found = owner.fetch('found_ops', [])
		path = curOp.path
		if path not in found:
			found.append(path)
		owner.store('found_ops', found)
	except Exception:
		pass
