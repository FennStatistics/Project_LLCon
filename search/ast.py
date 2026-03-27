from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TermNode:
    value: str


@dataclass(frozen=True)
class AndNode:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class OrNode:
    left: "Node"
    right: "Node"


@dataclass(frozen=True)
class NotNode:
    operand: "Node"


@dataclass(frozen=True)
class ProxNode:
    left: "Node"
    right: "Node"
    distance: int


Node = TermNode | AndNode | OrNode | NotNode | ProxNode
