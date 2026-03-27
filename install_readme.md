# install_readme

This file lists the Python packages to install for a GUI-based XML tooling workflow. Optional items are marked as such.

Packages

1) GUI (modern replacement for Tkinter)
- Install: `pip install PySide6`
- Purpose: PySide6 is the UI framework (Qt for Python).

2) XML parsing
- Install: `pip install lxml`
- Purpose: lxml provides fast, robust XML parsing.

3) Optional but recommended: better search
- Install: `pip install regex`
- Purpose: regex offers improved proximity search vs the standard re module.

4) Optional later: speed up search
- Install: `pip install rapidfuzz`
- Purpose: rapidfuzz supports fuzzy matching and ranking.

5) Packaging to .exe
- Install: `pip install pyinstaller`
- Purpose: PyInstaller builds Windows executables.

6) Optional dev tools
- Install: `pip install pyside6-tools`
- Run: `pyside6-designer`
- Purpose: Qt Designer provides a drag-and-drop UI builder.

Final install (copy-paste)

```
pip install PySide6 lxml regex pyinstaller pyside6-tools
```
