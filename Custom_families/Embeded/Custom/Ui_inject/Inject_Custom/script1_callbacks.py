# me - this DAT
# scriptOp - the OP which is cooking
#
# press 'Setup Parameters' in the OP to call this function to re-create the parameters.

import re


def setupParameters(scriptOp):
	page = scriptOp.appendCustomPage('Operators')
	page.appendInt('Rows', label='Rows')
	page.appendToggle('Append', label='Append Nodes')
	page.appendStr('Compatible', label='Compatible OPs')
	page.appendStr('Search', label='Search String')
	page.appendStr('Source', label='Source')
	page.appendStr('Connectto', label='Connect To')
	page.appendToggle('All', label='Display All')
	page.appendToggle('Experimental', label='Display Experimental')
	page.appendStr('Limitcustom', label='Limit Custom')
	return


def onPulse(par):
	return


def _header():
	return ['name', 'label', 'type', 'subtype', 'mininputs', 'maxinputs', 'ordering', 'level', 'lictype', 'os', 'score', 'family', 'opType']


def _copy_input_or_header(scriptOp):
	scriptOp.clear()
	if len(scriptOp.inputs) > 0 and scriptOp.inputs[0] is not None:
		try:
			scriptOp.copy(scriptOp.inputs[0])
			return True
		except Exception:
			pass
	scriptOp.appendRow(_header())
	return False


def _input_is_operator_table(scriptOp):
	if len(scriptOp.inputs) == 0 or scriptOp.inputs[0] is None:
		return False
	input_table = scriptOp.inputs[0]
	try:
		return getattr(input_table, 'numRows', 0) > 0 and getattr(input_table, 'numCols', 0) > 0 and str(input_table[0, 0].val).strip().lower() == 'name'
	except Exception:
		return False


def _read_current_family(scriptOp):
	try:
		current = op('/ui/dialogs/menu_op/current')
		if current is not None:
			value = str(current[0, 0].val).strip()
			if value and value.lower() != 'name':
				return value
	except Exception:
		pass

	if len(scriptOp.inputs) > 0 and scriptOp.inputs[0] is not None:
		try:
			value = str(scriptOp.inputs[0][0, 0].val).strip()
			if value and value.lower() != 'name':
				return value
		except Exception:
			pass
	return ''


def _custom_families(scriptOp):
	names = []
	try:
		node_table = parent(2)
	except Exception:
		node_table = None
	if node_table is None:
		return names
	try:
		for child in getattr(node_table, 'children', []):
			try:
				if child.isCOMP and str(child.name).startswith('inject_'):
					name = str(child.name).partition('_')[2].strip()
					if name and name not in names:
						names.append(name)
			except Exception:
				pass
	except Exception:
		pass
	return names


