<img src="assets/logo/LabelForge_logo.jpeg" width="240" />

## Download

➡️ **Windows installer:**  
https://github.com/GiannisFanourakis/LabelForge/releases/latest


# LabelForge (Windows)

**Structured Label & Classification Generator**

LabelForge is a Windows desktop application for creating **clean, consistent, and professionally formatted labels** based on **hierarchical classification structures**.  
It supports **Free Typing** and **Rules Mode (Excel)**, and exports **print-ready PDF labels** using formal templates.

---

## What LabelForge Does

### Build a hierarchy (Levels 1–4)
- Labels are created as a **tree** with up to four levels.
- Each node contains:
  - **Code**
  - **Name**
- Parent–child relationships remain visible, reducing mistakes and keeping structure clear.

### Two input modes

#### Free Typing Mode
- No restrictions
- Autocomplete improves over time using your saved history

#### Rules Mode (Excel-Driven)
- Load a `rules.xlsx` workbook
- Select a **profile**
- Code → Name mappings are enforced (optionally locked)
- Suggestions are scoped by parent level to prevent invalid choices

### Fast typing (“lazy-friendly”)
- Typing `1` can become `01` (rule-defined padding)
- Typing `2` under `01` becomes `01.2`
- Suggestions are context-aware (you only see valid options for that branch)

---

## PDF Export

### Output formats
- **PDF** (print-ready)

### Page sizes
- A4 / A5 presets (portrait & landscape)
- Optional custom size in **centimeters**

### Layout behavior
- Text wraps and font size adapts to avoid truncation
- When content is tall:
  - the exporter can flow into **two columns** on the same page
  - top-level groups are kept intact (Level 1 is not separated from its children when possible)

---

## Templates (Visual Styles)

Choose a template at export time (with preview):

- Classic Formal (Serif)
- Modern Formal (Sans-Serif)
- Institutional
- Boxed Sections
- Compact / Dense
- Code-First
- Indented Outline
- Two-Column Layout

You can also set an optional **Section Title** above the hierarchy:
- *(None)* (recommended default)
- Classification / Taxonomy / Collection Path / Hierarchy
- Custom

---

## Installing (Windows)

### Option A — Installer (recommended)
1. Download the latest LabelForge installer (`LabelForge-Setup.exe`)
2. Run the installer
3. Launch LabelForge from:
   - Start Menu, or
   - Desktop shortcut (if enabled)

### Option B — Portable build (if provided)
1. Download the portable zip
2. Extract anywhere (e.g., `C:\Apps\LabelForge`)
3. Run `LabelForge.exe`

---

## Using Rules Mode (Excel)

In **Rules Mode**, you will load a rules workbook.

**Basic expectations:**
- The workbook contains one or more **profiles**
- Each profile defines:
  - Level labels (what Level 1/2/3/4 are called)
  - Code formats (padding / delimiter)
  - Allowed values per level
  - Code → Name mappings

> If your organization has multiple standards, you can store them as separate profiles.

---

## Rules Mode (Excel)

LabelForge supports a rules-driven workflow using Excel authority files.

Included examples:
- `examples/rules/Rules_Example_SIMPLE.xlsx` – minimal, human-friendly authority format
- `examples/rules/Rules_Example_RANDOM.xlsx` – multi-level hierarchy example

Load these via **Rules Mode → Load Excel…** inside the application.


---

## Data & Cache

LabelForge stores a local autocomplete cache so typing gets faster over time.

Typical contents:
- Previously used codes and names per level
- Previously used titles and cabinet/section text

You can also manually trigger **Save Cache** from the UI.

---

## Troubleshooting

### App does not launch / closes immediately
- Re-run the installer as Administrator
- Ensure Windows Defender did not quarantine files
- Try launching from a local folder (not a network drive)

### PDF looks highlighted or “underlined” unexpectedly
This is usually your PDF viewer’s search highlighting (not part of the PDF).
- Press **Ctrl+F**
- Clear the search field and close search panel

### Rules file not loading
- Confirm it is `.xlsx` (not `.xls` or `.csv`)
- Ensure it is not password-protected
- Close the file in Excel before loading (some systems lock it)

---

## Intended Use
LabelForge is domain-agnostic and suitable for:
- museums and collections
- archives and libraries
- research labs
- inventory and storage labeling
- any workflow needing structured, repeatable labeling

---

## Feedback

Bug reports, suggestions, and real-world use cases are welcome.

Please open an issue:
https://github.com/GiannisFanourakis/LabelForge/issues


---


## Support LabelForge

LabelForge is **free and open-source software**.

If you find it useful and would like to support its continued development, you may choose to make a **voluntary donation**.

Donations help support:
- ongoing development
- bug fixes and maintenance
- long-term improvements

Donations are **optional** and do not affect your rights under the license.

---

## License

LabelForge is released under the **MIT License**.

You are free to use, modify, and distribute this software, including for commercial purposes, provided the license terms are respected.
