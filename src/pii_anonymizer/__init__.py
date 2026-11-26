"""``pii_anonymizer``: detección, enmascaramiento y auditoría de PII.

La totalidad de la API pública se reexporta desde :mod:`pii_anonymizer.api`.
La implementación interna vive en ``pii_anonymizer._internal`` y no forma
parte del contrato de compatibilidad.
"""

from __future__ import annotations

from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    AnonymizerError,
    ComplianceReport,
    InvalidRuleError,
    MaskingStrategy,
    PiiAnonymizer,
    SaltProvider,
    SensitivePatternDetector,
    TextMatch,
)

__version__ = "1.0.0"

__all__ = [
    "AnonymizerBuilder",
    "AnonymizerError",
    "AnonymizationRule",
    "ComplianceReport",
    "InvalidRuleError",
    "MaskingStrategy",
    "PiiAnonymizer",
    "SaltProvider",
    "SensitivePatternDetector",
    "TextMatch",
]
