"""Fachada de aplicación que implementa el puerto primario."""

from __future__ import annotations

from typing import Any

from pii_anonymizer._internal.application.ports import PiiAnonymizer
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
from pii_anonymizer._internal.domain.models import (
    AnonymizationRule,
    ComplianceReport,
)


class DefaultPiiAnonymizer(PiiAnonymizer):
    """Facade/Controller que delega cada operación en su caso de uso.

    La fachada no contiene lógica de negocio: solo traduce la llamada del
    cliente al caso de uso responsable, manteniendo bajo acoplamiento y alta
    cohesión.
    """

    def __init__(
        self,
        anonymize_map_use_case: AnonymizeMapUseCase,
        anonymize_text_use_case: AnonymizeTextUseCase,
        register_rule_use_case: RegisterRuleUseCase,
        audit_compliance_use_case: AuditComplianceUseCase,
    ) -> None:
        """Inyecta los cuatro casos de uso que atiende la fachada.

        Args:
            anonymize_map_use_case: Caso de uso para estructuras anidadas.
            anonymize_text_use_case: Caso de uso para texto plano.
            register_rule_use_case: Caso de uso de alta de reglas.
            audit_compliance_use_case: Caso de uso de auditoría.
        """
        self._anonymize_map_use_case = anonymize_map_use_case
        self._anonymize_text_use_case = anonymize_text_use_case
        self._register_rule_use_case = register_rule_use_case
        self._audit_compliance_use_case = audit_compliance_use_case

    def anonymize_map(self, data: dict[str, Any]) -> dict[str, Any]:
        """Delega la anonimización de estructuras en su caso de uso."""
        return self._anonymize_map_use_case.execute(data)

    def anonymize_text(self, raw_text: str) -> str:
        """Delega la anonimización de texto en su caso de uso."""
        return self._anonymize_text_use_case.execute(raw_text)

    def register_rule(self, rule: AnonymizationRule) -> None:
        """Delega el registro de reglas en su caso de uso."""
        self._register_rule_use_case.execute(rule)

    def audit_compliance(self, data: dict[str, Any]) -> ComplianceReport:
        """Delega la auditoría en su caso de uso."""
        return self._audit_compliance_use_case.execute(data)
