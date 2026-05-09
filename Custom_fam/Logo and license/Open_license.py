from typing import List

def _changed_values(dat: DAT, info: ChangedDATInfo) -> List[str]:
	values = []
	try:
		cells = list(getattr(info, 'cells', []) or [])
	except Exception:
		cells = []
	for cell in cells:
		try:
			values.append(str(cell.val).strip())
		except Exception:
			pass
	if values:
		return values
	try:
		max_rows = min(getattr(dat, 'numRows', 0), 4)
		max_cols = min(getattr(dat, 'numCols', 0), 4)
		for row in range(max_rows):
			for col in range(max_cols):
				try:
					values.append(str(dat[row, col].val).strip())
				except Exception:
					pass
	except Exception:
		pass
	return values

def onTableChange(dat: DAT, prevDAT: DAT, info: ChangedDATInfo):
	if '1' not in _changed_values(dat, info):
		return
	op_license = op('license')
	if op_license is not None:
		op_license.openViewer()
	return
