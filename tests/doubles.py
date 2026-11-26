"""Dobles de prueba reutilizables por la suite.

Se implementan exclusivamente los puertos públicos de ``pii_anonymizer.api``.
"""

from __future__ import annotations

from pii_anonymizer.api import MaskingStrategy, SaltProvider


class FixedSaltProviderStub(SaltProvider):
    """Stub de ``SaltProvider`` con un valor fijo y predecible."""

    def __init__(self, salt: str = "fixed-test-salt-2026") -> None:
        self._salt = salt

    def get_salt(self) -> str:
        """Retorna siempre el mismo *salt*."""
        return self._salt


class SpyMaskingStrategy(MaskingStrategy):
    """Spy que registra cada invocación y retorna una etiqueta inocua."""

    def __init__(self, tag: str = "SPY") -> None:
        self._tag = tag
        self.calls: list[str] = []

    @property
    def invocation_count(self) -> int:
        """Cantidad de veces que se invocó ``mask``."""
        return len(self.calls)

    def mask(self, raw_value: str) -> str:
        """Registra el valor recibido y retorna una etiqueta numerada."""
        self.calls.append(raw_value)
        return f"[{self._tag}:{len(self.calls)}]"