def cook(scriptOp):
	if _input_is_operator_table(scriptOp):
		_copy_input_or_header(scriptOp)
		return

	currFamily = _read_current_family(scriptOp)
	if not currFamily:
		_copy_input_or_header(scriptOp)
		return

	if currFamily in _custom_families(scriptOp):
		_copy_input_or_header(scriptOp)
		return

	try:
		if currFamily not in families.keys():
			_copy_input_or_header(scriptOp)
			return
	except Exception:
		_copy_input_or_header(scriptOp)
		return

	scriptOp.clear()
	scriptOp.appendRow(_header())

	tableRows = scriptOp.par.Rows
	append = scriptOp.par.Append
	searchString = scriptOp.par.Search.eval().lower().strip()
	source = scriptOp.par.Source.eval()
	connectTo = scriptOp.par.Connectto.eval()
	license = licences.type

	if not connectTo:
		connectTo = 'Bla'

	if not append:
		compatible = ['x']
	else:
		compatible = [i.split(':')[0] for i in scriptOp.par.Compatible.eval().split(' ')]

	allNodes = []
	allFamilies = [currFamily]

	for family in allFamilies:
		try:
			family_nodes = families[family]
		except Exception:
			continue
		for i in family_nodes:
			if 'x' in compatible or i.type in compatible:
				node = {}
				node['nodeName'] = i.type
				node['nodeLabel'] = i.label
				node['opType'] = i.OPType
				node['score'] = 0
				node['icon'] = i.icon

				if not len(searchString) or searchString in i.type.lower() or searchString in i.label.lower() or searchString in i.OPType.lower() or searchString in f"{i.type} {family.lower()}" or searchString in f"{i.label.lower()} {family.lower()}" or searchString in i.icon.lower():
					labelByCapital = re.findall('[A-Z][^A-Z]*', i.label)
					if i.label.lower() == searchString:
						node['score'] = 5
					elif i.icon.lower().startswith(searchString):
						node['score'] = 4.5
					elif i.OPType.lower().startswith(searchString):
						node['score'] = 4.5
					elif f"{i.type} {family.lower()}".startswith(searchString):
						node['score'] = 4.5
					elif f"{i.label.lower()} {family.lower()}".startswith(searchString):
						node['score'] = 4.5
					elif i.type.lower() == searchString:
						node['score'] = 4
					elif i.label.lower().startswith(searchString):
						node['score'] = 3
					elif searchString in i.label.lower().split(' '):
						node['score'] = 2
					elif any(s.startswith(searchString) for s in i.label.lower().split(' ')):
						node['score'] = 2
					elif any(s.lower().startswith(searchString) for s in labelByCapital):
						node['score'] = 2
					if node['score'] > 0:
						opType = ['defGenerator', 'defFilter'][i.isFilter]
					else:
						opType = ['defGeneratorDisable', 'defFilterDisable'][i.isFilter]
				else:
					opType = ['defGeneratorDisable', 'defFilterDisable'][i.isFilter]
				if i.supported == 0:
					opType = ['defGeneratorDisable', 'defFilterDisable'][i.isFilter]
				elif source == 'output' and not i.isFilter and i.maxInputs == 0 and currFamily == connectTo:
					opType = ['defGeneratorDisable', 'defFilterDisable'][i.isFilter]
				if i.licenseType == 'Pro' and 'Pro' not in license:
					opType = ['defGeneratorDisable', 'defFilterDisable'][i.isFilter]
				elif i.licenseType == 'Commercial' and 'Non-Commercial' in license:
					opType = ['defGeneratorDisable', 'defFilterDisable'][i.isFilter]

				node['isFilter'] = 'layouts/{0}/{1}'.format(family, opType)
				node['subType'] = getSubType(i.subType)
				node['minInputs'] = i.minInputs
				node['maxInputs'] = i.maxInputs
				node['visibility'] = i.visibleLevel
				node['ordered'] = i.isMultiInputs
				node['supported'] = i.supported
				node['licLevel'] = i.licenseType
				node['custom'] = i.isCustom
				node['family'] = family
				if scriptOp.par.Experimental.eval():
					allNodes.append(node)
				elif i.visibleLevel < 2 and scriptOp.par.All.eval():
					allNodes.append(node)
				elif i.visibleLevel < 1 and not scriptOp.par.All.eval():
					allNodes.append(node)

	if currFamily == 'COMP':
		heading = [['', '3D Objects', 'layouts/COMP/defLabel'], ['', 'Panels', 'layouts/COMP/defLabel'], ['', 'Other', 'layouts/COMP/defLabel'], ['', 'Dynamics', 'layouts/COMP/defLabel']]
		sortedList = sorted(allNodes, key=lambda k: k['subType'])
		count = 0
		currSubType = -1

		for i in sortedList:
			if i['subType'] != currSubType:
				if count > 0:
					addRows = tableRows - (count % tableRows)
					for _ in range(addRows):
						scriptOp.appendRow()

				currSubType = i['subType']
				scriptOp.appendRow(heading[currSubType])
				count = 1
			scriptOp.appendRow([i['nodeName'], i['nodeLabel'], i['isFilter'], i['subType'], i['minInputs'], i['maxInputs'], i['ordered'], i['visibility'], i['licLevel'], i['supported'], i['score'], i['family'], i['opType']])
			count += 1
		addRows = tableRows - (count % tableRows)

	elif currFamily == 'Custom':
		sortedList = sorted(allNodes, key=lambda k: k['nodeLabel'].lower())
		for i in sortedList:
			if i['custom']:
				scriptOp.appendRow([i['nodeName'], i['nodeLabel'], i['isFilter'], i['subType'], i['minInputs'], i['maxInputs'], i['ordered'], i['visibility'], i['licLevel'], i['supported'], i['score'], i['family'], i['opType']])
		addRows = tableRows - (len(sortedList) % tableRows)

	else:
		sortedList = sorted(allNodes, key=lambda k: k['nodeLabel'].lower())
		for i in sortedList:
			if not i['custom']:
				scriptOp.appendRow([i['nodeName'], i['nodeLabel'], i['isFilter'], i['subType'], i['minInputs'], i['maxInputs'], i['ordered'], i['visibility'], i['licLevel'], i['supported'], i['score'], i['family'], i['opType']])
		addRows = tableRows - (len(sortedList) % tableRows)

	for _ in range(addRows):
		scriptOp.appendRow()

	return


def getSubType(subType):
	if subType == 'object':
		return 0
	elif subType == 'panel':
		return 1
	elif subType == 'dynamics':
		return 3
	else:
		return 2
