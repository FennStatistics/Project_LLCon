from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from models.absatz import AbsatzRecord
from models.search_summary import SearchSummary
from search.fts_builder import build_fts_query
from search.fts_builder import collect_positive_terms
from search.query_parser import QueryParser
from search.query_parser import QueryParseError


@dataclass(frozen=True)
class SearchResult:
    summary: SearchSummary
    results: list[AbsatzRecord]
    highlight_terms: list[str]
    truncated: bool


class SearchServiceError(RuntimeError):
    pass


class SearchService:
    def __init__(self, db_path: Path) -> None:
        if not db_path.exists():
            raise SearchServiceError(f"Database not found: {db_path}")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def get_sections(self) -> list[str | None]:
        rows = self.conn.execute(
            "SELECT DISTINCT section FROM absatz ORDER BY section"
        ).fetchall()
        return [row["section"] for row in rows]

    def get_years(self) -> list[int | None]:
        rows = self.conn.execute(
            "SELECT DISTINCT year FROM absatz ORDER BY year"
        ).fetchall()
        return [row["year"] for row in rows]

    def get_bands(self) -> list[str | None]:
        rows = self.conn.execute(
            "SELECT DISTINCT band FROM absatz ORDER BY band"
        ).fetchall()
        return [row["band"] for row in rows]

    def get_entscheidungsarten(self) -> list[str | None]:
        rows = self.conn.execute(
            "SELECT DISTINCT entscheidungsart FROM absatz ORDER BY entscheidungsart"
        ).fetchall()
        return [row["entscheidungsart"] for row in rows]

    def search(
        self,
        query: str,
        section_filter: str | None,
        year_filter: int | str | None,
        band_filter: str | None,
        entscheidungsart_filter: str | None,
        sort: str,
        limit: int,
    ) -> SearchResult:
        try:
            ast = QueryParser(query).parse()
        except QueryParseError as exc:
            raise SearchServiceError(str(exc)) from exc

        fts_query = build_fts_query(ast)
        highlight_terms = collect_positive_terms(ast)

        results, truncated = self._fetch_results(
            fts_query,
            section_filter,
            year_filter,
            band_filter,
            entscheidungsart_filter,
            sort,
            limit,
        )
        summary = self._fetch_summary(
            fts_query, section_filter, year_filter, band_filter, entscheidungsart_filter
        )

        return SearchResult(
            summary=summary,
            results=results,
            highlight_terms=highlight_terms,
            truncated=truncated,
        )

    def _fetch_results(
        self,
        fts_query: str,
        section_filter: str | None,
        year_filter: int | str | None,
        band_filter: str | None,
        entscheidungsart_filter: str | None,
        sort: str,
        limit: int,
    ) -> tuple[list[AbsatzRecord], bool]:
        clause, params = _filter_clause(
            section_filter, year_filter, band_filter, entscheidungsart_filter
        )

        order_by = _order_by_clause(sort)
        sql = (
            "SELECT absatz.id, file_name, section, section_path, absatz_id, rn, tbeg, "
            "absatz_ebene1nr, absatz_ebene1zeichen, ebene1_nr, ebene1_zeichen, "
            "ebene1_tbeg, year, band, entscheidungsart, text_raw, "
            "bm25(absatz_fts) as rank "
            "FROM absatz_fts JOIN absatz ON absatz_fts.rowid = absatz.id "
            "WHERE absatz_fts MATCH ? "
            + clause
            + " "
            + order_by
            + " LIMIT ?"
        )

        rows = self.conn.execute(sql, [fts_query, *params, limit + 1]).fetchall()
        truncated = len(rows) > limit
        if truncated:
            rows = rows[:limit]
        return [AbsatzRecord.from_row(row) for row in rows], truncated

    def _fetch_summary(
        self,
        fts_query: str,
        section_filter: str | None,
        year_filter: int | str | None,
        band_filter: str | None,
        entscheidungsart_filter: str | None,
    ) -> SearchSummary:
        clause, params = _filter_clause(
            section_filter, year_filter, band_filter, entscheidungsart_filter
        )
        base_sql = (
            "FROM absatz_fts JOIN absatz ON absatz_fts.rowid = absatz.id "
            "WHERE absatz_fts MATCH ? "
            + clause
        )

        totals = self.conn.execute(
            "SELECT COUNT(*) as total, COUNT(DISTINCT file_name) as files "
            + base_sql,
            [fts_query, *params],
        ).fetchone()

        section_rows = self.conn.execute(
            "SELECT section, COUNT(*) as count "
            + base_sql
            + " GROUP BY section ORDER BY count DESC",
            [fts_query, *params],
        ).fetchall()

        section_counts: dict[str, int] = {}
        for row in section_rows:
            key = row["section"] if row["section"] is not None else "unknown"
            section_counts[key] = row["count"]

        return SearchSummary(
            total_matches=int(totals["total"]),
            distinct_files=int(totals["files"]),
            section_counts=section_counts,
        )


def _filter_clause(
    section_filter: str | None,
    year_filter: int | str | None,
    band_filter: str | None,
    entscheidungsart_filter: str | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []

    if section_filter is not None:
        if section_filter == "__unknown__":
            clauses.append("absatz.section IS NULL")
        else:
            clauses.append("absatz.section = ?")
            params.append(section_filter)

    if year_filter is not None:
        if year_filter == "__unknown__":
            clauses.append("absatz.year IS NULL")
        else:
            clauses.append("absatz.year = ?")
            params.append(year_filter)

    if band_filter is not None:
        if band_filter == "__unknown__":
            clauses.append("absatz.band IS NULL")
        else:
            clauses.append("absatz.band = ?")
            params.append(band_filter)

    if entscheidungsart_filter is not None:
        if entscheidungsart_filter == "__unknown__":
            clauses.append("absatz.entscheidungsart IS NULL")
        else:
            clauses.append("absatz.entscheidungsart = ?")
            params.append(entscheidungsart_filter)

    if not clauses:
        return "", []
    return " AND " + " AND ".join(clauses), params


def _order_by_clause(sort: str) -> str:
    if sort == "Relevance":
        return "ORDER BY rank, absatz.id"
    if sort == "File name":
        return "ORDER BY file_name, absatz.id"
    if sort == "Section":
        return "ORDER BY section, file_name, absatz.id"
    return "ORDER BY absatz.id"
