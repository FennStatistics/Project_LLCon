from __future__ import annotations

from html import escape
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal
from PySide6.QtCore import Slot
from PySide6.QtGui import QFont
from PySide6.QtGui import QPageSize
from PySide6.QtGui import QPdfWriter
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QComboBox
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QLineEdit
from PySide6.QtWidgets import QMainWindow
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPushButton
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QTextBrowser

from models.absatz import AbsatzRecord
from services.search_service import SearchResult
from services.search_service import SearchService
from services.search_service import SearchServiceError
from utils.highlight import highlight_text


class SearchWorker(QObject):
    finished = Signal(SearchResult)
    failed = Signal(str)

    def __init__(
        self,
        db_path: Path,
        query: str,
        section_filter: str | None,
        year_from: int | None,
        year_to: int | None,
        year_list: list[int] | None,
        band_from: int | None,
        band_to: int | None,
        band_list: list[int] | None,
        entscheidungsart_filter: str | None,
        sort: str,
        limit: int,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.query = query
        self.section_filter = section_filter
        self.year_from = year_from
        self.year_to = year_to
        self.year_list = year_list
        self.band_from = band_from
        self.band_to = band_to
        self.band_list = band_list
        self.entscheidungsart_filter = entscheidungsart_filter
        self.sort = sort
        self.limit = limit

    @Slot()
    def run(self) -> None:
        try:
            service = SearchService(self.db_path)
            result = service.search(
                self.query,
                self.section_filter,
                self.year_from,
                self.year_to,
                self.year_list,
                self.band_from,
                self.band_to,
                self.band_list,
                self.entscheidungsart_filter,
                self.sort,
                self.limit,
            )
            service.close()
            self.finished.emit(result)
        except (SearchServiceError, Exception) as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("L.L.Con. XML Search")
        self.db_path = db_path
        self.max_results = 500
        self.thread: QThread | None = None
        self.worker: SearchWorker | None = None

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "term1 <5> term2 AND (term3 OR term4) AND NOT(term5)"
        )
        self.search_help = QLabel(
            "Search terms: AND, OR, NOT, parentheses. Proximity: term1 <5> term2. "
            "Chain proximity: a <3> b <5> c. Prefix wildcard: Nationals*. "
            "Case-insensitive."
        )
        self.search_help.setWordWrap(True)
        self.search_button = QPushButton("Search")
        self.section_filter = QComboBox()
        self.year_from = QComboBox()
        self.year_to = QComboBox()
        self.year_list = QLineEdit()
        self.year_list.setPlaceholderText("e.g. 1951,1970,2000")
        self.band_from = QComboBox()
        self.band_to = QComboBox()
        self.band_list = QLineEdit()
        self.band_list.setPlaceholderText("e.g. 10,104,158")
        self.entscheidungsart_filter = QComboBox()
        self.sort_combo = QComboBox()
        self.sort_help = QLabel(
            "Sort: Relevance uses BM25 (term frequency / inverse document frequency; "
            "lower score = more relevant). "
            "Document order = corpus order. File name = alphabetical. "
            "Section = section then file name."
        )
        self.sort_help.setWordWrap(True)
        self.summary_label = QLabel("Ready")
        self.summary_label.setWordWrap(True)
        self.results_browser = QTextBrowser()
        self.results_browser.setOpenExternalLinks(False)
        self.pdf_button = QPushButton("Generate PDF")
        self.pdf_button.setEnabled(False)
        self.last_result: SearchResult | None = None
        self.last_query: str = ""
        self.last_filter_texts: tuple[str, str, str, str] = (
            "All sections",
            "All years",
            "All bands",
            "All types",
        )

        self._setup_filters()
        self._setup_layout()
        self._connect_signals()

    def _setup_filters(self) -> None:
        try:
            service = SearchService(self.db_path)
            sections = service.get_sections()
            years = service.get_years()
            bands = service.get_bands()
            entscheidungsarten = service.get_entscheidungsarten()
            service.close()
        except SearchServiceError:
            sections = []
            years = []
            bands = []
            entscheidungsarten = []

        self.section_filter.addItem("All sections", None)
        for section in sections:
            if section is None:
                self.section_filter.addItem("Unknown", "__unknown__")
            else:
                self.section_filter.addItem(section, section)

        self.year_from.addItem("All", None)
        self.year_to.addItem("All", None)
        years_sorted = sorted([year for year in years if year is not None])
        for year in years_sorted:
            self.year_from.addItem(str(year), year)
            self.year_to.addItem(str(year), year)

        self.band_from.addItem("All", None)
        self.band_to.addItem("All", None)
        band_values: list[tuple[int, str]] = []
        for band in [value for value in bands if value is not None]:
            try:
                band_values.append((int(band), str(band)))
            except ValueError:
                continue
        for band_value, band_label in sorted(band_values, key=lambda x: x[0]):
            self.band_from.addItem(band_label, band_value)
            self.band_to.addItem(band_label, band_value)

        self.entscheidungsart_filter.addItem("All types", None)
        for item in sorted([value for value in entscheidungsarten if value is not None]):
            self.entscheidungsart_filter.addItem(str(item), item)
        if any(value is None for value in entscheidungsarten):
            self.entscheidungsart_filter.addItem("Unknown", "__unknown__")

        self.sort_combo.addItems(
            ["Relevance", "Document order", "File name", "Section"]
        )

    def _setup_layout(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_button)

        filter_row_bottom = QHBoxLayout()
        filter_row_bottom.addWidget(QLabel("Section"))
        filter_row_bottom.addWidget(self.section_filter)
        filter_row_bottom.addWidget(QLabel("Year from"))
        filter_row_bottom.addWidget(self.year_from)
        filter_row_bottom.addWidget(QLabel("to"))
        filter_row_bottom.addWidget(self.year_to)
        filter_row_bottom.addWidget(QLabel("Year list"))
        filter_row_bottom.addWidget(self.year_list)
        filter_row_bottom.addStretch(1)

        filter_row_bottom.addWidget(QLabel("Band from"))
        filter_row_bottom.addWidget(self.band_from)
        filter_row_bottom.addWidget(QLabel("to"))
        filter_row_bottom.addWidget(self.band_to)
        filter_row_bottom.addWidget(QLabel("Band list"))
        filter_row_bottom.addWidget(self.band_list)
        filter_row_bottom.addStretch(1)
        
        filter_row_type = QHBoxLayout()
        filter_row_type.addWidget(QLabel("Type"))
        filter_row_type.addWidget(self.entscheidungsart_filter)
        filter_row_type.addWidget(QLabel("Sort"))
        filter_row_type.addWidget(self.sort_combo)
        filter_row_type.addStretch(1)
        filter_row_type.addWidget(self.pdf_button)

        layout.addLayout(search_row)
        layout.addWidget(self.search_help)
        layout.addLayout(filter_row_bottom)
        layout.addLayout(filter_row_type)
        layout.addWidget(self.sort_help)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.results_browser, 1)

        self.setCentralWidget(container)

    def _connect_signals(self) -> None:
        self.search_button.clicked.connect(self.start_search)
        self.search_input.returnPressed.connect(self.start_search)
        self.pdf_button.clicked.connect(self.generate_pdf)

    def _parse_int_list(self, text: str, label: str) -> list[int] | None:
        tokens = [token.strip() for token in text.split(",") if token.strip()]
        if not tokens:
            return None
        invalid = [token for token in tokens if not token.isdigit()]
        if invalid:
            raise ValueError(
                f"{label} list has invalid values: {', '.join(invalid)}"
            )
        return [int(token) for token in tokens]

    def start_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            self.summary_label.setText("Enter a search query.")
            return

        section_filter = self.section_filter.currentData()
        year_from = self.year_from.currentData()
        year_to = self.year_to.currentData()
        band_from = self.band_from.currentData()
        band_to = self.band_to.currentData()
        try:
            year_list = self._parse_int_list(self.year_list.text(), "Year")
            band_list = self._parse_int_list(self.band_list.text(), "Band")
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid filter", str(exc))
            return

        if year_list is None:
            if year_from is not None and year_to is not None and year_from > year_to:
                QMessageBox.warning(
                    self,
                    "Invalid year range",
                    "Year from must be less than or equal to year to.",
                )
                return
        else:
            year_from = None
            year_to = None

        if band_list is None:
            if band_from is not None and band_to is not None and band_from > band_to:
                QMessageBox.warning(
                    self,
                    "Invalid band range",
                    "Band from must be less than or equal to band to.",
                )
                return
        else:
            band_from = None
            band_to = None
        entscheidungsart_filter = self.entscheidungsart_filter.currentData()
        sort = self.sort_combo.currentText()
        self.last_query = query
        year_desc = _format_range_list(year_from, year_to, year_list)
        band_desc = _format_range_list(band_from, band_to, band_list)
        self.last_filter_texts = (
            self.section_filter.currentText(),
            year_desc,
            band_desc,
            self.entscheidungsart_filter.currentText(),
        )

        self.search_button.setEnabled(False)
        self.summary_label.setText("Searching...")
        self.results_browser.setHtml("")
        self.pdf_button.setEnabled(False)
        self.last_result = None

        self.thread = QThread()
        thread = cast(QThread, self.thread)
        self.worker = SearchWorker(
            self.db_path,
            query,
            section_filter,
            year_from,
            year_to,
            year_list,
            band_from,
            band_to,
            band_list,
            entscheidungsart_filter,
            sort,
            self.max_results,
        )
        self.worker.moveToThread(thread)

        thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_search_finished)
        self.worker.failed.connect(self._on_search_failed)
        self.worker.finished.connect(thread.quit)
        self.worker.failed.connect(thread.quit)
        thread.finished.connect(self._cleanup_thread)

        thread.start()

    @Slot(SearchResult)
    def _on_search_finished(self, result: SearchResult) -> None:
        self.search_button.setEnabled(True)
        summary = result.summary
        section_bits = ", ".join(
            f"{k}: {v}" for k, v in list(summary.section_counts.items())[:5]
        )
        summary_text = (
            f"Matches: {summary.total_matches} | "
            f"Files: {summary.distinct_files}"
        )
        if section_bits:
            summary_text += f" | Sections: {section_bits}"
        if result.truncated:
            summary_text += f" | Showing first {self.max_results} results"
        self.summary_label.setText(summary_text)

        html = build_results_html(result.results, result.highlight_terms)
        self.results_browser.setHtml(html)
        self.last_result = result
        self.pdf_button.setEnabled(bool(result.results))

    @Slot(str)
    def _on_search_failed(self, message: str) -> None:
        self.search_button.setEnabled(True)
        self.summary_label.setText(f"Search error: {message}")
        self.results_browser.setHtml("")
        self.last_result = None
        self.pdf_button.setEnabled(False)

    @Slot()
    def _cleanup_thread(self) -> None:
        if self.thread is not None:
            self.thread.deleteLater()
        if self.worker is not None:
            self.worker.deleteLater()
        self.thread = None
        self.worker = None

    def generate_pdf(self) -> None:
        if not self.last_result or not self.last_result.results:
            QMessageBox.information(
                self,
                "No results",
                "Run a search before generating a PDF.",
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF",
            "search_results.pdf",
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".pdf"):
            file_path += ".pdf"

        section_text, year_text, band_text, type_text = self.last_filter_texts
        file_map = _build_file_section_map(self.last_result.results)
        if not file_map:
            QMessageBox.warning(
                self,
                "No data",
                "The current results do not contain file/section data to export.",
            )
            return
        html = build_pdf_html(
            self.last_result,
            self.last_query,
            section_text,
            year_text,
            band_text,
            type_text,
        )
        try:
            writer = QPdfWriter(file_path)
            writer.setPageSize(QPageSize(QPageSize.A4))
            writer.setResolution(300)
            writer.setTitle("L.L.Con. Search Results")

            document = QTextDocument()
            document.setPageSize(writer.pageLayout().fullRectPoints().size())
            document.setDefaultFont(QFont("Arial", 10))
            document.setHtml(html)
            document.print_(writer)
        except Exception as exc:
            QMessageBox.critical(self, "PDF failed", str(exc))
            return
        QMessageBox.information(self, "PDF generated", f"Saved to {file_path}")


