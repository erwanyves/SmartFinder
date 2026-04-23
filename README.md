# SmartFinder
A unified launcher for FreeCAD component macros — one toolbar icon to rule them all

SmartFinder is a FreeCAD macro that acts as an intelligent dispatcher for your component-specific macros (Springs, O-rings, Profiles, and any future additions). Instead of cluttering your toolbar with one icon per macro, SmartFinder provides a single entry point that auto-detects the selected component's family and launches the right macro automatically.

---

## Features

- **Auto-detection** — selects an existing component and SmartFinder identifies its family from its custom FreeCAD properties, then launches the associated macro directly, with no dialog required.
- **Manual selection** — when nothing is selected (or the component is not recognised), a clean dropdown lets you choose the target family.
- **Ambiguity handling** — if multiple families match the selected object (overlapping identifying properties), an orange warning banner invites you to pick the correct one or refine your family definitions.
- **Family editor** — a built-in CRUD dialog lets you add, edit, and delete component families at any time, without touching any file manually.
- **Add-family wizard** — step-by-step assistant that reads the custom properties of the currently selected FreeCAD object so you can pick the identifying property directly from a list.
- **Persistent storage** — family definitions are saved in `families.json` and survive FreeCAD restarts.
- **Internationalisation** — UI fully translated in English and French. Language is auto-detected from FreeCAD preferences, then system locale. A `lang.txt` file lets you override the language manually.
- **Extensible** — adding a new language requires only a new `locales/<code>.json` file. Adding a new component family takes three clicks in the editor.
- **Modular architecture** — cleanly separated into functional modules (controller, detector, launcher, families, UI, i18n) for easy maintenance and testing.

---

## Requirements

| Requirement | Version |
|---|---|
| FreeCAD | ≥ 1.0 |
| Python | ≥ 3.8 (bundled with FreeCAD) |
| PySide2 | bundled with FreeCAD |

No external dependencies.

---

## Installation

### 1. Locate your FreeCAD macro directory

In FreeCAD, go to **Edit → Preferences → General → Macro** to find your macro directory path, or open the macro editor (**Macro → Macros…**) and note the directory shown.

Typical paths:

| OS | Path |
|---|---|
| Linux | `~/.FreeCAD/Macro/` |
| macOS | `~/Library/Preferences/FreeCAD/Macro/` |
| Windows | `%APPDATA%\FreeCAD\Macro\` |

### 2. Copy the files

Place `SmartFinder.FCMacro` and the `SmartFinder/` folder into your macro directory:

```
<Macro directory>/
├── SmartFinder.FCMacro          ← entry point (the file you run)
└── SmartFinder/
    ├── __init__.py
    ├── controller.py
    ├── detector.py
    ├── families.json             ← auto-created on first run
    ├── families.py
    ├── i18n.py
    ├── lang.txt                  ← optional language override
    ├── launcher.py
    ├── ui_add_wizard.py
    ├── ui_editor.py
    ├── ui_main.py
    └── locales/
        ├── en.json
        └── fr.json
