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

It **installs automatically**: drag the `.tox` into your project and
the plugin opens its own installation window. To uninstall, open the
**Preferences** button and click **Uninstall** — the uninstallation
window will remove every trace of the plugin and restore the UI to
its original state.

**Built-in families** distributed through a continuously updated
server are coming soon.

---

## Cosa installa

Quando trascini il `.tox` in TouchDesigner, la finestra di installazione
si apre e ti chiede se installare il plugin. Una volta installato avrà
aggiunta in alto una toolbar con tutto quello che serve per poter
manipolare le proprie famiglie:

<div align="center">
  <img src="Images/Toolbar.png" alt="Custom Families toolbar" />
</div>

Da sinistra a destra:

<table>
<tr>
<td width="100" align="center"><img src="Images/Preferences_fill.png" width="56" alt="Preferences" /></td>
<td><b>Preferences</b> — apre il pannello preferenze e contiene il pulsante di disinstallazione del plugin.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Local_text.png" width="80" alt="Local" /></td>
<td><b>Local</b> — il tuo framework personale: contiene tutte le famiglie che crei o importi sulla macchina locale.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Create_family.png" width="56" alt="Create family" /></td>
<td><b>Create new family</b> — un click crea una nuova famiglia vuota dentro <code>Local</code>, pronta da configurare.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Button_Custom.png" width="80" alt="Custom family" /></td>
<td><b>Famiglie locali</b> — ogni famiglia che vive dentro <code>Local</code> ha qui il suo bottone (in figura: una <i>Custom family</i> di esempio installata con il plugin, più un'altra famiglia chiamata <code>other</code>).</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Server_text.png" width="80" alt="Server" /></td>
<td><b>Server</b> — la sezione dove arriveranno le famiglie built-in distribuite e aggiornate dagli sviluppatori del plugin.</td>
</tr>
</table>

---

<details>
<summary><b>Custom_families — funzionalità</b></summary>

- Toolbar orizzontale dedicata in alto, integrata nel layout TD
- Dialog grafico di installazione con barra di progresso
- Dialog grafico di disinstallazione con barra di progresso
- Contenitori `Local` e `Server` per organizzare le famiglie
- Smart-check di stato: se mancano componenti, reinstalla solo quelli
- Disinstallazione pulita: ogni traccia (toolbar, inject, watcher)
  viene rimossa quando il plugin viene disinstallato
- Stile della toolbar configurabile (colore di sfondo, outline)
- Backup dell'UI originale prima dell'installazione

</details>

<details>
<summary><b>Custom_fam — funzionalità della famiglia</b></summary>

- Auto-installazione: drag-and-drop in `/project1` → la famiglia entra
  da sola in `Custom_families/Local`
- Bottone in toolbar generato automaticamente, colore personalizzabile
- Menu contestuale completo (vedi sezione successiva)
- Rinomina in-place dal label del bottone
- Duplicazione one-click con identità separata
- Set di custom operators incorporato
- Watcher dedicato che ripulisce gli inject UI quando la famiglia
  viene eliminata
- Release notes integrate, con editor e visualizzatore

</details>

<details>
<summary><b>Menu delle funzioni della famiglia</b></summary>

| Voce | Effetto |
|---|---|
| **Go to family** | Naviga al COMP della famiglia in un network pane |
| **Rename** | Rinomina la famiglia in-place |
| **Change color** | Apre il color picker del bottone |
| **Duplicate** | Duplica la famiglia con identità indipendente |
| **Edit custom operators** | Apre i custom operators in un nuovo pane |
| **Export family** | Esporta la famiglia come `.tox` |
| **Release notes** | Mostra le release notes |
| **Edit release notes** | Apre l'editor delle release notes |
| **View release notes** | Visualizzatore read-only |
| **Update** | Aggiorna la famiglia all'ultima versione |
| **Delete** | Elimina la famiglia e ne ripulisce ogni traccia UI |

</details>

---

## Licenza

[MIT](LICENSE) © 2026 Gianluca Colia
