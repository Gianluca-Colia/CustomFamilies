# Custom Families — Documentazione per sviluppatori

Questo documento elenca le **API pubbliche** esposte dai due componenti
che formano il plugin e descrive cosa fa ogni funzione. È pensato per
sviluppatori che vogliono pilotare Custom Families in modo programmatico
(textport TD, callback dei pannelli, script esterni) anziché tramite UI.

Le funzioni qui descritte sono quelle che seguono la convenzione di
TouchDesigner per le estensioni (nome con iniziale maiuscola → richiamabile
dall'esterno del componente). Gli helper interni (con underscore iniziale)
non sono inclusi di proposito.

---

## 1. `Custom_families` — il contenitore

Il contenitore è il COMP installato in `/ui/Plugins/Custom_families`.
Ospita la toolbar, le finestre di dialogo, gli scaffali `Local`/`Server`
ed è l'host per qualsiasi `Custom_fam` che crei o importi.

Ha tre classi di estensione, ciascuna agganciata a un sub-COMP diverso
(`Installer`, `Uninstaller`, `Updater`).

### 1.1 Estensione `Installer` — `Custom_families/Installer/Install.py`

| Funzione | Cosa fa |
|---|---|
| **`Run()`** | Entry point principale dell'install. Gira in tre fasi: (A) riallinea il DAT `Install` stesso alla copia in LOCALAPPDATA e rientra; (B) riallinea ogni altro DAT elencato nella tabella `Scripts`; (C) decide tra full install, reinstall chirurgico delle parti mancanti, oppure no-op "già installato". Pilota la barra di progresso dell'Install_window attraverso tutti i passi (download, split del pane, watcher, inject toolbar, patch del menu_op, abilitazione runtime/Local, riallineamento finale). |
| **`RealignScripts(only=None, skip=None)`** | Cammina la tabella `Scripts` dentro il COMP Installer e ripunta `par.file` di ogni riga al suo script canonico su disco in `LOCALAPPDATA/Derivative/TouchDesigner099/Custom families/...` quando il file esiste davvero lì. Ritorna `True` se almeno un `par.file` è cambiato. `only` restringe il pass a un singolo op path, `skip` ne esclude uno. |

### 1.2 Estensione `Uninstaller` — `Custom_families/Uninstaller/Uninstall.py`

| Funzione | Cosa fa |
|---|---|
| **`Run()`** | Entry point principale di uninstall. Pilota una sequenza multi-step deferita (visibile nella barra di progresso dell'Uninstall_window) che: ripristina la visibilità del panebar, ripristina lo stile originale della toolbar, ripristina i collegamenti `familypanel`/`families` del menu_op ai default TD, distrugge i contenitori `Local` e `Server` (lasciando ai watcher di ogni famiglia il tempo di scatenare la propria pulizia a catena), rimuove gli inject `Local_bar` / `Server_bar` / pulsante / `Pages` / `Page_number`, chiude il pane della toolbar, infine distrugge il COMP `Custom_families`. |

### 1.3 Estensione `Updater` — `Custom_families/Updater/Update.py`

Al momento è uno stub (scaffolding di estensione TD di default). Riservato
ai flussi di update futuri; nessuna funzione di produzione è ancora esposta.

---

## 2. `Custom_fam` — la singola famiglia

Una `Custom_fam` è una voce dentro lo scaffale `Local` (o `Server`) del
contenitore. Porta i propri custom operators, il proprio bottone in
toolbar, il proprio insert nel menu_op e il proprio watcher.

Espone quattro classi di estensione, ognuna con una responsabilità precisa.

### 2.1 `ComponentEXT` — ciclo di vita e stato condiviso

`Custom_fam/ComponentEXT.py` — l'estensione "facciata" della famiglia. La
maggior parte delle funzioni delega ai bridge specializzati installer/
uninstaller/rename; è da qui che si chiama quando si scripta contro una
famiglia.

#### Install / uninstall

| Funzione | Cosa fa |
|---|---|
| **`Install()`** | Installa la famiglia. Risolve il bridge installer, aggiorna lo shortcut globale, imposta `par.Install = 1`, poi delega a `InstallerEXT.Install()`. |
| **`Uninstall()`** | Disinstalla la famiglia delegando al bridge uninstaller (`RemoveFamily`). |
| **`HandleInstallValue(raw_value, source_label='external')`** | Coerce un valore (`'1'`/`'true'`/`'on'`/`'yes'` oppure `'0'`/`'false'`/`'off'`/`'no'`) e lo instrada verso `Install()` o verso `RemoveFamily()` dell'uninstaller. Usata dai callback che osservano `par.Install`. |
| **`DeleteCleanup()`** | Esegue lo stesso teardown di `Uninstall()`. Chiamata alla distruzione del COMP. |

#### Identità / nome

| Funzione | Cosa fa |
|---|---|
| **`GetFamilyName()`** | Ritorna il nome canonico della famiglia (lo shortcut globale sanitizzato). |
| **`GetGlobalShortcut()`** | Ritorna l'OP shortcut sanitizzato della famiglia, aggiornandolo se necessario. |
| **`UpdateGlobalShortcut()`** | Legge il parametro `opshortcut` corrente, lo sanitizza e salva il risultato nella property dependable `Global_op_shortcut`. Notifica l'installer se il nome è cambiato. |
| **`SanitizePluginName(name)`** | Rimuove gli spazi, scarta ogni carattere fuori da `[A-Za-z0-9_]`, prefissa con `_` un eventuale numero iniziale. È l'unica fonte di verità su come può essere fatto un nome di famiglia. |
| **`PromptRenameFamily()`** | Apre il `PopDialog` di rename (default sul nome corrente). Su conferma delega a `RenameEXT.RenameFamily`. |

#### Menu della famiglia / azioni

| Funzione | Cosa fa |
|---|---|
| **`OpenFamilyContextMenu(buttonComp=None)`** | Apre il `PopMenu` della famiglia allineato al bottone passato, con le voci: *Rename*, *Edit custom operators*, *Export family*, *Delete*. Ogni voce è cablata sul rispettivo metodo. |
| **`EditCustomOperators()`** | Apre il COMP root dei custom operators della famiglia nel network pane corrente (o nel suo viewer). |
| **`ExportFamily()`** | Mostra all'utente un file picker e salva il COMP della famiglia come `.tox` nel path scelto. |
| **`DeleteFamily()`** | Rimuove la famiglia delegando a `RemoveFamily` dell'uninstaller. |

#### Update / placement

| Funzione | Cosa fa |
|---|---|
| **`UpdateAll(showMessage=False)`** | Sweep completo: ricostruisce bookmark/bottone in toolbar, colore, mirroring della pagina About sui cloni installati, wiring dei custom operators e ogni stato derivato dal COMP. È il refresh "pesante". |
| **`ScheduleUpdateAll(showMessage=False)`** | Defera `UpdateAll` di un frame, fondendo richieste ripetute così che più trigger nello stesso tick eseguano il refresh una volta sola. Ritorna `False` se un refresh è già in coda. |
| **`DeferredUpdateAll(showMessage=False)`** | Target interno della call deferita di `ScheduleUpdateAll`. Si rimette in coda se è in corso un rename o reinstall, in modo che il refresh parta solo a stato del COMP stabilizzato. |
| **`PlaceNamedCustomOperator(display_name)`** | Piazza il custom operator indicato nel network pane corrente al cursore, come se l'utente l'avesse scelto dal dialog OP Create. |
| **`PlaceOp(panelValue, display_name)`** | Entry di placement di livello più basso usata dal callback del pannello OP Create; rispetta lo stato del panel value per evitare drop doppi. |
| **`CancelPendingPlacement(clear_pane=False)`** | Annulla qualsiasi drop in corso (es. l'utente ha premuto Esc). Se `clear_pane=True` ripulisce anche lo stato di anteprima del pane di destinazione. |

#### Sync del colore

| Funzione | Cosa fa |
|---|---|
| **`GetColorFromOwner()`** | Legge il colore della famiglia dal parametro dedicato sul COMP owner. |
| **`GetColorTargetsOfOwner(maxDepth=...)`** | Ritorna la lista degli operatori dentro la famiglia che devono assumere il colore famiglia (bottoni, bookmark tag, ecc.). |
| **`UpdateChildrenColor(maxDepth=...)`** | Propaga il colore corrente dell'owner a ogni figlio targetable. |
| **`SyncInstalledColor(maxDepth=...)`** | Stessa propagazione ma applicata ai *cloni installati* della famiglia che vivono fuori dal COMP sorgente (bottone in toolbar, insert nel menu_op, ecc.). |

#### Mirroring della pagina About

La pagina About è la pagina parametri esposta dai custom operators con
le info di famiglia/versione. Questi helper la mantengono sincronizzata
tra la famiglia sorgente e i suoi cloni:

| Funzione | Cosa fa |
|---|---|
| **`FindCustomPage(o, page_name)`** | Ritorna la custom page di nome dato su `o` se esiste, altrimenti `None`. |
| **`GetAboutTargetCompsOfOwner(maxDepth=...)`** | Elenca ogni COMP dentro la famiglia che deve portare la pagina About. |
| **`GetExternalAboutTargetComps()`** | Stesso elenco ma per i cloni installati fuori dal sorgente. |
| **`ExtractReferenceAboutDefinition(page_name=ABOUT_PAGE_NAME, excluded_par_names=None)`** | Snapshotta dal COMP sorgente le definizioni canoniche dei parametri della pagina About. |
| **`CreateCustomPage(target_op, page_name=ABOUT_PAGE_NAME)`** | Crea una nuova pagina About sull'operatore dato. |
| **`GetOrCreateCustomPage(target_op, page_name=ABOUT_PAGE_NAME)`** | Ritorna la pagina About su `target_op`, creandola se manca. |
| **`ParameterExists(target_op, par_name)`** | Helper: `target_op` ha un parametro chiamato `par_name`? |
| **`AppendParameterFromDefinition(target_page, par_def)`** | Aggiunge un parametro a una custom page partendo da una definizione snapshottata. |
| **`EnsureParameterExists(target_op, target_page, par_def)`** | Versione idempotente: aggiunge solo se manca. |
| **`ApplyExtraDefinition(target_op, par_def)`** | Applica gli extra (range, default, voci di menu, ...) sopra a un parametro già creato. |
| **`IsStringLikeStyle(style_name)`** | Ritorna True per gli stili di parametro che memorizzano una stringa. |
| **`SetTupletValues(target_op, par_def)`** | Scrive i valori di un tuplet sul parametro target. |
| **`UpdateAboutSpecialValues(target_op)`** | Aggiorna i valori speciali della pagina About (nome famiglia, versione, ...). |
| **`SyncAboutOnComp(target_op, about_defs, page_name=ABOUT_PAGE_NAME)`** | Sincronizza la pagina About su un singolo COMP target rispetto allo snapshot. |
| **`RebuildAboutOnAllComps(page_name=ABOUT_PAGE_NAME, maxDepth=...)`** | Spazza ogni COMP target e ricostruisce la sua pagina About da zero. |

#### Manutenzione

| Funzione | Cosa fa |
|---|---|
| **`RepairManagedScriptSyncs()`** | Cammina gli script gestiti dalla famiglia e ripunta il `par.file` di ognuno al path canonico su disco (relativo alla cartella root della famiglia). Ritorna il numero di script ripuntati. È il corrispettivo lato famiglia di `RealignScripts` del contenitore. |
| **`ScheduleInstallStateWatch()`** | Schedula un poll deferito di un frame su `par.Install`, così le modifiche di valore esterne vengono osservate e instradate via `HandleInstallValue`. |

---

### 2.2 `InstallerEXT` — pipeline di install

`Custom_fam/InstallerEXT.py` (classe `GenericInstallerEXT`, aliasata in
`InstallerEXT`).

| Funzione | Cosa fa |
|---|---|
| **`Install(family_name=None, color=None, compatible_types=None, show_message=False, is_update=None, reset_trace=True)`** | Routine di install principale. Sanitizza il nome famiglia, si assicura che il COMP della famiglia sia ospitato dentro `Custom_families/Local` (mette in coda un trasferimento se non lo è), sostituisce qualunque famiglia esistente con lo stesso nome, esegue la pipeline di install completa: re-tag dei figli, watcher di delete-execute, install toggle, install watcher, install dell'insert nel menu_op (`familypanel`), aggiornamento delle tabelle colori / compatible-types / eval, install degli hook panel-execute, patch di `create_node` e `search_exec`. Registra la famiglia installata per la pulizia successiva. |
| **`Uninstall(family_name=None, reset_trace=True)`** | Controparte uninstall principale. Smonta tutti gli inject/patch prodotti da `Install` (toggle, watcher, insert nel menu_op, panel-execute, patch su create_node e search_exec, voci nelle tabelle colore/compat/eval, marker di famiglia installata). |
| **`SchedulePostInitSetup()`** | Schedula il setup deferito post-`__init__`: bridge verso l'host (`Custom_families`), wiring degli hook runtime, refresh dello stato di install. Permette all'estensione di completare il caricamento prima di toccare la UI di TD. |
| **`SuppressContextMenuToggle(frame_window=3)`** | Sopprime il toggle di right-click della famiglia per una finestra di pochi frame, in modo che una cascata di eventi UI non riapra il menu mentre un'azione utente è in elaborazione. |
| **`ScheduleInstallStateWatch()`** | Stessa intenzione del metodo in ComponentEXT ma lato installer: defera di un frame il poll dello stato di install. |
| **`NormalizeCustomOperatorRuntimeExecutes()`** | Normalizza i DAT di runtime-execute per-operatore in tutta la famiglia, così ogni custom operator ha lo stesso nome/ruolo per il proprio hook runtime. |
| **`PrepareCustomOperatorRuntimeLink(operator_comp)`** | Cabla un singolo COMP custom-operator all'hook runtime della famiglia, così riceve gli eventi di livello famiglia (sync colore, sync About, placement). |
| **`RefreshCustomOperatorTemplate(operator_comp)`** | Ri-applica il template della famiglia a un COMP custom-operator: aggiorna in un solo passaggio tag, pagina About, colore e hook runtime. |
| **`RebuildInstalledClones(previous_family=None, new_family=None)`** | Ricostruisce ogni clone installato della famiglia (bottone toolbar, insert nel menu_op, copie dei custom operators). Quando la famiglia è in fase di rename, `previous_family`/`new_family` permettono al rebuild di rinominare in place. |
| **`DeleteCleanup(family_name=None, reset_trace=True)`** | Entry di compatibilità che mappa sul percorso di uninstall; chiamata alla distruzione del COMP. |
| **`HandleInstallValue(raw_value, source_label='external')`** | Mirror lato installer del metodo in ComponentEXT (stesse regole di coerce), così la modifica del toggle è instradabile anche quando solo l'estensione installer è raggiungibile. |
| **`HandleInstallFromOwnerState(source_label='external')`** | Legge il valore corrente di `par.Install` sull'owner e lo instrada via `HandleInstallValue`. Si usa come riconciliatore one-shot. |

---

### 2.3 `UninstallerEXT` — pipeline di uninstall

`Custom_fam/UninstallerEXT.py` (classe `GenericUninstallerEXT`, aliasata
in `UninstallerEXT`).

| Funzione | Cosa fa |
|---|---|
| **`RemoveFamily(family_name=None)`** | Uninstall completo. Distrugge prima il bottone in toolbar (così un bottone stale non può sopravvivere a un fallimento più profondo), poi delega alla catena di destroy dell'installer (cloni UI, menu_op, helper esterni di delete), pulisce il marker di famiglia installata, imposta `par.Install = 0`. Se il bridge installer non è raggiungibile, ricade su una pulizia self-contained. |
| **`RemoveInstalledUi(family_name=None)`** | Come `RemoveFamily` ma mantiene vivo l'install toggle — usata quando vuoi rinfrescare la UI installata della famiglia senza ribaltare lo stato di install (es. durante un rename). |
| **`Uninstall(family_name=None)`** | Alias di `RemoveFamily`, per simmetria con `InstallerEXT.Install`. |
| **`DeleteCleanup(family_name=None)`** | Alias di `RemoveFamily`, chiamata alla distruzione del COMP. |

---

### 2.4 `RenameEXT` — pipeline di rename

`Custom_fam/RenameEXT.py` (classe `GenericRenameEXT`, aliasata in
`RenameEXT`).

| Funzione | Cosa fa |
|---|---|
| **`RenameFamily(new_name, show_message=False, previous_name=None)`** | Rename atomico. Sanitizza il nuovo nome, cattura lo stato di install, distrugge il vecchio bottone, esegue `RemoveFamily(old_name)` se la famiglia era installata, rinomina il COMP owner, aggiorna `opshortcut` e `Global_op_shortcut`, poi reinstalla con il nuovo nome. Salva un flag `cf_reinstall_in_progress` e un guard `_renameInProgress` così che lo `UpdateAll` deferito non ricostruisca la nuova UI prima che la vecchia sia stata rimossa. Salta la pulizia distruttiva se un COMP fratello possiede ancora `old_name` (tipico quando un copia-incolla scatena un rename automatico sul duplicato). |
| **`HandleObservedNameChange(previous_name, new_name, show_message=False)`** | Wrapper chiamato dal watcher che osserva i rename del COMP. Sanitizza entrambi i nomi e inoltra a `RenameFamily`. |
| **`PromptRenameFamily()`** | Apre il `PopDialog` di rename. Specchio di `ComponentEXT.PromptRenameFamily` ma vive sull'estensione di rename stessa; usato come fallback quando viene chiamato da contesti in cui `ComponentEXT` non è raggiungibile. |

---

## Licenza

[MIT](LICENSE) © 2026 Gianluca Colia
