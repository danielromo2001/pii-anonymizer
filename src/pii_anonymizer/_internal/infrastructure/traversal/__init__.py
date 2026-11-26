"""Recorrido de estructuras con el patrón Composite."""

from __future__ import annotations

from pii_anonymizer._internal.infrastructure.traversal.composite import (
    CompositeStructureTraverser,
    DataNode,
    DictNode,
    ListNode,
    ScalarNode,
    TraversalContext,
)

__all__ = [
    "CompositeStructureTraverser",
    "DataNode",
    "DictNode",
    "ListNode",
    "ScalarNode",
    "TraversalContext",
]
