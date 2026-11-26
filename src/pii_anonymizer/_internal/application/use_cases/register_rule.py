"""Caso de uso: registrar o reemplazar una regla de anonimización."""

from __future__ import annotations

from pii_anonymizer._internal.application.ports import RuleRepository
from pii_anonymizer._internal.domain.exceptions import InvalidRuleError
from pii_anonymizer._internal.domain.models import AnonymizationRule


class RegisterRuleUseCase:
    """Valida el contrato de la regla y la persiste en el repositorio."""

    def __init__(self, rule_repository: RuleRepository) -> None:
        """Inyecta el repositorio donde se persistirán las reglas.

        Args:
            rule_repository: Destino de las reglas registradas.
        """
        self._rule_repository = rule_repository

    def execute(self, rule: AnonymizationRule) -> None:
        """Registra ``rule``, reemplazando una existente con el mismo ``rule_id``.

        Args:
            rule: Regla de dominio ya construida.

        Raises:
            InvalidRuleError: Si ``rule`` no es una instancia de
                :class:`AnonymizationRule`.
        """
        if not isinstance(rule, AnonymizationRule):
            raise InvalidRuleError(
                "register_rule espera una instancia de AnonymizationRule."
            )
        self._rule_repository.save(rule)
