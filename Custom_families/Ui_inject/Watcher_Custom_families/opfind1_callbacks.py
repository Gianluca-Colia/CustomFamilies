"""
Op Find DAT Callbacks

me - this DAT
dat - the DAT that is querying
curOp - the OP being queried
row - the table row index
"""

from typing import Any, Dict


def onFindOPGetInclude(dat: opfindDAT, curOp: OP, row: int) -> bool:
	return True


def onOPFound(dat: opfindDAT, curOp: OP, row: int, results: Dict[str, Any]):
	return
