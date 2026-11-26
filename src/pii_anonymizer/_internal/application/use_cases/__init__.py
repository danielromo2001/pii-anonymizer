"""Casos de uso de la capa de aplicación."""

from __future__ import annotations

from pii_anonymizer._internal.application.use_cases.anonymize_map import (
    AnonymizeMapUseCase,
)
from pii_anonymizer._internal.application.use_cases.anonymize_text import (
    AnonymizeTextUseCase,
)
from pii_anonymizer._internal.application.use_cases.audit_compliance import (
    AuditComplianceUseCase,
)
from pii_anonymizer._internal.application.use_cases.register_rule import (
    RegisterRuleUseCase,
)

__all__ = [
    "AnonymizeMapUseCase",
    "AnonymizeTextUseCase",
    "AuditComplianceUseCase",
    "RegisterRuleUseCase",
]
