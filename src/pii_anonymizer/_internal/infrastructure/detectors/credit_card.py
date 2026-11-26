"""Detector de números de tarjeta de crédito."""

from __future__ import annotations

import re

from pii_anonymizer._internal.domain.models import TextMatch
from pii_anonymizer._internal.domain.ports import SensitivePatternDetector


class CreditCardDetector(SensitivePatternDetector):
    """Detecta secuencias de 13 a 19 dígitos con espacios o guiones opcionales."""

    _PATTERN = re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)")

    @property
    def category(self) -> str:
        """Categoría reportada por este detector."""
        return "CREDIT_CARD"

    def detect(self, text: str) -> list[TextMatch]:
        """Retorna los números de tarjeta encontrados en ``text``.

        Args:
            text: Texto plano a analizar.

        Returns:
            Coincidencias con índices absolutos y el fragmento original,
            incluyendo los separadores presentes.
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
