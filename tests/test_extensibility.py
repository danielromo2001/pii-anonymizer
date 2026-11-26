"""Prueba de extensibilidad usando exclusivamente ``pii_anonymizer.api``.

Simula a un equipo auditor que agrega una estrategia y un detector propios
sin conocer ni modificar la implementación interna.
"""

from __future__ import annotations

import re

from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    MaskingStrategy,
    SaltProvider,
    SensitivePatternDetector,
    TextMatch,
)


class RedactionTagStrategy(MaskingStrategy):
    """Estrategia de extensión que reemplaza todo por una etiqueta fija."""

    def __init__(self, tag: str = "[REDACTED]") -> None:
        self._tag = tag

    def mask(self, raw_value: str) -> str:
        """Ignora el valor original y retorna la etiqueta."""
        return self._tag


class ColombianCedulaDetector(SensitivePatternDetector):
    """Detector de cédulas colombianas de 6 a 10 dígitos."""

    _PATTERN = re.compile(r"(?<!\d)\d{6,10}(?!\d)")

    @property
    def category(self) -> str:
        """Categoría propia de la extensión."""
        return "CO_CEDULA"

    def detect(self, text: str) -> list[TextMatch]:
        """Retorna las cédulas encontradas."""
        return [
            TextMatch(
                category=self.category,
                start=match.start(),
                end=match.end(),
                matched_text=match.group(0),
            )
            for match in self._PATTERN.finditer(text)
        ]


class ConstantSaltProvider(SaltProvider):
    """Proveedor de *salt* de extensión con valor constante."""

    def get_salt(self) -> str:
        """Retorna un valor fijo."""
        return "auditor-salt"


class FixedWindowDetector(SensitivePatternDetector):
    """Detector de prueba que reporta una ventana fija."""

    def __init__(self, category: str, start: int, end: int) -> None:
        self._category = category
        self._start = start
        self._end = end

    @property
    def category(self) -> str:
        """Categoría configurada."""
        return self._category

    def detect(self, text: str) -> list[TextMatch]:
        """Retorna la ventana si el texto es suficientemente largo."""
        if len(text) < self._end:
            return []
        return [
            TextMatch(
                category=self._category,
                start=self._start,
                end=self._end,
                matched_text=text[self._start : self._end],
            )
        ]


class BrokenBoundsDetector(SensitivePatternDetector):
    """Detector defensivo que reporta índices fuera del texto."""

    @property
    def category(self) -> str:
        """Categoría de la extensión defectuosa."""
        return "BROKEN"

    def detect(self, text: str) -> list[TextMatch]:
        """Retorna coincidencias inválidas a propósito."""
        return [
            TextMatch("BROKEN", -1, 2, "xx"),
            TextMatch("BROKEN", 100, 200, "yy"),
        ]


def test_custom_strategy_and_detector_are_registered_through_public_api() -> None:
    anonymizer = (
        AnonymizerBuilder()
        .with_default_rules()
        .add_rule(
            AnonymizationRule(
                rule_id="co_cedula",
                strategy=RedactionTagStrategy(),
                field_names=("cedula", "documento"),
                detector=ColombianCedulaDetector(),
            )
        )
        .build()
    )

    text_result = anonymizer.anonymize_text("cliente con cédula 1029384756")
    map_result = anonymizer.anonymize_map(
        {"cedula": "1029384756", "nota": "documento 1029384756"}
    )

    assert "1029384756" not in text_result
    assert "[REDACTED]" in text_result
    assert map_result["cedula"] == "[REDACTED]"
    assert "1029384756" not in map_result["nota"]
    assert "[REDACTED]" in map_result["nota"]


def test_custom_strategy_can_replace_builtin_email_detection() -> None:
    anonymizer = (
        AnonymizerBuilder()
        .add_rule(
            AnonymizationRule(
                rule_id="email_redacted",
                strategy=RedactionTagStrategy("[EMAIL_REDACTED]"),
                detector=AnonymizerBuilder.email_detector(),
            )
        )
        .build()
    )

    assert anonymizer.anonymize_text("ana@example.com") == "[EMAIL_REDACTED]"


def test_custom_hash_strategy_uses_injected_salt_provider() -> None:
    strategy = AnonymizerBuilder.hash_mask_strategy(ConstantSaltProvider(), 10)
    anonymizer = AnonymizerBuilder().add_rule(
        AnonymizationRule(
            rule_id="secret",
            strategy=strategy,
            field_names=("secret",),
        )
    ).build()

    first = anonymizer.anonymize_map({"secret": "valor"})["secret"]
    second = anonymizer.anonymize_map({"secret": "valor"})["secret"]

    assert first == second
    assert first.startswith("hash:")
    assert len(first) == len("hash:") + 10


def test_registering_extension_after_build_affects_both_entry_points() -> None:
    anonymizer = AnonymizerBuilder().with_default_rules().build()
    anonymizer.register_rule(
        AnonymizationRule(
            rule_id="co_cedula",
            strategy=RedactionTagStrategy(),
            field_names=("cedula",),
            detector=ColombianCedulaDetector(),
        )
    )

    assert anonymizer.anonymize_map({"cedula": "1029384756"}) == {
        "cedula": "[REDACTED]"
    }
    assert (
        anonymizer.anonymize_text("cc 1029384756") == "cc [REDACTED]"
    )


def test_overlapping_matches_keep_the_first_and_longest_window() -> None:
    anonymizer = (
        AnonymizerBuilder()
        .add_rule(
            AnonymizationRule(
                "first",
                RedactionTagStrategy("[A]"),
                detector=FixedWindowDetector("FIRST", 0, 2),
            )
        )
        .add_rule(
            AnonymizationRule(
                "second",
                RedactionTagStrategy("[B]"),
                detector=FixedWindowDetector("SECOND", 1, 3),
            )
        )
        .build()
    )

    assert anonymizer.anonymize_text("abc") == "[A]c"


def test_out_of_bounds_matches_from_third_party_detector_are_ignored() -> None:
    anonymizer = (
        AnonymizerBuilder()
        .add_rule(
            AnonymizationRule(
                "broken",
                RedactionTagStrategy(),
                detector=BrokenBoundsDetector(),
            )
        )
        .build()
    )

    assert anonymizer.anonymize_text("abc") == "abc"
