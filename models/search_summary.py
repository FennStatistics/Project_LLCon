from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchSummary:
    total_matches: int
    distinct_files: int
    section_counts: dict[str, int]
