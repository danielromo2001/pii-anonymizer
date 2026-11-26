"""Objetos de valor inmutables del dominio."""

from __future__ import annotations

from dataclasses import dataclass, field

from pii_anonymizer._internal.domain.exceptions import InvalidRuleError
from pii_anonymizer._internal.domain.ports import (
    MaskingStrategy,
    SensitivePatternDetector,
)


@dataclass(frozen=True, slots=True)
class TextMatch:
    """Coincidencia de un patrón PII dentro de un texto.

    Attributes:
        category: Categoría detectada, por ejemplo ``"EMAIL"`` o
            ``"CREDIT_CARD"``.
        start: Índice inclusivo donde inicia la coincidencia.
        end: Índice exclusivo donde termina la coincidencia.
        matched_text: Fragmento original que hizo *match*. Nunca se incluye
            en reportes de auditoría.
    """

    category: str
    start: int
    end: int
    matched_text: str


@dataclass(frozen=True, slots=True)
class AnonymizationRule:
    """Regla de anonimización aplicable por nombre de campo y/o detector.

    Una regla debe declarar al menos un criterio de aplicación: nombres de
    campo (comparados sin distinguir mayúsculas) o un detector de patrones.

    Attributes:
        rule_id: Identificador estable y único de la regla.
        strategy: Estrategia concreta que transforma el valor sensible.
        field_names: Claves de diccionario a enmascarar. La comparación se
            realiza de forma *case-insensitive*.
        detector: Detector opcional para localizar PII dentro de cadenas.

    Raises:
        InvalidRuleError: Si ``rule_id`` está vacío, ``strategy`` es ``None``,
            algún nombre de campo está vacío o no se define ni ``field_names``
            ni ``detector``.
    """

    rule_id: str
    strategy: MaskingStrategy
    field_names: tuple[str, ...] = ()
    detector: SensitivePatternDetector | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, str) or not self.rule_id.strip():
            raise InvalidRuleError("rule_id no puede estar vacío.")
        if self.strategy is None:
            raise InvalidRuleError(
                f"La regla '{self.rule_id}' requiere una estrategia de enmascaramiento."
            )

        raw_names = self.field_names
        if raw_names is None:
            raw_names = ()
        elif isinstance(raw_names, str):
            raw_names = (raw_names,)

        normalized_names = tuple(name.strip() for name in raw_names)
        if any(not name for name in normalized_names):
            raise InvalidRuleError(
                f"La regla '{self.rule_id}' contiene nombres de campo vacíos."
            )
        if not normalized_names and self.detector is None:
            raise InvalidRuleError(
                f"La regla '{self.rule_id}' debe definir field_names o detector."
            )

        object.__setattr__(self, "rule_id", self.rule_id.strip())
        object.__setattr__(self, "field_names", normalized_names)


@dataclass(frozen=True, slots=True)
class ComplianceReport:
    """Resultado agregado de una auditoría de cumplimiento.

    El reporte contiene exclusivamente metadatos y conteos; por diseño nunca
    almacena valores PII en claro ni fragmentos de los mismos.

    Attributes:
        total_fields_scanned: Cantidad de valores escalares recorridos.
        anonymized_fields_count: Cantidad de valores escalares transformados
            al menos una vez.
        detected_categories: Conteo de hallazgos por categoría o regla.
        applied_rule_ids: Identificadores únicos de las reglas aplicadas, en
            el orden en que se aplicaron.
    """

    total_fields_scanned: int
    anonymized_fields_count: int
    detected_categories: dict[str, int] = field(default_factory=dict)
    applied_rule_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "detected_categories", dict(self.detected_categories))
        object.__setattr__(self, "applied_rule_ids", tuple(self.applied_rule_ids))
