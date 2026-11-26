"""Estrategia de enmascaramiento mediante hash con sal."""

from __future__ import annotations

import hashlib

from pii_anonymizer._internal.domain.ports import (
    MaskingStrategy,
    SaltProvider,
)


class HashMaskStrategy(MaskingStrategy):
    """Reemplaza el valor por ``hash:<sha256(salt + valor)[:longitud]>``.

    El resultado es irreversible y determinista para un mismo *salt*. El
    proveedor de *salt* se inyecta por constructor para cumplir con la
    inversión de dependencias y permitir dobles de prueba.
    """

    _MAX_PREFIX_LENGTH = 64

    def __init__(self, salt_provider: SaltProvider, prefix_length: int = 12) -> None:
        """Inicializa la estrategia.

        Args:
            salt_provider: Fuente del *salt* criptográfico.
            prefix_length: Cantidad de caracteres hexadecimales a conservar.

        Raises:
            ValueError: Si ``salt_provider`` es ``None`` o ``prefix_length``
                está fuera del rango ``1..64``.
        """
        if salt_provider is None:
            raise ValueError("salt_provider es obligatorio.")
        if not 1 <= prefix_length <= self._MAX_PREFIX_LENGTH:
            raise ValueError("prefix_length debe estar entre 1 y 64.")
        self._salt_provider = salt_provider
        self._prefix_length = prefix_length

    def mask(self, raw_value: str) -> str:
        """Calcula el hash salado de ``raw_value``.

        Args:
            raw_value: Valor sensible original.

        Returns:
            Cadena con prefijo ``hash:`` y el fragmento hexadecimal.
        """
        salt = self._salt_provider.get_salt()
        digest = hashlib.sha256(f"{salt}{raw_value}".encode("utf-8")).hexdigest()
        return f"hash:{digest[: self._prefix_length]}"
