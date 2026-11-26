"""Puertos de extensión del dominio.

Los puertos son contratos abstractos que permiten invertir dependencias
(Dependency Inversion Principle). La infraestructura los implementa y el
dominio/aplicación dependen únicamente de las abstracciones.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pii_anonymizer._internal.domain.models import TextMatch


class MaskingStrategy(ABC):
    """Contrato para transformar un valor sensible en una representación segura.

    Es el punto de extensión que materializa el patrón Strategy: el cliente
    puede intercambiar algoritmos de enmascaramiento sin modificar los casos
    de uso ni los detectores.
    """

    @abstractmethod
    def mask(self, raw_value: str) -> str:
        """Retorna la representación sanitizada de ``raw_value``.

        Args:
            raw_value: Valor original que puede contener PII.

        Returns:
            Valor transformado que no debe exponer el dato original.
        """


class SensitivePatternDetector(ABC):
    """Contrato para detectar PII dentro de una cadena de texto.

    Cada implementación actúa como un eslabón de la cadena de detección
    (Chain of Responsibility) y declara la categoría que reconoce.
    """

    @property
    @abstractmethod
    def category(self) -> str:
        """Nombre legible de la categoría PII detectada (por ejemplo, ``EMAIL``)."""

    @abstractmethod
    def detect(self, text: str) -> list["TextMatch"]:
        """Busca coincidencias de la categoría en ``text``.

        Args:
            text: Cadena de texto a analizar.

        Returns:
            Lista de coincidencias con índices absolutos sobre ``text``.
        """


class SaltProvider(ABC):
    """Contrato para proveer el *salt* criptográfico de las estrategias de hash.

    Abstraer el origen del *salt* permite usar valores aleatorios en producción
    y valores fijos en pruebas, sin cambiar la estrategia de enmascaramiento.
    """

    @abstractmethod
    def get_salt(self) -> str:
        """Retorna el *salt* que se concatenará antes de calcular el hash."""
