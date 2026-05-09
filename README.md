<div align="center">
  <img src="Images/Install%20window%20content.png" alt="Custom Families" width="260" />

  # Custom Families

  Plugin TouchDesigner per **creare, manipolare, salvare ed esportare
  famiglie di operatori personalizzate**, con installazione e
  disinstallazione automatiche e un sistema di compatibilità integrato.

  [![Download](https://img.shields.io/badge/Download-Custom__families.tox-orange?style=for-the-badge&logo=download)](https://github.com/Gianluca-Colia/CustomFamilies/raw/main/.tox/Custom_families/Custom_families.tox)
</div>

---

## Cos'è

Custom Families è un plugin per TouchDesigner che ti permette di
**creare, manipolare, salvare ed esportare** famiglie di operatori
personalizzate, con un sistema di compatibilità che ne garantisce il
funzionamento tra versioni diverse.

Si **installa e disinstalla automaticamente**: trascini il `.tox` nel
progetto e il plugin registra la propria toolbar, i propri dialog e i
propri watcher; all'uninstall rimuove ogni traccia e restituisce l'UI
originale.

Presto arriveranno **famiglie built-in** distribuite tramite un server
costantemente aggiornato.

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
<summary><b>Menu del bottone famiglia</b></summary>

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
