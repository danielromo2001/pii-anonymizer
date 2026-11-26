"""Demostración ejecutable de las cuatro funcionalidades de la API pública.

Ejecución desde la raíz del repositorio::

    python examples/demo_cli.py

El script solo importa símbolos de ``pii_anonymizer`` / ``pii_anonymizer.api``.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pii_anonymizer.api import (  # noqa: E402
    AnonymizationRule,
    AnonymizerBuilder,
    MaskingStrategy,
    SensitivePatternDetector,
    TextMatch,
)


class PhoneNumberDetector(SensitivePatternDetector):
    """Extensión de ejemplo: detecta teléfonos móviles colombianos."""

    _PATTERN = re.compile(r"(?<!\d)(?:\+57\s?)?3\d{2}[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\d)")

    @property
    def category(self) -> str:
        """Categoría de la extensión."""
        return "PHONE"

    def detect(self, text: str) -> list[TextMatch]:
        """Retorna los teléfonos encontrados en ``text``."""
        return [
            TextMatch(
                category=self.category,
                start=match.start(),
                end=match.end(),
                matched_text=match.group(0),
            )
            for match in self._PATTERN.finditer(text)
        ]


class RedactionTagStrategy(MaskingStrategy):
    """Extensión de ejemplo: reemplaza todo por una etiqueta fija."""

    def mask(self, raw_value: str) -> str:
        """Retorna la etiqueta de redacción."""
        return "[TELÉFONO REDACTADO]"


def _print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> None:
    """Ejecuta la demostración completa por consola."""
    anonymizer = AnonymizerBuilder().with_default_rules().build()

    payload = {
        "customer": {
            "name": "Ana Pérez",
            "email": "ana.perez@example.com",
            "password": "ClaveSuperSecreta2026",
            "document_id": "1029384756",
            "phone": "300 123 4567",
            "card_number": "4111 1111 1111 1111",
        },
        "notes": "Contactar a ana.perez@example.com o al 300 123 4567.",
        "orders": [
            {"id": "ORD-1", "email": "compras@example.com"},
            {"id": "ORD-2", "note": "sin datos sensibles"},
        ],
    }
    original_payload = json.loads(json.dumps(payload))

    _print_section("1) anonymize_map — estructura anidada sanitizada")
    sanitized_payload = anonymizer.anonymize_map(payload)
    print(json.dumps(sanitized_payload, indent=2, ensure_ascii=False))
    print("\n¿El payload original quedó intacto?")
    print(payload == original_payload)

    _print_section("2) anonymize_text — traza de log sanitizada")
    log_line = (
        "INFO pago aprobado para ana.perez@example.com con la tarjeta "
        "4111 1111 1111 1111; notificación a compras@example.com"
    )
    print("Entrada:")
    print(log_line)
    print("\nSalida:")
    print(anonymizer.anonymize_text(log_line))

    _print_section("3) register_rule — extensión OCP con teléfonos")
    phone_rule = AnonymizationRule(
        rule_id="phone",
        strategy=RedactionTagStrategy(),
        field_names=("phone", "telefono", "teléfono"),
        detector=PhoneNumberDetector(),
    )
    anonymizer.register_rule(phone_rule)
    print("Regla registrada:", phone_rule.rule_id)
    print(
        json.dumps(
            anonymizer.anonymize_map(
                {
                    "phone": "300 123 4567",
                    "notes": "Llamar al 300 123 4567",
                }
            ),
            indent=2,
            ensure_ascii=False,
        )
    )
    print("\nTexto:")
    print(anonymizer.anonymize_text("Contacto: +57 300 123 4567"))

    _print_section("4) audit_compliance — metadatos sin PII")
    report = anonymizer.audit_compliance(payload)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    print("\nEl reporte contiene valores sensibles en claro?")
    serialized_report = json.dumps(asdict(report), ensure_ascii=False)
    sensitive_in_report = any(
        value in serialized_report
        for value in (
            "ana.perez@example.com",
            "ClaveSuperSecreta2026",
            "1029384756",
            "4111 1111 1111 1111",
        )
    )
    print(sensitive_in_report)

    _print_section("Demostración finalizada")


if __name__ == "__main__":
    main()
