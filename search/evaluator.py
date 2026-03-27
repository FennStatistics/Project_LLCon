from __future__ import annotations

from dataclasses import dataclass
import re

from search.ast import AndNode
from search.ast import Node
from search.ast import NotNode
from search.ast import OrNode
from search.ast import ProxNode
from search.ast import TermNode


TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True)
class EvaluationContext:
    tokens: list[str]
    positions: dict[str, list[int]]


def evaluate(node: Node, text: str, terms: list[str]) -> bool:
    tokens = tokenize(text)
    if not tokens:
        return _evaluate_empty(node)
    positions = build_positions(tokens, terms)
    context = EvaluationContext(tokens=tokens, positions=positions)
    return _evaluate(node, context)


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def collect_terms(node: Node) -> list[str]:
    if isinstance(node, TermNode):
        return [node.value]
    if isinstance(node, NotNode):
        return collect_terms(node.operand)
    if isinstance(node, AndNode) or isinstance(node, OrNode) or isinstance(node, ProxNode):
        terms: list[str] = []
        terms.extend(collect_terms(node.left))
        terms.extend(collect_terms(node.right))
        return terms
    return []


def build_positions(tokens: list[str], terms: list[str]) -> dict[str, list[int]]:
    positions: dict[str, list[int]] = {term: [] for term in terms}
    unique_terms = sorted(set(terms))
    for term in unique_terms:
        if term.endswith("*"):
            prefix = term[:-1]
            positions[term] = [
                index for index, token in enumerate(tokens) if token.startswith(prefix)
            ]
        else:
            positions[term] = [
                index for index, token in enumerate(tokens) if token == term
            ]
    return positions


def _evaluate(node: Node, context: EvaluationContext) -> bool:
    if isinstance(node, TermNode):
        return bool(context.positions.get(node.value))
    if isinstance(node, NotNode):
        return not _evaluate(node.operand, context)
    if isinstance(node, AndNode):
        return _evaluate(node.left, context) and _evaluate(node.right, context)
    if isinstance(node, OrNode):
        return _evaluate(node.left, context) or _evaluate(node.right, context)
    if isinstance(node, ProxNode):
        if not _evaluate(node.left, context) or not _evaluate(node.right, context):
            return False
        left_positions = _positions_for_node(node.left, context)
        right_positions = _positions_for_node(node.right, context)
        if not left_positions or not right_positions:
            return False
        return _within_distance(left_positions, right_positions, node.distance)
    return False


def _positions_for_node(node: Node, context: EvaluationContext) -> list[int]:
    if isinstance(node, TermNode):
        return context.positions.get(node.value, [])
    if isinstance(node, NotNode):
        return []
    if isinstance(node, AndNode) or isinstance(node, OrNode) or isinstance(node, ProxNode):
        combined: list[int] = []
        combined.extend(_positions_for_node(node.left, context))
        combined.extend(_positions_for_node(node.right, context))
        return sorted(set(combined))
    return []


def _within_distance(
    left_positions: list[int], right_positions: list[int], distance: int
) -> bool:
    left_positions = sorted(left_positions)
    right_positions = sorted(right_positions)
    left_index = 0
    right_index = 0
    while left_index < len(left_positions) and right_index < len(right_positions):
        left_pos = left_positions[left_index]
        right_pos = right_positions[right_index]
        if abs(left_pos - right_pos) <= distance:
            return True
        if left_pos < right_pos:
            left_index += 1
        else:
            right_index += 1
    return False


def _evaluate_empty(node: Node) -> bool:
    if isinstance(node, TermNode):
        return False
    if isinstance(node, NotNode):
        return True
    if isinstance(node, AndNode):
        return _evaluate_empty(node.left) and _evaluate_empty(node.right)
    if isinstance(node, OrNode):
        return _evaluate_empty(node.left) or _evaluate_empty(node.right)
    if isinstance(node, ProxNode):
        return False
    return False
