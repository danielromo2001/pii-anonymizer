"""Caso de uso: auditar el cumplimiento de anonimización de una estructura."""

from __future__ import annotations

from typing import Any

from pii_anonymizer._internal.application.ports import (
    RuleRepository,
    StructureTraverser,
)
from pii_anonymizer._internal.domain.models import ComplianceReport


class AuditComplianceUseCase:
    """Recorre la estructura y retorna únicamente el reporte agregado.

    El diccionario sanitizado se descarta para que ningún valor sensible
    pueda filtrarse a través de este caso de uso.
    """

    def __init__(
        self,
        rule_repository: RuleRepository,
        traverser: StructureTraverser,
    ) -> None:
        """Inyecta el repositorio de reglas y el recorredor de estructuras.

        Args:
            rule_repository: Fuente de las reglas activas.
            traverser: Adaptador que recorre y contabiliza los datos.
        """
        self._rule_repository = rule_repository
        self._traverser = traverser

    def execute(self, data: dict[str, Any]) -> ComplianceReport:
        """Analiza ``data`` sin mutarlo y retorna el reporte de cumplimiento.

        Args:
            data: Diccionario de entrada a auditar.

        Returns:
            Reporte con conteos y reglas aplicadas, sin valores PII.
        """
        rules = self._rule_repository.get_all()
        _, report = self._traverser.traverse(data, rules)
        return report
