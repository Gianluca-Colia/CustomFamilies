# Custom Families — Documentazione

Funzioni che puoi chiamare via Python (textport, callback, script) per
pilotare il plugin senza usare la UI.

In TouchDesigner ogni funzione vive su un'estensione di un COMP. Si
richiama così:

```python
op('Custom_families').ext.Install.Run()
op('MyFamily').ext.ComponentEXT.Install()
```

> Nei nostri esempi usiamo gli **op-shortcut** (`Custom_families`,
> nome della famiglia, ecc.). Funzionano da qualsiasi punto del progetto.

---

## 1. Contenitore — `Custom_families`

Il plugin nel suo complesso (toolbar, dialog, scaffali `Local`/`Server`).

### Install / Uninstall del plugin

| Funzione | Cosa fa |
|---|---|
| **`Install.Run()`** | Installa il plugin. Scarica il framework, monta toolbar e dialog, riallinea gli script. |
| **`Uninstall.Run()`** | Disinstalla il plugin. Ripristina la UI di TD allo stato originale. |

```python
op('Custom_families').ext.Install.Run()
op('Custom_families').ext.Uninstall.Run()
```

### Crea una nuova famiglia

| Funzione | Cosa fa |
|---|---|
| **`Createfamily.Create()`** | Spawna una nuova famiglia dentro `Local`. Clona il template `Embeded/Custom`, allinea `par.opshortcut` al nome assegnato da TD (`Custom`, `Custom1`, …) e attiva il cooking sul nuovo COMP. |

Si può chiamare in due modi equivalenti:

```python
# Via parametro (stessa via che usa il bottone Create_button della UI)
op('Custom_families').par.Createfamily.pulse()

# Via estensione (utile da script che vogliono il riferimento al nuovo COMP)
new_fam = op('Custom_families').op('Create_family').ext.Createfamily.Create()
```

`Create()` ritorna il COMP appena creato (o `None` in caso di errore).
Lo step finale dell'`Install.Run()` chiama già un pulse di `Createfamily`,
quindi a fresh install corrisponde sempre una prima famiglia pronta in `Local`.

---

## 2. Singola famiglia — `Custom_fam`

Una famiglia è un COMP creato/importato dentro `Custom_families/Local`.
Tutte le sue funzioni principali stanno sull'estensione **`ComponentEXT`**.

### Install / Uninstall

| Funzione | Cosa fa |
|---|---|
| **`Install()`** | Installa la famiglia (bottone in toolbar, voce nel menu_op, custom operators). |
| **`Uninstall()`** | Disinstalla la famiglia (rimuove tutto ciò che `Install` aveva aggiunto). |
| **`DeleteFamily()`** | Disinstalla **e** distrugge il COMP. Equivale a *Delete* nel menu contestuale. |

### Rename

| Funzione | Cosa fa |
|---|---|
| **`RenameEXT.RenameFamily(new_name)`** | Rinomina la famiglia. Pulisce il vecchio nome e reinstalla con il nuovo in modo atomico. |

```python
op('MyFamily').ext.RenameEXT.RenameFamily('NuovoNome')
```

### Export

| Funzione | Cosa fa |
|---|---|
| **`ExportFamily()`** | Apre un file picker e salva la famiglia come `.tox`. |

### Custom operators

| Funzione | Cosa fa |
|---|---|
| **`EditOperators()`** | Apre la cartella dei custom operators in un network pane. |

### Info

| Funzione | Cosa fa |
|---|---|
| **`GetFamilyName()`** | Ritorna il nome corrente della famiglia. |

### Refresh UI

| Funzione | Cosa fa |
|---|---|
| **`UpdateAll()`** | Rinfresca tutto ciò che la famiglia ha installato (bottone, colore, pagina About, custom operators). |

---

## Esempi

```python
# Plugin completo
op('Custom_families').ext.Install.Run()
op('Custom_families').ext.Uninstall.Run()

# Crea una nuova famiglia
op('Custom_families').par.Createfamily.pulse()
new_fam = op('Custom_families').op('Create_family').ext.Createfamily.Create()

# Singola famiglia
fam = op('MyFamily')
fam.ext.ComponentEXT.Install()
fam.ext.ComponentEXT.EditOperators()
fam.ext.ComponentEXT.ExportFamily()
fam.ext.ComponentEXT.Uninstall()
```

---

## Licenza

[MIT](LICENSE) © 2026 Gianluca Colia
