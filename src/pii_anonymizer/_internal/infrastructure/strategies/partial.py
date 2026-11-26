"""Estrategia de enmascaramiento parcial."""

from __future__ import annotations

from pii_anonymizer._internal.domain.ports import MaskingStrategy


class PartialMaskStrategy(MaskingStrategy):
    """Conserva extremos visibles y enmascara el centro de la cadena.

    Para direcciones de correo preserva el dominio completo (incluido el
    carácter ``@``), de modo que el valor siga siendo legible para soporte
    sin exponer la parte local. Si la cadena es demasiado corta para dejar
    un centro enmascarado, se enmascara por completo.
    """

    def __init__(
        self,
        visible_prefix: int = 2,
        visible_suffix: int = 2,
        mask_char: str = "*",
    ) -> None:
        """Inicializa la estrategia.

        Args:
            visible_prefix: Cantidad de caracteres visibles al inicio.
            visible_suffix: Cantidad de caracteres visibles al final.
            mask_char: Carácter utilizado para enmascarar.

        Raises:
            ValueError: Si algún tamaño es negativo o ``mask_char`` no es
                exactamente un carácter.
        """
        if visible_prefix < 0 or visible_suffix < 0:
            raise ValueError("Los tamaños visibles no pueden ser negativos.")
        if len(mask_char) != 1:
            raise ValueError("mask_char debe ser exactamente un carácter.")
        self._visible_prefix = visible_prefix
        self._visible_suffix = visible_suffix
        self._mask_char = mask_char

    def mask(self, raw_value: str) -> str:
        """Enmascara el centro de ``raw_value``.

        Args:
            raw_value: Cadena original; puede ser vacía.

        Returns:
            Cadena con el centro reemplazado por ``mask_char``. En correos se
            conserva el dominio posterior a ``@``.
        """
        if not raw_value:
            return raw_value

        local, separator, domain = raw_value.rpartition("@")
        if separator and local and domain:
            return f"{self._mask_core(local)}@{domain}"
        return self._mask_core(raw_value)

    def _mask_core(self, value: str) -> str:
        """Enmascara el centro de un fragmento sin dominio."""
        visible = self._visible_prefix + self._visible_suffix
        if len(value) <= visible:
            return self._mask_char * len(value)

        prefix = value[: self._visible_prefix]
        suffix = value[len(value) - self._visible_suffix :] if self._visible_suffix else ""
        hidden = len(value) - self._visible_prefix - self._visible_suffix
        return f"{prefix}{self._mask_char * hidden}{suffix}"
