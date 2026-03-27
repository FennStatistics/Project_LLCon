from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtCore import QThread
from PySide6.QtCore import Signal
from PySide6.QtCore import Slot
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
        year_filter: int | str | None,
        band_filter: str | None,
        entscheidungsart_filter: str | None,
        sort: str,
        limit: int,
    ) -> None:
        super().__init__()
        self.db_path = db_path
        self.query = query
        self.section_filter = section_filter
        self.year_filter = year_filter
        self.band_filter = band_filter
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
                self.year_filter,
                self.band_filter,
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
        self.search_button = QPushButton("Search")
        self.section_filter = QComboBox()
        self.year_filter = QComboBox()
        self.band_filter = QComboBox()
        self.entscheidungsart_filter = QComboBox()
        self.sort_combo = QComboBox()
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

        self.year_filter.addItem("All years", None)
        years_sorted = sorted([year for year in years if year is not None])
        for year in years_sorted:
            self.year_filter.addItem(str(year), year)
        if any(year is None for year in years):
            self.year_filter.addItem("Unknown", "__unknown__")

        self.band_filter.addItem("All bands", None)
        for band in sorted([value for value in bands if value is not None]):
            self.band_filter.addItem(str(band), band)
        if any(value is None for value in bands):
            self.band_filter.addItem("Unknown", "__unknown__")

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

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Section"))
        filter_row.addWidget(self.section_filter)
        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Year"))
        filter_row.addWidget(self.year_filter)
        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Band"))
        filter_row.addWidget(self.band_filter)
        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Type"))
        filter_row.addWidget(self.entscheidungsart_filter)
        filter_row.addSpacing(12)
        filter_row.addWidget(QLabel("Sort"))
        filter_row.addWidget(self.sort_combo)
        filter_row.addSpacing(12)
        filter_row.addWidget(self.pdf_button)
        filter_row.addStretch(1)

        layout.addLayout(search_row)
        layout.addLayout(filter_row)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.results_browser, 1)

        self.setCentralWidget(container)

    def _connect_signals(self) -> None:
        self.search_button.clicked.connect(self.start_search)
        self.search_input.returnPressed.connect(self.start_search)
        self.pdf_button.clicked.connect(self.generate_pdf)

    def start_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            self.summary_label.setText("Enter a search query.")
            return

        section_filter = self.section_filter.currentData()
        year_filter = self.year_filter.currentData()
        band_filter = self.band_filter.currentData()
        entscheidungsart_filter = self.entscheidungsart_filter.currentData()
        sort = self.sort_combo.currentText()
        self.last_query = query
        self.last_filter_texts = (
            self.section_filter.currentText(),
            self.year_filter.currentText(),
            self.band_filter.currentText(),
            self.entscheidungsart_filter.currentText(),
        )

        self.search_button.setEnabled(False)
        self.summary_label.setText("Searching...")
        self.results_browser.setHtml("")
        self.pdf_button.setEnabled(False)
        self.last_result = None

        self.thread = QThread()
        self.worker = SearchWorker(
            self.db_path,
            query,
            section_filter,
            year_filter,
            band_filter,
            entscheidungsart_filter,
            sort,
            self.max_results,
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_search_finished)
        self.worker.failed.connect(self._on_search_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_thread)

        self.thread.start()

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

        section_text, year_text, band_text, type_text = self.last_filter_texts
        html = build_pdf_html(
            self.last_result,
            self.last_query,
            section_text,
            year_text,
            band_text,
            type_text,
        )

        writer = QPdfWriter(file_path)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setTitle("L.L.Con. Search Results")
        document = QTextDocument()
        document.setHtml(html)
        document.print_(writer)
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


def build_pdf_html(
    result: SearchResult,
    query: str,
    section_filter: str,
    year_filter: str,
    band_filter: str,
    entscheidungsart_filter: str,
) -> str:
    file_map: dict[str, set[str]] = {}
    for record in result.results:
        section = record.section or "unknown"
        file_map.setdefault(record.file_name, set()).add(section)

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
        "body { font-family: Arial, sans-serif; font-size: 12px; }"
        "table { width: 100%; border-collapse: collapse; }"
        "th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }"
        "th { background: #f0f0f0; }"
        "</style></head><body>"
        f"<h2>L.L.Con. Search Results</h2>"
        f"<p><strong>Query:</strong> {escape(query)}</p>"
        f"<p><strong>Filters:</strong> {filters}</p>"
        f"<p><strong>Total matches:</strong> {result.summary.total_matches} | "
        f"<strong>Files:</strong> {result.summary.distinct_files}</p>"
        f"{truncated_note}"
        "<table>"
        "<thead><tr><th>File name</th><th>Sections</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
        "</body></html>"
    )
