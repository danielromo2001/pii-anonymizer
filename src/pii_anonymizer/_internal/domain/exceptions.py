"""Excepciones propias del núcleo de dominio.

Este módulo no depende de ninguna otra capa ni de librerías externas.
"""

from __future__ import annotations


class AnonymizerError(Exception):
    """Excepción base para todos los errores controlados del componente.

    Permite a los clientes de la API pública capturar cualquier fallo
    originado por el dominio sin acoplarse a excepciones de implementación.
    """


class InvalidRuleError(AnonymizerError):
    """Se lanza cuando una :class:`AnonymizationRule` viola sus invariantes.

    Los motivos habituales son un identificador vacío, una estrategia de
    enmascaramiento nula o la ausencia simultánea de ``field_names`` y
    ``detector``.
    """
