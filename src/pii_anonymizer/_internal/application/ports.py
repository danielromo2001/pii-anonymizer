"""Puertos primario y secundarios de la capa de aplicación."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pii_anonymizer._internal.domain.models import (
    AnonymizationRule,
    ComplianceReport,
)


class PiiAnonymizer(ABC):
    """Puerto primario que expone las cuatro capacidades esenciales.

    Es el contrato que consume la aplicación cliente. La fachada
    ``DefaultPiiAnonymizer`` lo implementa delegando en casos de uso.
    """

    @abstractmethod
    def anonymize_map(self, data: dict[str, Any]) -> dict[str, Any]:
        """Retorna una copia sanitizada de ``data`` sin mutar la entrada.

        Args:
            data: Diccionario potencialmente anidado con PII.

        Returns:
            Nueva estructura con los valores sensibles enmascarados.
        """

    @abstractmethod
    def anonymize_text(self, raw_text: str) -> str:
        """Enmascara todas las coincidencias PII encontradas en ``raw_text``.

        Args:
            raw_text: Texto plano, por ejemplo una línea de *log*.

        Returns:
            Texto sanitizado.
        """

    @abstractmethod
    def register_rule(self, rule: AnonymizationRule) -> None:
        """Registra o reemplaza una regla de anonimización.

        Args:
            rule: Regla validada que se persistirá en el repositorio.

        Raises:
            InvalidRuleError: Si la regla no cumple las invariantes del dominio.
        """

    @abstractmethod
    def audit_compliance(self, data: dict[str, Any]) -> ComplianceReport:
        """Analiza ``data`` y retorna metadatos agregados de cumplimiento.

        Args:
            data: Diccionario potencialmente anidado con PII.

        Returns:
            Reporte sin valores sensibles.
        """


class RuleRepository(ABC):
    """Puerto secundario para persistir reglas en memoria."""

    @abstractmethod
    def save(self, rule: AnonymizationRule) -> None:
        """Inserta o actualiza una regla identificada por ``rule_id``."""

    @abstractmethod
    def get_all(self) -> list[AnonymizationRule]:
        """Retorna todas las reglas en orden de registro."""

    @abstractmethod
    def find_by_field(self, field_name: str) -> AnonymizationRule | None:
        """Busca la regla asociada a un nombre de campo (sin distinguir mayúsculas)."""

    @abstractmethod
    def get_detector_rules(self) -> list[AnonymizationRule]:
        """Retorna únicamente las reglas que declaran un detector."""


class StructureTraverser(ABC):
    """Puerto secundario para recorrer y sanitizar estructuras anidadas."""

    @abstractmethod
    def traverse(
        self,
        data: dict[str, Any],
        rules: list[AnonymizationRule],
    ) -> tuple[dict[str, Any], ComplianceReport]:
        """Recorre ``data`` aplicando ``rules`` y construye un reporte.

        Args:
            data: Estructura de entrada que no debe mutarse.
            rules: Reglas activas que se aplicarán durante el recorrido.

        Returns:
            Tupla ``(copia_sanitizada, reporte)``.
        """
