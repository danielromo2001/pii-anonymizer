"""Estrategias concretas de enmascaramiento."""

from __future__ import annotations

from pii_anonymizer._internal.infrastructure.strategies.hashing import (
    HashMaskStrategy,
)
from pii_anonymizer._internal.infrastructure.strategies.partial import (
    PartialMaskStrategy,
)
from pii_anonymizer._internal.infrastructure.strategies.salt import (
    RandomSaltProvider,
)

__all__ = ["HashMaskStrategy", "PartialMaskStrategy", "RandomSaltProvider"]
