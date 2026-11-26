"""Integración de la app con la API pública de ``pii-anonymizer``."""

from __future__ import annotations

import re
from typing import Any

from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    ComplianceReport,
    MaskingStrategy,
    SensitivePatternDetector,
    TextMatch,
)


class RedactionTagStrategy(MaskingStrategy):
    """Reemplaza cualquier valor por una etiqueta fija."""

    def __init__(self, tag: str = "[OCULTO]") -> None:
        """Inicializa la estrategia.

        Args:
            tag: Texto que reemplazará el valor original.
        """
        self._tag = tag

    def mask(self, raw_value: str) -> str:
        """Retorna la etiqueta de redacción sin exponer ``raw_value``.

        Args:
            raw_value: Valor original.

        Returns:
            Etiqueta fija configurada.
        """
        return self._tag


class PhoneNumberDetector(SensitivePatternDetector):
    """Detecta teléfonos móviles colombianos en texto libre."""

    _PATTERN = re.compile(
        r"(?<!\d)(?:\+57[\s.-]?)?3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
    )

    @property
    def category(self) -> str:
        """Categoría reportada por el detector."""
        return "PHONE"

    def detect(self, text: str) -> list[TextMatch]:
        """Busca teléfonos en ``text``.

        Args:
            text: Texto plano a analizar.

        Returns:
            Coincidencias con índices absolutos sobre ``text``.
        """
        return [
            TextMatch(
                category=self.category,
                start=match.start(),
                end=match.end(),
                matched_text=match.group(0),
            )
            for match in self._PATTERN.finditer(text)
        ]


class WorkshopPiiService:
    """Configura la librería y expone las operaciones usadas por la app."""

    def __init__(self) -> None:
        """Construye un anonimizador con reglas por defecto y reglas del taller."""
        self._anonymizer = (
            AnonymizerBuilder()
            .with_default_rules()
            .add_rule(
                AnonymizationRule(
                    rule_id="phone",
                    strategy=AnonymizerBuilder.partial_mask_strategy(3, 2),
                    field_names=("phone", "telefono", "teléfono", "celular"),
                    detector=PhoneNumberDetector(),
                )
            )
            .add_rule(
                AnonymizationRule(
                    rule_id="full_name",
                    strategy=AnonymizerBuilder.partial_mask_strategy(1, 0),
                    field_names=("full_name", "nombre", "customer_name"),
                )
            )
            .add_rule(
                AnonymizationRule(
                    rule_id="address",
                    strategy=RedactionTagStrategy("[DIRECCIÓN OCULTA]"),
                    field_names=("address", "direccion", "dirección"),
                )
            )
            .add_rule(
                AnonymizationRule(
                    rule_id="vin",
                    strategy=AnonymizerBuilder.partial_mask_strategy(0, 4),
                    field_names=("vin",),
                )
            )
            .build()
        )

    def mask_map(self, data: dict[str, Any]) -> dict[str, Any]:
        """Anonimiza un diccionario anidado sin mutar la entrada.

        Args:
            data: Estructura con posibles datos personales.

        Returns:
            Copia sanitizada.
        """
        return self._anonymizer.anonymize_map(data)

    def mask_text(self, text: str) -> str:
        """Anonimiza correos, tarjetas y teléfonos dentro de un texto.

        Args:
            text: Texto original.

        Returns:
            Texto con las coincidencias enmascaradas.
        """
        return self._anonymizer.anonymize_text(text)

    def audit(self, data: dict[str, Any]) -> ComplianceReport:
        """Genera un reporte de auditoría sin valores PII.

        Args:
            data: Estructura a auditar.

        Returns:
            Reporte con conteos y metadatos.
        """
        return self._anonymizer.audit_compliance(data)
