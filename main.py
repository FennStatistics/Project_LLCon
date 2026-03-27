from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from ui.main_window import MainWindow


def main() -> None:
    db_path = Path("data_processed/corpus.sqlite")
    app = QApplication(sys.argv)

    if not db_path.exists():
        QMessageBox.critical(
            None,
            "Database not found",
            "The preprocessed database was not found.\n"
            "Run notebooks/prepare_corpus.ipynb to generate data_processed/corpus.sqlite.",
        )
        sys.exit(1)

    window = MainWindow(db_path)
    window.resize(1100, 800)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
