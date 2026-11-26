"""Cadena de detección y resolución de reemplazos de texto.

Implementa el patrón de comportamiento **Chain of Responsibility** para
encadenar detectores y el patrón **Strategy** para transformar cada
coincidencia con la estrategia declarada por su regla.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pii_anonymizer._internal.domain.models import AnonymizationRule, TextMatch
from pii_anonymizer._internal.domain.ports import (
    MaskingStrategy,
    SensitivePatternDetector,
)


@dataclass(frozen=True, slots=True)
class AppliedMask:
    """Metadatos de un reemplazo efectivamente aplicado sobre un texto.

    No contiene el valor original ni el valor enmascarado; solo permite
    contabilizar hallazgos para el reporte de auditoría.

    Attributes:
        rule_id: Regla que aportó la estrategia de enmascaramiento.
        category: Categoría PII reportada por el detector.
        start: Índice inclusivo original del reemplazo.
        end: Índice exclusivo original del reemplazo.
    """

    rule_id: str
    category: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _Candidate:
    """Coincidencia interna asociada a la regla que la resolverá."""

    match: TextMatch
    strategy: MaskingStrategy
    rule_id: str
    category: str


class _DetectorHandler:
    """Eslabón concreto de la cadena de responsabilidad."""

    def __init__(
        self,
        rule: AnonymizationRule,
        detector: SensitivePatternDetector,
    ) -> None:
        self._rule = rule
        self._detector = detector
        self._next: _DetectorHandler | None = None

    def set_next(self, next_handler: "_DetectorHandler") -> "_DetectorHandler":
        """Enlaza el siguiente eslabón y lo retorna para facilitar el encadenado."""
        self._next = next_handler
        return next_handler

    def handle(self, text: str, collected: list[_Candidate]) -> None:
        """Detecta coincidencias, las acumula y delega al siguiente eslabón."""
        for match in self._detector.detect(text):
            collected.append(
                _Candidate(
                    match=match,
                    strategy=self._rule.strategy,
                    rule_id=self._rule.rule_id,
                    category=self._detector.category,
                )
            )
        if self._next is not None:
            self._next.handle(text, collected)


class DetectorChain:
    """Encadena los detectores activos y aplica las estrategias asociadas.

    Los rangos se resuelven de derecha a izquierda para no invalidar los
    índices de las coincidencias restantes. Ante solapamientos se conserva
    la coincidencia que inicia primero y, a igual inicio, la más larga.
    """

    def __init__(self, rules: Iterable[AnonymizationRule]) -> None:
        """Encadena las reglas que declaran un detector, en su orden de llegada.

        Args:
            rules: Reglas activas; las que no tienen detector se omiten.
        """
        self._head: _DetectorHandler | None = None
        tail: _DetectorHandler | None = None
        for rule in rules:
            detector = rule.detector
            if detector is None:
                continue
            handler = _DetectorHandler(rule, detector)
            if self._head is None:
                self._head = handler
            elif tail is not None:
                tail.set_next(handler)
            tail = handler

    def apply(self, text: str) -> str:
        """Retorna el texto con todas las coincidencias válidas enmascaradas.

        Args:
            text: Texto plano a sanitizar.

        Returns:
            Texto sanitizado; ``text`` sin cambios si no hay detectores o
            coincidencias.
        """
        sanitized, _ = self.apply_detailed(text)
        return sanitized

    def apply_detailed(self, text: str) -> tuple[str, tuple[AppliedMask, ...]]:
        """Sanitiza ``text`` y retorna metadatos de los reemplazos aplicados.

        Args:
            text: Texto plano a sanitizar.

        Returns:
            Tupla ``(texto_sanitizado, reemplazos_aplicados)``.
        """
        if not text or self._head is None:
            return text, ()

        candidates: list[_Candidate] = []
        self._head.handle(text, candidates)

        accepted = self._resolve_overlaps(candidates, len(text))
        sanitized = text
        applied: list[AppliedMask] = []
        for candidate in reversed(accepted):
            match = candidate.match
            sanitized = (
                sanitized[: match.start]
                + candidate.strategy.mask(sanitized[match.start : match.end])
                + sanitized[match.end :]
            )
            applied.append(
                AppliedMask(
                    rule_id=candidate.rule_id,
                    category=candidate.category,
                    start=match.start,
                    end=match.end,
                )
            )
        applied.reverse()
        return sanitized, tuple(applied)

    @staticmethod
    def _resolve_overlaps(
        candidates: list[_Candidate],
        text_length: int,
    ) -> list[_Candidate]:
        """Filtra coincidencias fuera de rango y resuelve solapamientos."""
        valid = [
            candidate
            for candidate in candidates
            if 0 <= candidate.match.start < candidate.match.end <= text_length
        ]
        valid.sort(key=lambda candidate: (candidate.match.start, -candidate.match.end))

        accepted: list[_Candidate] = []
        last_end = -1
        for candidate in valid:
            if candidate.match.start >= last_end:
                accepted.append(candidate)
                last_end = candidate.match.end
        return accepted