def build_results_html(records: list[AbsatzRecord], terms: list[str]) -> str:
    if not records:
        return "<div>No results.</div>"

    blocks: list[str] = [
        "<style>"
        ".result { margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #ddd; }"
        ".meta { font-size: 12px; color: #444; margin-bottom: 6px; }"
        ".text { font-size: 14px; }"
        ".hl { background-color: #ffeb99; }"
        "</style>"
    ]

    for record in records:
        meta = _format_meta(record)
        text_html = highlight_text(record.text_raw, terms)
        blocks.append(
            "<div class='result'>"
            f"<div class='meta'>{meta}</div>"
            f"<div class='text'>{text_html}</div>"
            "</div>"
        )
    return "".join(blocks)


def _format_meta(record: AbsatzRecord) -> str:
    section = record.section or "unknown"
    meta_parts = [
        f"File: {escape(record.file_name)}",
        f"Section: {escape(section)}",
    ]

    if record.ebene1_zeichen or record.ebene1_nr:
        ebene1 = record.ebene1_zeichen or record.ebene1_nr or ""
        meta_parts.append(f"Ebene1: {escape(ebene1)}")
    if record.absatz_id:
        meta_parts.append(f"AbsatzID: {escape(record.absatz_id)}")
    if record.rn:
        meta_parts.append(f"Rn: {escape(record.rn)}")
    if record.tbeg:
        meta_parts.append(f"TBEG: {escape(record.tbeg)}")

    return " | ".join(meta_parts)


