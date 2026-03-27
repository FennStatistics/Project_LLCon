# Project_LLCon

Commands
```
pip install -r requirements.txt
jupyter lab
python main.py
python application/main.py
```

Overview
This repository contains the L.L.Con. XML corpus and a local desktop search tool.
The workflow is two-phase: preprocess XML into SQLite (notebook), then run the UI
against the prepared database.

Data source
- Decisions of the German Federal Constitutional Court (GFCC), years 1951-2022.
- 1998+ decisions were downloaded from the GFCC website.
- 1951-1997 decisions (official report series, ORS) were provided by Mohr Siebeck.
- Documentation: `data/Wendel_Korpus_BVerfG/Documentation_EN.pdf`.

Search links
- L.L.Con. project: https://www.lehrstuhl-moellers.de/llcon
- GFCC decisions: https://www.bundesverfassungsgericht.de/e/
- Corpus data (Zenodo): https://zenodo.org/records/10369205

Credits
- Corpus compiled by Luisa Wendel and the L.L.Con. project team.


Project team
- Project supervision: Dr. Sarah Katharina Stein:
  https://csl.mpg.de/de/s-katharina-stein
- Programmer: Dr. Julius Fenn: 
  https://uni-freiburg.de/frias/dr-julius-fenn/
