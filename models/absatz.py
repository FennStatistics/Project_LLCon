from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AbsatzRecord:
    id: int
    file_name: str
    section: str | None
    section_path: str | None
    absatz_id: str | None
    rn: str | None
    tbeg: str | None
    absatz_ebene1nr: str | None
    absatz_ebene1zeichen: str | None
    ebene1_nr: str | None
    ebene1_zeichen: str | None
    ebene1_tbeg: str | None
    year: int | None
    band: str | None
    entscheidungsart: str | None
    text_raw: str

    @classmethod
    def from_row(cls, row: Any) -> "AbsatzRecord":
        return cls(
            id=row["id"],
            file_name=row["file_name"],
            section=row["section"],
            section_path=row["section_path"],
            absatz_id=row["absatz_id"],
            rn=row["rn"],
            tbeg=row["tbeg"],
            absatz_ebene1nr=row["absatz_ebene1nr"],
            absatz_ebene1zeichen=row["absatz_ebene1zeichen"],
            ebene1_nr=row["ebene1_nr"],
            ebene1_zeichen=row["ebene1_zeichen"],
            ebene1_tbeg=row["ebene1_tbeg"],
            year=row["year"],
            band=row["band"],
            entscheidungsart=row["entscheidungsart"],
            text_raw=row["text_raw"],
        )
