from __future__ import annotations

from html import escape
import re


def highlight_text(text: str, terms: list[str]) -> str:
    escaped = escape(text)
    clean_terms = [t for t in terms if t]
    if not clean_terms:
        return escaped

    unique_terms = sorted(set(clean_terms), key=len, reverse=True)
    pattern = re.compile(
        "(" + "|".join(re.escape(term) for term in unique_terms) + ")",
        re.IGNORECASE,
    )
    return pattern.sub(r'<span class="hl">\1</span>', escaped)
