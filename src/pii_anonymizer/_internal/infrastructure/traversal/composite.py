"""Recorrido de estructuras anidadas mediante el patrón Composite."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pii_anonymizer._internal.application.ports import StructureTraverser
from pii_anonymizer._internal.application.services.detector_chain import (
    DetectorChain,
)
from pii_anonymizer._internal.domain.models import (
    AnonymizationRule,
    ComplianceReport,
)


@dataclass
class TraversalContext:
    """Estado efímero de una única invocación de recorrido.

    Se crea dentro de :meth:`CompositeStructureTraverser.traverse`, por lo
    que el adaptador es *stateless* entre llamadas y seguro de reutilizar.

    Attributes:
        field_rules: Índice de reglas por nombre de campo normalizado.
        detector_rules: Reglas que aportan detectores de texto.
        total_fields_scanned: Escalares visitados.
        anonymized_fields_count: Escalares transformados al menos una vez.
        detected_categories: Hallazgos acumulados por categoría.
        applied_rule_ids: Reglas aplicadas, sin duplicados y en orden de uso.
    """

    field_rules: dict[str, AnonymizationRule]
    detector_rules: tuple[AnonymizationRule, ...] = ()
    total_fields_scanned: int = 0
    anonymized_fields_count: int = 0
    detected_categories: dict[str, int] = field(default_factory=dict)
    applied_rule_ids: dict[str, None] = field(default_factory=dict)
    _detector_chain: DetectorChain = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._detector_chain = DetectorChain(self.detector_rules)

    def find_field_rule(self, field_name: str) -> AnonymizationRule | None:
        """Busca la regla asociada a ``field_name`` sin distinguir mayúsculas."""
        return self.field_rules.get(field_name.casefold())

    def record_field_mask(self, rule: AnonymizationRule) -> None:
        """Contabiliza un campo enmascarado por coincidencia de nombre."""
        self.anonymized_fields_count += 1
        category = _category_for(rule)
        self.detected_categories[category] = (
            self.detected_categories.get(category, 0) + 1
        )
        self.applied_rule_ids[rule.rule_id] = None

    def apply_detectors(self, text: str) -> str:
        """Sanitiza ``text`` y contabiliza cada coincidencia encontrada."""
        sanitized, applied = self._detector_chain.apply_detailed(text)
        if applied:
            self.anonymized_fields_count += 1
            for item in applied:
                self.detected_categories[item.category] = (
                    self.detected_categories.get(item.category, 0) + 1
                )
                self.applied_rule_ids[item.rule_id] = None
        return sanitized


def _category_for(rule: AnonymizationRule) -> str:
    """Usa la categoría del detector cuando existe; si no, el ``rule_id``."""
    return rule.detector.category if rule.detector is not None else rule.rule_id


def _node_for(value: Any) -> "DataNode":
    """Construye el nodo Composite adecuado para ``value``."""
    if isinstance(value, dict):
        return DictNode(value)
    if isinstance(value, list):
        return ListNode(value)
    return ScalarNode(value)


class DataNode(ABC):
    """Componente del patrón Composite que representa un valor de datos."""

    @abstractmethod
    def process(self, context: TraversalContext) -> Any:
        """Retorna una versión procesada (posiblemente nueva) del nodo.

        Args:
            context: Estado compartido de la invocación actual.

        Returns:
            Valor procesado.
        """


class DictNode(DataNode):
    """Nodo compuesto que recorre un diccionario y produce uno nuevo."""

    def __init__(self, data: dict[Any, Any]) -> None:
        """Almacena la referencia de solo lectura al diccionario de entrada.

        Args:
            data: Diccionario que se recorrerá sin mutar.
        """
        self._data = data

    def process(self, context: TraversalContext) -> dict[Any, Any]:
        """Construye un diccionario sanitizado sin mutar ``data``."""
        sanitized: dict[Any, Any] = {}
        for key, value in self._data.items():
            rule = (
                context.find_field_rule(key)
                if isinstance(key, str)
                else None
            )
            if rule is not None and not isinstance(value, (dict, list)):
                sanitized[key] = ScalarNode(value, field_rule=rule).process(context)
            else:
                sanitized[key] = _node_for(value).process(context)
        return sanitized


class ListNode(DataNode):
    """Nodo compuesto que recorre una lista y produce una nueva."""

    def __init__(self, data: list[Any]) -> None:
        """Almacena la referencia de solo lectura a la lista de entrada.

        Args:
            data: Lista que se recorrerá sin mutar.
        """
        self._data = data

    def process(self, context: TraversalContext) -> list[Any]:
        """Construye una lista sanitizada sin mutar ``data``."""
        return [_node_for(item).process(context) for item in self._data]


class ScalarNode(DataNode):
    """Nodo hoja que aplica una regla de campo o los detectores de texto."""

    def __init__(
        self,
        value: Any,
        field_rule: AnonymizationRule | None = None,
    ) -> None:
        """Inicializa la hoja con su valor y, opcionalmente, su regla de campo.

        Args:
            value: Valor escalar original.
            field_rule: Regla que debe aplicarse por coincidencia de nombre.
        """
        self._value = value
        self._field_rule = field_rule

    def process(self, context: TraversalContext) -> Any:
        """Procesa el escalar según la regla de campo o los detectores.

        Las reglas de campo enmascaran cadenas y valores numéricos (enteros o
        reales); ``None`` y booleanos se preservan porque no representan
        datos identificables en sí mismos.
        """
        context.total_fields_scanned += 1
        if self._field_rule is not None:
            if isinstance(self._value, str):
                raw_value = self._value
            elif isinstance(self._value, bool) or self._value is None:
                return self._value
            elif isinstance(self._value, (int, float)):
                raw_value = str(self._value)
            else:
                return self._value

            masked = self._field_rule.strategy.mask(raw_value)
            context.record_field_mask(self._field_rule)
            return masked
        if not isinstance(self._value, str):
            return self._value
        return context.apply_detectors(self._value)


class CompositeStructureTraverser(StructureTraverser):
    """Adaptador que recorre diccionarios y listas con el patrón Composite.

    Cada valor escalar se contabiliza una vez. Los valores de texto se
    examinan con los detectores activos, salvo que el nombre de su campo
    coincida con una regla, en cuyo caso se aplica la estrategia de esa regla
    al valor completo.
    """

    def __init__(self) -> None:
        """Crea un recorredor sin estado; el contexto vive en cada invocación."""

    def traverse(
        self,
        data: dict[str, Any],
        rules: list[AnonymizationRule],
    ) -> tuple[dict[str, Any], ComplianceReport]:
        """Recorre ``data`` y retorna la copia sanitizada con su reporte.

        Args:
            data: Diccionario de entrada; no se muta.
            rules: Reglas activas.

        Returns:
            Tupla ``(copia_sanitizada, reporte)``.

        Raises:
            TypeError: Si ``data`` no es un diccionario.
        """
        if not isinstance(data, dict):
            raise TypeError("data debe ser un diccionario.")

        field_rules: dict[str, AnonymizationRule] = {}
        detector_rules: list[AnonymizationRule] = []
        for rule in rules:
            for name in rule.field_names:
                field_rules[name.casefold()] = rule
            if rule.detector is not None:
                detector_rules.append(rule)

        context = TraversalContext(
            field_rules=field_rules,
            detector_rules=tuple(detector_rules),
        )
        sanitized = DictNode(data).process(context)
        report = ComplianceReport(
            total_fields_scanned=context.total_fields_scanned,
            anonymized_fields_count=context.anonymized_fields_count,
            detected_categories=dict(context.detected_categories),
            applied_rule_ids=tuple(context.applied_rule_ids),
        )
        return sanitized, report
