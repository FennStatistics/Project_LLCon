from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from models.absatz import AbsatzRecord
from models.search_summary import SearchSummary
from search.ast import Node
from search.fts_builder import build_fts_query
from search.fts_builder import collect_positive_terms
from search.evaluator import collect_terms
from search.evaluator import evaluate
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
        year_from: int | None,
        year_to: int | None,
        year_list: list[int] | None,
        band_from: int | None,
        band_to: int | None,
        band_list: list[int] | None,
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
        eval_terms = collect_terms(ast)

        results = self._fetch_results(
            fts_query,
            ast,
            eval_terms,
            section_filter,
            year_from,
            year_to,
            year_list,
            band_from,
            band_to,
            band_list,
            entscheidungsart_filter,
            sort,
            limit,
        )
        summary = self._fetch_summary(
            fts_query,
            ast,
            eval_terms,
            section_filter,
            year_from,
            year_to,
            year_list,
            band_from,
            band_to,
            band_list,
            entscheidungsart_filter,
        )

        return SearchResult(
            summary=summary,
            results=results,
            highlight_terms=highlight_terms,
            truncated=summary.total_matches > limit,
        )

    def _fetch_results(
        self,
        fts_query: str,
        ast: Node,
        eval_terms: list[str],
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
    ) -> list[AbsatzRecord]:
        clause, params = _filter_clause(
            section_filter,
            year_from,
            year_to,
            year_list,
            band_from,
            band_to,
            band_list,
            entscheidungsart_filter,
        )

        order_by = _order_by_clause(sort)
        sql_base = (
            "SELECT absatz.id, file_name, section, section_path, absatz_id, rn, tbeg, "
            "absatz_ebene1nr, absatz_ebene1zeichen, ebene1_nr, ebene1_zeichen, "
            "ebene1_tbeg, year, band, entscheidungsart, text_raw, absatz.text_norm, "
            "bm25(absatz_fts) as rank "
            "FROM absatz_fts JOIN absatz ON absatz_fts.rowid = absatz.id "
            "WHERE absatz_fts MATCH ? "
            + clause
            + " "
            + order_by
        )
        batch_size = 1000
        offset = 0
        matched_rows: list[sqlite3.Row] = []
        while len(matched_rows) < limit:
            rows = self.conn.execute(
                sql_base + " LIMIT ? OFFSET ?",
                [fts_query, *params, batch_size, offset],
            ).fetchall()
            if not rows:
                break
            for row in rows:
                if evaluate(ast, row["text_norm"], eval_terms):
                    matched_rows.append(row)
                    if len(matched_rows) >= limit:
                        break
            offset += len(rows)
            if len(rows) < batch_size:
                break

        return [AbsatzRecord.from_row(row) for row in matched_rows]

    def _fetch_summary(
        self,
        fts_query: str,
        ast: Node,
        eval_terms: list[str],
        section_filter: str | None,
        year_from: int | None,
        year_to: int | None,
        year_list: list[int] | None,
        band_from: int | None,
        band_to: int | None,
        band_list: list[int] | None,
        entscheidungsart_filter: str | None,
    ) -> SearchSummary:
        clause, params = _filter_clause(
            section_filter,
            year_from,
            year_to,
            year_list,
            band_from,
            band_to,
            band_list,
            entscheidungsart_filter,
        )
        base_sql = (
            "FROM absatz_fts JOIN absatz ON absatz_fts.rowid = absatz.id "
            "WHERE absatz_fts MATCH ? "
            + clause
        )
        cursor = self.conn.execute(
            "SELECT file_name, section, absatz.text_norm " + base_sql,
            [fts_query, *params],
        )
        total_matches = 0
        file_hits: set[str] = set()
        section_counts: dict[str, int] = {}
        for row in cursor:
            if not evaluate(ast, row["text_norm"], eval_terms):
                continue
            total_matches += 1
            file_hits.add(row["file_name"])
            key = row["section"] if row["section"] is not None else "unknown"
            section_counts[key] = section_counts.get(key, 0) + 1

        return SearchSummary(
            total_matches=total_matches,
            distinct_files=len(file_hits),
            section_counts=section_counts,
        )


def _filter_clause(
    section_filter: str | None,
    year_from: int | None,
    year_to: int | None,
    year_list: list[int] | None,
    band_from: int | None,
    band_to: int | None,
    band_list: list[int] | None,
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

    if year_list:
        placeholders = ", ".join(["?"] * len(year_list))
        clauses.append(f"absatz.year IN ({placeholders})")
        params.extend(year_list)
    else:
        if year_from is not None:
            clauses.append("absatz.year >= ?")
            params.append(year_from)
        if year_to is not None:
            clauses.append("absatz.year <= ?")
            params.append(year_to)

    if band_list:
        placeholders = ", ".join(["?"] * len(band_list))
        clauses.append(f"CAST(absatz.band AS INTEGER) IN ({placeholders})")
        params.extend(band_list)
    else:
        if band_from is not None:
            clauses.append("CAST(absatz.band AS INTEGER) >= ?")
            params.append(band_from)
        if band_to is not None:
            clauses.append("CAST(absatz.band AS INTEGER) <= ?")
            params.append(band_to)

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
