# App_readme

This guide explains how to use the local search app in simple steps.

Quick start
1) Install packages
- `pip install -r requirements.txt`

2) Build the search database
- Open Jupyter: `jupyter lab`
- Run notebook: `notebooks/prepare_corpus.ipynb`
- Output file: `data_processed/corpus.sqlite`

3) Run the app
- `python main.py`

If the app says the database is missing, re-run the notebook step.

Using the search

Search box
- Type a query and press Enter or click Search.

Query syntax
- Boolean: `AND`, `OR`, `NOT`
- Grouping: parentheses, e.g. `(term1 OR term2) AND term3`
- Proximity: `term1 <5> term2` means within 5 words
- Chain proximity: `a <3> b <5> c`
- Wildcard prefix: `Nationals*` matches `Nationalsozialismus`, `Nationalstolz`
- Case-insensitive

Filters
- Section: choose a top-level section (or All)
- Year range: From / To
- Year list: comma-separated values, e.g. `1951,1970,2000`
- Band range: From / To
- Band list: comma-separated values, e.g. `10,104,158`
- Type: Entscheidungsart (or All)

Rules for year/band
- If the list is filled, it overrides the range.
- If both are empty, no filter is applied.

Sort options
- Relevance: BM25 score (lower score = more relevant)
- Document order: corpus order
- File name: alphabetical
- Section: section then file name

Results
- Summary at the top shows total matches and files.
- Each result shows file name, section, and paragraph metadata.

Export to PDF
- Run a search, then click Generate PDF.
- Choose where to save the file.
- The PDF lists file names and their sections from the current results.

Troubleshooting
- No results: check spelling or broaden filters.
- Database missing: run `notebooks/prepare_corpus.ipynb` again.
- PDF empty: make sure the current search returns results.
