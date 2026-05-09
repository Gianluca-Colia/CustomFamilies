"""
CHOP Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the CHOP Execute DAT.
"""

def onOffToOn(channel: Channel, sampleIndex: int, val: float, 
			  prev: float):
	"""
	Called when a channel changes from 0 to non-zero.
	
	Args:
		channel: The Channel object which has changed
		sampleIndex: The index of the changed sample
		val: The numeric value of the changed sample
		prev: The previous sample value
	"""
	def _get_family_comp():
		try:
			return parent(2)
		except Exception:
			return None

	def _get_active_network_pane():
		try:
			pane = ui.panes.current
			if pane is not None and getattr(pane, 'type', None) == PaneType.NETWORKEDITOR:
				return pane
		except Exception:
			pass

		try:
			for pane in ui.panes:
				if getattr(pane, 'type', None) == PaneType.NETWORKEDITOR:
					return pane
		except Exception:
			pass
		return None

	def _set_pane_owner(pane, owner_comp):
		if pane is None or owner_comp is None:
			return False
		try:
			pane.owner = owner_comp
			return True
		except Exception:
			return False

	def _stored_family_pane():
		try:
			pane_id = me.fetch('cf_gotofamily_left_pane_id', None)
		except Exception:
			pane_id = None
		if pane_id is None:
			return None

		candidate = None
		try:
			for pane in ui.panes:
				if getattr(pane, 'id', None) == pane_id:
					candidate = pane
					break
		except Exception:
			candidate = None

		if candidate is None:
			return None

		try:
			if getattr(candidate, 'type', None) != PaneType.NETWORKEDITOR:
				return None
		except Exception:
			return None
		return candidate

	def _store_family_pane(pane):
		if pane is None:
			return
		try:
			me.unstore('cf_gotofamily_left_pane')
			me.store('cf_gotofamily_left_pane_id', pane.id)
		except Exception:
			pass

	def _home_to_family(target_pane, family_comp):
		if target_pane is None or family_comp is None:
			return False

		try:
			for child in getattr(family_comp.parent(), 'children', []):
				try:
					child.selected = False
				except Exception:
					pass
		except Exception:
			pass

		try:
			family_comp.selected = True
		except Exception:
			pass

		try:
			family_comp.current = True
		except Exception:
			pass

		for method_name in ('homeSelected', 'homeSel', 'homeTo'):
			try:
				method = getattr(target_pane, method_name, None)
			except Exception:
				method = None
			if not callable(method):
				continue
			for args in ((), (family_comp,), ([family_comp],)):
				try:
					method(*args)
					return True
				except Exception:
					pass

		return None

	def _focus_family_in_parent(family_comp):
		if family_comp is None:
			return False

		try:
			family_parent = family_comp.parent()
		except Exception:
			family_parent = None

		if family_parent is None:
			return False

		active_pane = _get_active_network_pane()
		if active_pane is None:
			return False

		target_pane = _stored_family_pane()
		if target_pane is not None:
			if _set_pane_owner(target_pane, family_parent):
				_home_to_family(target_pane, family_comp)
				return True

		target_pane = active_pane
		right_pane = None
		try:
			try:
				original_owner = active_pane.owner
			except Exception:
				original_owner = None

			right_pane = active_pane.splitRight()
		except Exception:
			return False

		if not _set_pane_owner(target_pane, family_parent):
			return False

		if right_pane is not None and original_owner is not None:
			_set_pane_owner(right_pane, original_owner)

		_store_family_pane(target_pane)
		_home_to_family(target_pane, family_comp)
		return True

	return _focus_family_in_parent(_get_family_comp())

def whileOn(channel: Channel, sampleIndex: int, val: float, 
			prev: float):
	"""
	Called every frame while a channel is non-zero.
	
	Args:
		channel: The Channel object which has changed
		sampleIndex: The index of the changed sample
		val: The numeric value of the changed sample
		prev: The previous sample value
	"""
	return

def onOnToOff(channel: Channel, sampleIndex: int, val: float, 
			  prev: float):
	"""
	Called when a channel changes from non-zero to 0.
	
	Args:
		channel: The Channel object which has changed
		sampleIndex: The index of the changed sample
		val: The numeric value of the changed sample
		prev: The previous sample value
	"""
	return

def whileOff(channel: Channel, sampleIndex: int, val: float, 
			 prev: float):
	"""
	Called every frame while a channel is 0.
	
	Args:
		channel: The Channel object which has changed
		sampleIndex: The index of the changed sample
		val: The numeric value of the changed sample
		prev: The previous sample value
	"""
	return

def onValueChange(channel: Channel, sampleIndex: int, val: float, 
				  prev: float):
	"""
	Called when a channel value changes.
	
	Args:
		channel: The Channel object which has changed
		sampleIndex: The index of the changed sample
		val: The numeric value of the changed sample
		prev: The previous sample value
	"""
	return
