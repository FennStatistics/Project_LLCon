from __future__ import annotations

from search.ast import AndNode
from search.ast import Node
from search.ast import NotNode
from search.ast import OrNode
from search.ast import ProxNode
from search.ast import TermNode


def build_fts_query(node: Node) -> str:
    if isinstance(node, TermNode):
        return _quote_term(node.value)
    if isinstance(node, AndNode):
        return f"({build_fts_query(node.left)} AND {build_fts_query(node.right)})"
    if isinstance(node, OrNode):
        return f"({build_fts_query(node.left)} OR {build_fts_query(node.right)})"
    if isinstance(node, NotNode):
        return f"(NOT {build_fts_query(node.operand)})"
    if isinstance(node, ProxNode):
        left = build_fts_query(node.left)
        right = build_fts_query(node.right)
        return f"({left} AND {right})"
    raise TypeError("Unsupported node type")


def collect_positive_terms(node: Node, negated: bool = False) -> list[str]:
    if isinstance(node, TermNode):
        if negated:
            return []
        return [_normalize_highlight_term(node.value)]
    if isinstance(node, NotNode):
        return collect_positive_terms(node.operand, True)
    if isinstance(node, AndNode) or isinstance(node, OrNode) or isinstance(node, ProxNode):
        terms: list[str] = []
        terms.extend(collect_positive_terms(node.left, negated))
        terms.extend(collect_positive_terms(node.right, negated))
        return terms
    return []


def _quote_term(term: str) -> str:
    if term.endswith("*"):
        return term
    safe = term.replace('"', '""')
    return f'"{safe}"'


def _normalize_highlight_term(term: str) -> str:
    if term.endswith("*"):
        return term[:-1]
    return term
