"""Caso de uso: anonimizar texto plano."""

from __future__ import annotations

from pii_anonymizer._internal.application.ports import RuleRepository
from pii_anonymizer._internal.application.services.detector_chain import (
    DetectorChain,
)


class AnonymizeTextUseCase:
    """Construye la cadena de detectores y sanitiza el texto recibido."""

    def __init__(self, rule_repository: RuleRepository) -> None:
        """Inyecta el repositorio del que se obtienen las reglas con detector.

        Args:
            rule_repository: Fuente de las reglas activas.
        """
        self._rule_repository = rule_repository

    def execute(self, raw_text: str) -> str:
        """Enmascara las coincidencias PII presentes en ``raw_text``.

        Args:
            raw_text: Texto plano, típicamente una traza de *log*.

        Returns:
            Texto con las coincidencias reemplazadas por su versión
            enmascarada.
        """
        rules = self._rule_repository.get_detector_rules()
        return DetectorChain(rules).apply(raw_text)
