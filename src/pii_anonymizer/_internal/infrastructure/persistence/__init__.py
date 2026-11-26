"""Adaptador de persistencia en memoria."""

from __future__ import annotations

from pii_anonymizer._internal.infrastructure.persistence.in_memory_rule_repo import (
    InMemoryRuleRepository,
)

__all__ = ["InMemoryRuleRepository"]
