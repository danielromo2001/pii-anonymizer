"""Frontera pública y Composition Root de ``pii_anonymizer``.

Este paquete reexporta únicamente contratos estables. Es el único punto de
entrada permitido para aplicaciones, pruebas y extensiones de terceros.
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
from pii_anonymizer._internal.application.ports import PiiAnonymizer
from pii_anonymizer.api.builder import AnonymizerBuilder

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
