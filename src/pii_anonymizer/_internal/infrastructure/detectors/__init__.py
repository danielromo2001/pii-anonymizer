"""Detectores concretos basados en expresiones regulares."""

from __future__ import annotations

from pii_anonymizer._internal.infrastructure.detectors.credit_card import (
    CreditCardDetector,
)
from pii_anonymizer._internal.infrastructure.detectors.email import EmailDetector

__all__ = ["CreditCardDetector", "EmailDetector"]
