"""Detector de direcciones de correo electrónico."""

from __future__ import annotations

import re

from pii_anonymizer._internal.domain.models import TextMatch
from pii_anonymizer._internal.domain.ports import SensitivePatternDetector


class EmailDetector(SensitivePatternDetector):
    """Detecta direcciones de correo con formato habitual."""

    _PATTERN = re.compile(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        re.IGNORECASE,
    )

    @property
    def category(self) -> str:
        """Categoría reportada por este detector."""
        return "EMAIL"

    def detect(self, text: str) -> list[TextMatch]:
        """Retorna las direcciones de correo encontradas en ``text``.

        Args:
            text: Texto plano a analizar.

        Returns:
            Coincidencias con índices absolutos y el fragmento original.
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
