<div align="center">
  <img src="Images/Install%20window%20content.png" alt="Custom Families" width="260" />

  # Custom Families

  TouchDesigner plugin to **create, manipulate, save and export
  custom operator families**, with automatic installation and
  uninstallation and a built-in compatibility system.

  [![Download](https://img.shields.io/badge/Download-Custom__families.tox-orange?style=for-the-badge&logo=download)](https://github.com/Gianluca-Colia/CustomFamilies/raw/main/.tox/Custom_families/Custom_families.tox)
  [![TouchDesigner](https://img.shields.io/badge/TouchDesigner-2025.32460-blueviolet?style=for-the-badge)](https://derivative.ca/download)

  Developed and tested on **TouchDesigner build 2025.32460** — compatible with this version.
</div>

---

## What it is

Custom Families is a TouchDesigner plugin that lets you **create,
manipulate, save and export** custom operator families, with a
compatibility system across different versions.

**Built-in families** distributed through a continuously updated
server are coming soon.

---

## Installation

Click the **Download** button at the top of this page to get the
`.tox` file, then drag it into your TouchDesigner project. The
installation window will open and ask whether you want to install
the plugin.

---

## Uninstall

Open the **Preferences** button and click **Uninstall** — the
uninstallation window will remove every trace of the plugin and
restore the UI to its original state.

---

## What gets added to the UI

Once installed, a **horizontal toolbar** is added at the top of the
TouchDesigner interface with everything you need to manage your families:

<div align="center">
  <img src="Images/Toolbar.png" alt="Custom Families toolbar" />
</div>

From left to right:

<table>
<tr>
<td width="100" align="center"><img src="Images/Preferences_fill.png" width="56" alt="Preferences" /></td>
<td><b>Preferences</b> — opens the preferences panel and contains the plugin uninstall button.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Local_text.png" width="80" alt="Local" /></td>
<td><b>Local</b> — your personal framework: contains all the families you create or import on the local machine.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Create_family.png" width="56" alt="Create family" /></td>
<td><b>Create new family</b> — one click creates a new empty family inside <code>Local</code>, ready to configure.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Button_Custom.png" width="80" alt="Custom family" /></td>
<td><b>Local families</b> — each family inside <code>Local</code> gets its own button here (shown: a sample <i>Custom family</i> installed with the plugin, plus another family called <code>other</code>).</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Server_text.png" width="80" alt="Server" /></td>
<td><b>Server</b> — the section where built-in families distributed and updated by the plugin developers will appear.</td>
</tr>
</table>

---

<details>
<summary><b>Custom_families — funzionalità</b></summary>

- Toolbar orizzontale dedicata, integrata nel layout TD
- Finestra di installazione con barra di caricamento
- Finestra di disinstallazione con barra di caricamento
- Framework locale per realizzare le proprie famiglie
- Smart-check di stato: se mancano componenti, vengono reinstallati
- Disinstallazione pulita: ogni traccia (toolbar, inject, watcher) viene rimossa quando il plugin viene disinstallato
- Backup dell'UI originale prima dell'installazione

</details>

<details>
<summary><b>Custom_fam — funzionalità della famiglia</b></summary>

- Auto-installazione: drag-and-drop in `/project1` → la famiglia entra da sola in `Custom_families/Local`
- Bottone in toolbar generato automaticamente, colore personalizzabile
- Menu contestuale completo (vedi sezione successiva)
- Rinomina in-place dal label del bottone
- Duplicazione one-click con identità separata
- Set di custom operators incorporato
- Release notes integrate, con editor e visualizzatore

</details>

<details>
<summary><b>Family function menu</b></summary>

| Item | Effect |
|---|---|
| **Go to family** | Navigates to the family COMP in a network pane |
| **Rename** | Renames the family in-place |
| **Change color** | Opens the button colour picker |
| **Duplicate** | Duplicates the family with an independent identity |
| **Edit custom operators** | Opens the custom operators in a new pane |
| **Export family** | Exports the family as a `.tox` |
| **Release notes** | Shows the release notes |
| **Edit release notes** | Opens the release notes editor |
| **View release notes** | Read-only viewer |
| **Update** | Updates the family to the latest version |
| **Delete** | Deletes the family and cleans up every UI trace |

</details>

---

## License

[MIT](LICENSE) © 2026 Gianluca Colia
