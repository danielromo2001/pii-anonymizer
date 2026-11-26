"""Capa de dominio del componente ``pii_anonymizer``.

El núcleo no importa módulos de ``application``, ``infrastructure`` ni
``api``, y tampoco depende de librerías de terceros.
"""

from __future__ import annotations

from pii_anonymizer._internal.domain.exceptions import (
    AnonymizerError,
    InvalidRuleError,
)
from pii_anonymizer._internal.domain.models import (
    AnonymizationRule,
    ComplianceReport,
    TextMatch,
)
from pii_anonymizer._internal.domain.ports import (
    MaskingStrategy,
    SaltProvider,
    SensitivePatternDetector,
)

__all__ = [
    "AnonymizationRule",
    "AnonymizerError",
    "ComplianceReport",
    "InvalidRuleError",
    "MaskingStrategy",
    "SaltProvider",
    "SensitivePatternDetector",
    "TextMatch",
]
