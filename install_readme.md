# install_readme

This file explains how to install and run the app in simple words.

Windows build (Option A - recommended)
You must build the Windows .exe on a Windows 11 machine.

1) Install Python
- Download from https://python.org
- During install, check "Add Python to PATH"

2) Get the project
- Copy the project folder to the Windows PC
- Or use git to clone it

3) Install packages
```
pip install -r requirements.txt
```

4) Build the database
- Run: `jupyter lab`
- Open: `notebooks/prepare_corpus.ipynb`
- Run all cells
- Output: `data_processed/corpus.sqlite`

5) Run the app (for testing)
```
python main.py
```

6) Build the Windows .exe
```
pyinstaller --noconfirm --name LLConSearch --windowed --clean main.py
```

The .exe will be in: `dist/LLConSearch/`.

Local run (macOS or Windows)
1) Install packages
```
pip install -r requirements.txt
```

2) Build the database
- Run: `jupyter lab`
- Open: `notebooks/prepare_corpus.ipynb`
- Run all cells

3) Run the app
```
python main.py
```
