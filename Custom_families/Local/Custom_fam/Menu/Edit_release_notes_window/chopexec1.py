"""
CHOP Execute DAT

me - this DAT

Make sure the corresponding toggle is enabled in the CHOP Execute DAT.
"""

def onOffToOn(channel: Channel, sampleIndex: int, val: float, prev: float):
	
	# Definiamo la finestra di dialogo 
	Edit_window = parent()
	
	# Definiamo La tabella dove salviamo Versione, Build e Descrizione
	Storage = parent(2).op('Version_Build_Description')
	
	# print(channel.name)
	
	if channel.name == 'Update':
		
		# aggiorniamo le righe della tabella prendendo le dati dai parametri Custom della finetra
		Storage[0,0] = Edit_window.par.Windowversion
		Storage[1,0] = Edit_window.par.Windowbuild
		Storage[2,0] = Edit_window.par.Windowdescription
		
		# Definiamo la Family
		Family = parent(3)
		
		# Chiamiamo la funzione della family per aggiornare la pagina about di tutti i suoi operatori
		Family.RebuildAboutOnAllComps()
		
		
	elif channel.name == 'winopen':
		
		# riallineamo i parametri/testi della finestra di dialogo quando la finestra viene aperta
		Edit_window.par.Windowversion = Storage[0,0]
		Edit_window.par.Windowbuild = Storage[1,0]
		Edit_window.par.Windowdescription = Storage[2,0]
		
	return

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