def _format_range_list(
    value_from: int | None,
    value_to: int | None,
    value_list: list[int] | None,
) -> str:
    if value_list:
        return ", ".join(str(value) for value in value_list)
    if value_from is None and value_to is None:
        return "All"
    if value_from is not None and value_to is not None:
        return f"{value_from}-{value_to}"
    if value_from is not None:
        return f">= {value_from}"
    return f"<= {value_to}"




def build_pdf_html(
    result: SearchResult,
    query: str,
    section_filter: str,
    year_filter: str,
    band_filter: str,
    entscheidungsart_filter: str,
) -> str:
    file_map = _build_file_section_map(result.results)
    rows = []
    for file_name in sorted(file_map.keys()):
        sections = ", ".join(sorted(file_map[file_name]))
        rows.append(
            f"<tr><td>{escape(file_name)}</td><td>{escape(sections)}</td></tr>"
        )

    filters = (
        f"Section: {escape(section_filter)} | "
        f"Year: {escape(year_filter)} | "
        f"Band: {escape(band_filter)} | "
        f"Type: {escape(entscheidungsart_filter)}"
    )

    truncated_note = (
        "<p><em>Note: Results are truncated in the UI.</em></p>"
        if result.truncated
        else ""
    )

    return (
        "<html><head><style>"
        "body { font-family: Arial, sans-serif; font-size: 12px; color: #000; }"
        "table { width: 100%; border-collapse: collapse; }"
        "th, td { border: 1px solid #ccc; padding: 6px; text-align: left; color: #000; }"
        "th { background: #f0f0f0; }"
        "</style></head><body>"
        f"<h2>L.L.Con. Search Results</h2>"
        f"<p><strong>Query:</strong> {escape(query)}</p>"
        f"<p><strong>Filters:</strong> {filters}</p>"
        f"<p><strong>Total matches:</strong> {result.summary.total_matches} | "
        f"<strong>Files:</strong> {result.summary.distinct_files}</p>"
        f"<p><strong>Exported files:</strong> {len(file_map)}</p>"
        f"{truncated_note}"
        "<table>"
        "<thead><tr><th>File name</th><th>Sections</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
        "</body></html>"
    )


def _build_file_section_map(records: list[AbsatzRecord]) -> dict[str, set[str]]:
    file_map: dict[str, set[str]] = {}
    for record in records:
        section = record.section or "unknown"
        file_map.setdefault(record.file_name, set()).add(section)
    return file_map
