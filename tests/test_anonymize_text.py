"""Pruebas de anonimización de texto plano."""

from __future__ import annotations

from pii_anonymizer.api import AnonymizerBuilder


def _build_anonymizer():
    return AnonymizerBuilder().with_default_rules().build()


def test_anonymizes_multiple_emails_and_cards_in_a_log_line() -> None:
    anonymizer = _build_anonymizer()
    log_line = (
        "2026-05-01 INFO pago de ana@example.com con 4111 1111 1111 1111; "
        "copia a luis@test.co y respaldo 5500-0000-0000-0004"
    )

    result = anonymizer.anonymize_text(log_line)

    assert "ana@example.com" not in result
    assert "luis@test.co" not in result
    assert "4111 1111 1111 1111" not in result
    assert "5500-0000-0000-0004" not in result
    assert "@example.com" in result
    assert "@test.co" in result
    assert "INFO" in result


def test_text_without_pii_is_returned_unchanged() -> None:
    anonymizer = _build_anonymizer()
    text = "2026-05-01 INFO servicio iniciado correctamente"

    assert anonymizer.anonymize_text(text) == text


def test_empty_text_returns_empty_text() -> None:
    anonymizer = _build_anonymizer()

    assert anonymizer.anonymize_text("") == ""


def test_accepts_card_numbers_with_and_without_separators() -> None:
    anonymizer = _build_anonymizer()
    text = (
        "corto 1234567890123, largo 1234567890123456789, "
        "espacios 4111 1111 1111 1111, guiones 4111-1111-1111-1111"
    )

    result = anonymizer.anonymize_text(text)

    assert "1234567890123" not in result
    assert "1234567890123456789" not in result
    assert "4111 1111 1111 1111" not in result
    assert "4111-1111-1111-1111" not in result


def test_does_not_detect_digit_runs_outside_supported_length() -> None:
    anonymizer = _build_anonymizer()
    text = "docena 123456789012 y veinte 12345678901234567890"

    assert anonymizer.anonymize_text(text) == text


def test_detector_based_rules_apply_from_left_to_right_without_index_shift() -> None:
    anonymizer = _build_anonymizer()
    text = "a@x.com b@y.com c@z.com"

    result = anonymizer.anonymize_text(text)

    assert result.count("@") == 3
    assert "a@x.com" not in result
    assert "b@y.com" not in result
    assert "c@z.com" not in result
    assert result.split()[-1].endswith("@z.com")


def test_repeated_emails_are_all_masked() -> None:
    anonymizer = _build_anonymizer()
    text = "ana@example.com ana@example.com"

    result = anonymizer.anonymize_text(text)

    assert "ana@example.com" not in result
    assert result.split()[0] == result.split()[1]