```

### 3. Add a toolbar button (recommended)

1. Go to **Tools → Customize → Toolbars**
2. In the left panel, select **Macros**
3. Find `SmartFinder` and add it to a toolbar
4. Optionally assign a custom icon and keyboard shortcut

---

## Quick Start

### Running for the first time

Launch SmartFinder from the toolbar or via **Macro → Macros… → SmartFinder**.

On first run, `families.json` is empty. SmartFinder will prompt you to add a family immediately.

### Adding your first family

1. In your FreeCAD document, **select an existing component** of the type you want to register (e.g. a Spring body).
2. Launch SmartFinder — it opens the **Type Editor** automatically.
3. Click **➕ Add…** to open the wizard.
4. **Step ①** — Enter a name for the family (e.g. `Spring`).
5. **Step ②** — The wizard lists the custom properties found on your selected object. Pick the one that uniquely identifies this component type (e.g. `SpringRate`). If no object is selected, type the property name manually.
6. **Step ③** — Click **Browse…** and select the `.FCMacro` file associated with this family.
7. Click **OK** — the family is saved.

Repeat for each component type (Oring, Profile, etc.).

### Everyday use

| Situation | What happens |
|---|---|
| Select a recognised component → launch SmartFinder | The associated macro starts immediately |
| Select nothing (or an unrecognised object) → launch SmartFinder | A dropdown appears — pick a family and click **Launch** |
| Two or more families match the selected object | An orange ⚠ banner explains the ambiguity — choose the correct family or open the editor to fix identifying properties |

---

## Language Configuration

SmartFinder detects the language to use in the following order:

1. **`lang.txt`** — place a two-letter ISO 639-1 code (e.g. `fr`) in `SmartFinder/lang.txt` to force a specific language. Leave the file empty to fall back to auto-detection.
2. **FreeCAD preference** — the language set in FreeCAD's General preferences.
3. **System locale** — the OS locale (e.g. `fr_BE` → `fr`).
4. **Fallback** — English (`en`).

### Adding a new language

1. Copy `locales/en.json` to `locales/<code>.json` (e.g. `locales/de.json`).
2. Translate all values — do not change the keys.
3. Comment lines (keys starting with `#`) can be left as-is.

SmartFinder will pick up the new language automatically when the system locale matches.

---

## Project Structure

```
SmartFinder/
├── controller.py      Orchestration — detects family, decides direct launch vs dialog
├── detector.py        Inspects selected FreeCAD object, returns matching families
├── families.py        CRUD layer — reads/writes families.json
├── i18n.py            Language detection and tr() translation function
├── launcher.py        Executes a .FCMacro file in an isolated namespace
├── ui_add_wizard.py   Step-by-step dialog for adding / editing a family
├── ui_editor.py       CRUD dialog — list, add, edit, delete families
├── ui_main.py         Main dialog — dropdown + launch / edit buttons
└── locales/
    ├── en.json        English strings (reference)
    └── fr.json        French strings
```

---

## How Family Detection Works

Each family is identified by a **single custom FreeCAD property name**. When SmartFinder is launched:

1. It reads the list of properties on the selected object.
2. It compares them against the identifying property of every registered family.
3. **Exactly one match** → the associated macro is launched directly.
4. **No match** → the manual selection dialog is shown.
5. **Multiple matches** → the ambiguity dialog is shown with a list of candidates.

To avoid false positives, choose an identifying property that is **unique to that component type** — a property that your macro adds only to that specific kind of object (e.g. `SpringRate` rather than a generic `Diameter`).

---

## Extending SmartFinder

### Supporting a new component macro

You do not need to modify any code. Simply:

1. Develop your component macro as a standalone `.FCMacro` file.
2. Open SmartFinder, click **Edit types…**, then **➕ Add…**.
3. Fill in the wizard — name, identifying property, macro path.

### Adding UI translations

See [Adding a new language](#adding-a-new-language) above.

### Modifying the source

Each module has a single, well-defined responsibility. The recommended entry points for customisation are:

- **`detector.py`** — change how families are matched (e.g. match on property value, not just presence).
- **`families.py`** — swap the JSON backend for a different storage format.
- **`launcher.py`** — change how macros are executed (e.g. import as a module instead of exec).

---

## Related Macros

SmartFinder was designed to work with the following companion macros, also available in this repository:

- **SpringFull.FCMacro** — parametric spring designer
- **Oring.py** — O-ring groove manager (ISO 3601, DIN 3771, JIS B2401)
- **Profile.FCMacro** — structural profile library

---

## Contributing

Contributions are welcome — bug reports, translations, and pull requests alike.

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-improvement`
3. Commit your changes.
4. Open a pull request.

Please keep each module's single-responsibility principle intact, and add or update the relevant `locales/*.json` entries for any new user-facing strings.

---

## License

This project is licensed under the **LGPL License** — see the [LICENSE](LICENSE) file for details.
