"""Caso de uso: anonimizar un diccionario potencialmente anidado."""

from __future__ import annotations

from typing import Any

from pii_anonymizer._internal.application.ports import (
    RuleRepository,
    StructureTraverser,
)


class AnonymizeMapUseCase:
    """Obtiene las reglas activas y delega el recorrido de la estructura.

    La entrada nunca se muta: el recorrido compone estructuras nuevas.
    """

    def __init__(
        self,
        rule_repository: RuleRepository,
        traverser: StructureTraverser,
    ) -> None:
        """Inyecta el repositorio de reglas y el recorredor de estructuras.

        Args:
            rule_repository: Fuente de las reglas activas.
            traverser: Adaptador que recorre y sanitiza la estructura.
        """
        self._rule_repository = rule_repository
        self._traverser = traverser

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """Retorna una copia sanitizada de ``data``.

        Args:
            data: Diccionario de entrada, posiblemente con listas y
                diccionarios anidados.

        Returns:
            Nueva estructura sanitizada.
        """
        rules = self._rule_repository.get_all()
        sanitized, _ = self._traverser.traverse(data, rules)
        return sanitized
