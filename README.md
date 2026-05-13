<div align="center">
  <img src="readme-assets/Nameplate%20loop.gif" alt="Custom Families" />

  TouchDesigner plugin to **create, manipulate, save and export
  custom operator families**, with automatic installation and
  uninstallation and a built-in compatibility system.

  [![Download TOX](https://img.shields.io/badge/Download_TOX-orange?style=for-the-badge&logo=download)](https://github.com/Gianluca-Colia/CustomFamilies/raw/main/.tox/Custom_families/Custom_familie[...]
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  [![TouchDesigner](https://img.shields.io/badge/TouchDesigner-2025.32460-blueviolet?style=for-the-badge)](https://derivative.ca/download)

  Developed and tested on **TouchDesigner build 2025.32460** — compatible with this version.

  [![License: MIT](https://img.shields.io/github/license/Gianluca-Colia/CustomFamilies?style=flat-square)](LICENSE)
  [![Issues](https://img.shields.io/github/issues/Gianluca-Colia/CustomFamilies?style=flat-square)](https://github.com/Gianluca-Colia/CustomFamilies/issues)
  [![Stars](https://img.shields.io/github/stars/Gianluca-Colia/CustomFamilies?style=flat-square)](https://github.com/Gianluca-Colia/CustomFamilies/stargazers)
  [![Last commit](https://img.shields.io/github/last-commit/Gianluca-Colia/CustomFamilies?style=flat-square)](https://github.com/Gianluca-Colia/CustomFamilies/commits/main)
</div>

---

## What it is

**Custom Families** is a powerful **TouchDesigner plugin** and **TOX extension** that lets you **create, manipulate, save and export** custom operator families with ease. Features a built-in compatibility system across different TouchDesigner versions, allowing you to manage, organize, and distribute custom operators efficiently.

Whether you're building **custom COMP families**, **operator extensions**, or **TouchDesigner tools**, this plugin streamlines the entire workflow with automatic installation, intelligent dependency management, and version control capabilities.

**Built-in families** distributed through a continuously updated server are coming soon.

---

## Key Features

- 🎨 **Create custom operator families** — build and organize custom COMP families effortlessly
- 📦 **Drag-and-drop TOX import** — auto-install `.tox` files directly into your project
- 🔧 **Operator extension management** — manage complex operator hierarchies and dependencies
- 💾 **Export families as TOX** — package and share your custom operators and families
- 🔄 **Automatic installation/uninstallation** — one-click setup and cleanup
- 🛡️ **Compatibility system** — works across different TouchDesigner versions (2025+)
- 🎯 **Overcome TouchDesigner limitations** — bypass the native 12-family limit in menu_op

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

<div align="center">
  <img src="readme-assets/Logo%20loop.gif" alt="Custom Families" width="260" />
</div>

Once installed, a **horizontal toolbar** is added at the top of the
TouchDesigner interface with everything you need to manage your families:

<div align="center">
  <img src="readme-assets/Toolbarv.png" alt="Custom Families toolbar" />
</div>

From left to right:

<table>
<tr>
<td width="100" align="center"><img src="Images/Preferences_fill.png" width="56" alt="Preferences" /></td>
<td><b>Preferences</b> — opens the preferences panel and contains the plugin uninstall button.</td>
</tr>
<tr>
<td width="100" align="center"><img src="readme-assets/Local_text.png" width="80" alt="Local" /></td>
<td><b>Local</b> — your personal framework: contains all the families you create or import on the local machine.</td>
</tr>
<tr>
<td width="100" align="center"><img src="Images/Create_family.png" width="56" alt="Create family" /></td>
<td><b>Create new family</b> — one click creates a new empty family inside <code>Local</code>, ready to configure.</td>
</tr>
<tr>
<td width="100" align="center"><img src="readme-assets/Button_Custom.png" width="80" alt="Custom family" /></td>
<td><b>Local families</b> — each family inside <code>Local</code> gets its own button here (shown: a sample <i>Custom family</i> installed with the plugin, plus another family called <code>other</code> family).</td>
</tr>
<tr>
<td width="100" align="center"><img src="readme-assets/Server_text.png" width="80" alt="Server" /></td>
<td><b>Server</b> — the section where built-in families distributed and updated by the plugin developers will appear.</td>
</tr>
</table>

---

## Features

<details>
<summary><b>Custom_families — plugin features</b></summary>

- Dedicated horizontal toolbar, integrated into the TD layout
- Installation window with loading bar
- Uninstallation window with loading bar
- Local framework to build your own families and custom operators
- Smart state check: if components are missing, they are reinstalled
- Clean uninstall: every trace of the plugin is removed when it is uninstalled
- Backup of the original UI before installation
- Overcomes TouchDesigner's built-in 12-family limit in menu_op
- Page numbering system to navigate families beyond the first page
- Support for custom operator distribution and versioning

</details>

<details>
<summary><b>Custom_fam — family management features</b></summary>

- Auto-install: drag-and-drop into `/project1` → the family enters `Custom_families/Local` on its own
- Toolbar button generated automatically, with customisable colour
- Full context menu for operator family management
- In-place rename from the button label
- One-click duplication with separate identity
- Built-in set of custom operators and COMP templates
- Integrated release notes, with editor and viewer
- Family versioning and compatibility tracking

</details>

<details>
<summary><b>Family function menu</b></summary>

| Item | Shortcut | Effect |
|---|---|---|
| **Go to family** | | Navigates to the family COMP in a network pane |
| **Rename** | `Ctrl+R` | Renames the family in-place |
| **Change color** | | Opens the button colour picker |
| **Duplicate** | `Ctrl+D` | Duplicates the family with an independent identity |
| **Edit operators** | `Ctrl+E` | Opens the custom operators in a new pane |
| **Export family** | | Exports the family as a `.tox` |
| **Release notes** | | Shows the release notes |
| **Edit release notes** | | Opens the release notes editor |
| **View release notes** | | Read-only viewer |
| **Update** | | Updates the family to the latest version |
| **Delete** | `Del` | Deletes the family and cleans up every UI trace |

</details>

---

## Use Cases

- 📚 **Organize reusable COMP families** — centralize your custom components and operator templates
- 🎬 **Build production tools** — create distributable operator extensions for teams
- 🔌 **Develop TouchDesigner extensions** — package custom operators as installable plugins
- 🌐 **Share operator libraries** — export and distribute families as `.tox` files
- 🚀 **Scale your workflow** — manage complex operator hierarchies efficiently

---

## Coming soon

Features currently in development:

- **Preferences window** — dedicated panel for plugin settings
- **UI theme selector** — dropdown inside Preferences to switch button and label aesthetics to a more TouchDesigner-native look
- **Theme-aware context menus** — context menus that automatically follow the chosen UI theme
- **Built-in families server** — families distributed and kept up to date by the developers
- **More consistent permanent installation**

---

## Links

- 📖 [Developer documentation](Documentation.md) — public API of the two main components
- 🐞 [Issues / known bugs](https://github.com/Gianluca-Colia/CustomFamilies/issues) — report a bug or browse what's pending
- 🚀 [Releases](https://github.com/Gianluca-Colia/CustomFamilies/releases) — tagged versions and changelogs
- 📄 [License (MIT)](LICENSE)

---

## License

[MIT](LICENSE) © 2026 Gianluca Colia