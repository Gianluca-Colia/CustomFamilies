# Custom Families — Documentazione

Guida rapida alle funzioni che puoi chiamare via Python (textport,
callback, script esterni) senza passare dalla UI.

In TouchDesigner ogni funzione vive su un'estensione di un COMP. La
chiami così:

```python
op('/ui/Plugins/Custom_families/Installer').ext.Install.Run()
op('/ui/Plugins/Custom_families/Local/MyFamily').ext.ComponentEXT.Install()
```

> Convenzione TD: solo i metodi con iniziale maiuscola sono richiamabili
> dall'esterno. Quelli con underscore iniziale sono interni.

---

## 1. Contenitore — `Custom_families`

Il plugin nel suo complesso. Il COMP risiede in
`/ui/Plugins/Custom_families` e ospita tutte le famiglie.

### Install / Uninstall del plugin

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`Run()`** | `Installer/Install` | Installa il plugin. Scarica il framework da GitHub in LOCALAPPDATA, riallinea gli script, monta toolbar, watcher, dialog e patch del menu_op. Idempotente: se è già installato non fa nulla; se manca solo qualcosa lo reinstalla. |
| **`Run()`** | `Uninstaller/Uninstall` | Disinstalla il plugin. Ripristina la UI di TD allo stato originale e rimuove ogni traccia (toolbar, dialog, watcher, contenitori `Local`/`Server`, COMP `Custom_families`). |

```python
# Install
op('/ui/Plugins/Custom_families/Installer').ext.Install.Run()

# Uninstall
op('/ui/Plugins/Custom_families/Uninstaller').ext.Uninstall.Run()
```

### Manutenzione

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`RealignScripts()`** | `Installer/Install` | Ripunta `par.file` di ogni DAT della tabella `Scripts` alla copia canonica in `LOCALAPPDATA/.../Custom families/...`. Utile dopo aver spostato la cartella di progetto. |

---

## 2. Singola famiglia — `Custom_fam`

Ogni famiglia che crei o importi è un COMP dentro
`Custom_families/Local/`. Ha quattro estensioni: `ComponentEXT`,
`InstallerEXT`, `UninstallerEXT`, `RenameEXT`.

**`ComponentEXT` è la facciata principale** — chiama da qui per la
maggior parte delle operazioni.

### Install / Uninstall di una famiglia

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`Install()`** | `ComponentEXT` | Installa la famiglia: monta bottone in toolbar, voce nel menu_op, watcher e custom operators. |
| **`Uninstall()`** | `ComponentEXT` | Disinstalla la famiglia: rimuove bottone, voce nel menu_op e tutti i cloni installati. |
| **`DeleteFamily()`** | `ComponentEXT` | Disinstalla **e** distrugge il COMP della famiglia. Equivalente alla voce *Delete* nel menu contestuale. |

### Rename / Export

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`PromptRenameFamily()`** | `ComponentEXT` | Apre il dialog di rename. Su conferma rinomina la famiglia in modo atomico (cleanup vecchio nome + reinstall col nuovo). |
| **`RenameFamily(new_name)`** | `RenameEXT` | Versione programmatica del rename, senza dialog. |
| **`ExportFamily()`** | `ComponentEXT` | Apre il file picker e salva la famiglia come `.tox`. |

### Custom operators

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`EditCustomOperators()`** | `ComponentEXT` | Apre la cartella dei custom operators della famiglia in un network pane. |
| **`PlaceNamedCustomOperator(name)`** | `ComponentEXT` | Piazza il custom operator indicato nel pane corrente, come se fosse stato scelto dall'OP Create dialog. |

### Identità

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`GetFamilyName()`** | `ComponentEXT` | Ritorna il nome canonico (sanitizzato) della famiglia. |
| **`SanitizePluginName(name)`** | `ComponentEXT` | Applica le regole di nome valido (no spazi, solo `[A-Za-z0-9_]`, no numero iniziale). Utile prima di passare un nome a `RenameFamily`. |

### Aggiornamento UI

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`UpdateAll()`** | `ComponentEXT` | Forza un refresh completo di tutto ciò che la famiglia ha installato (bottone, colore, pagina About, custom operators). |
| **`ScheduleUpdateAll()`** | `ComponentEXT` | Stesso refresh ma deferito di un frame, utile dopo modifiche rapide consecutive. |

### Menu contestuale

| Funzione | Estensione | Cosa fa |
|---|---|---|
| **`OpenFamilyContextMenu(buttonComp)`** | `ComponentEXT` | Apre il menu *Rename / Edit custom operators / Export family / Delete* allineato al bottone passato. |

---

## Esempi

```python
# Lavora sul plugin nel suo complesso
cf_installer = op('/ui/Plugins/Custom_families/Installer')
cf_installer.ext.Install.Run()
cf_installer.ext.Install.RealignScripts()

# Lavora su una singola famiglia
fam = op('/ui/Plugins/Custom_families/Local/MyFamily')
fam.ext.ComponentEXT.Install()
fam.ext.ComponentEXT.PlaceNamedCustomOperator('MyOperator')
fam.ext.RenameEXT.RenameFamily('NuovoNome')
fam.ext.ComponentEXT.ExportFamily()
fam.ext.ComponentEXT.Uninstall()
```

---

## Licenza

[MIT](LICENSE) © 2026 Gianluca Colia
