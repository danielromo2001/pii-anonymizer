"""Repositorio en memoria de reglas de anonimización."""

from __future__ import annotations

from pii_anonymizer._internal.application.ports import RuleRepository
from pii_anonymizer._internal.domain.models import AnonymizationRule


class InMemoryRuleRepository(RuleRepository):
    """Gestiona reglas en un diccionario indexado por ``rule_id``.

    El orden de inserción se conserva para que el reporte de auditoría y la
    resolución de reglas sean deterministas. Reemplazar una regla existente
    actualiza su valor sin alterar su posición.
    """

    def __init__(self) -> None:
        """Crea un repositorio vacío con orden de inserción preservado."""
        self._rules: dict[str, AnonymizationRule] = {}

    def save(self, rule: AnonymizationRule) -> None:
        """Inserta o reemplaza la regla identificada por ``rule.rule_id``."""
        self._rules[rule.rule_id] = rule

    def get_all(self) -> list[AnonymizationRule]:
        """Retorna una copia de la lista de reglas en orden de registro."""
        return list(self._rules.values())

    def find_by_field(self, field_name: str) -> AnonymizationRule | None:
        """Busca la primera regla que declare ``field_name``.

        La comparación ignora mayúsculas y espacios en los extremos.

        Args:
            field_name: Nombre de campo a buscar.

        Returns:
            La regla coincidente o ``None`` si no existe.
        """
        normalized = field_name.strip().casefold()
        for rule in self._rules.values():
            if any(name.casefold() == normalized for name in rule.field_names):
                return rule
        return None

    def get_detector_rules(self) -> list[AnonymizationRule]:
        """Retorna las reglas que poseen un detector de patrones."""
        return [rule for rule in self._rules.values() if rule.detector is not None]
