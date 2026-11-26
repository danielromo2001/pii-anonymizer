"""Proveedor criptográfico de *salt* para producción."""

from __future__ import annotations

import secrets

from pii_anonymizer._internal.domain.ports import SaltProvider


class RandomSaltProvider(SaltProvider):
    """Genera un token hexadecimal distinto y seguro en cada invocación."""

    def get_salt(self) -> str:
        """Retorna 32 caracteres hexadecimales provenientes de ``secrets``.

        Returns:
            Token aleatorio generado con :func:`secrets.token_hex`.
        """
        return secrets.token_hex(16)
