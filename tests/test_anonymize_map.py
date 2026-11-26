"""Pruebas de anonimización de estructuras anidadas."""

from __future__ import annotations

import copy

import pytest

from pii_anonymizer.api import AnonymizerBuilder
from tests.doubles import FixedSaltProviderStub


def _build_anonymizer():
    return (
        AnonymizerBuilder()
        .with_default_rules()
        .with_salt_provider(FixedSaltProviderStub())
        .build()
    )


def test_anonymizes_simple_dictionary_without_mutating_input() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "email": "ana@example.com",
        "password": "super-secreto",
        "age": 30,
    }
    original = copy.deepcopy(payload)

    result = anonymizer.anonymize_map(payload)

    assert payload == original
    assert result is not payload
    assert result["email"] != payload["email"]
    assert "@example.com" in result["email"]
    assert result["password"].startswith("hash:")
    assert result["age"] == 30


def test_anonymizes_three_levels_and_list_of_dictionaries() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "customer": {
            "profile": {
                "email": "deep@example.com",
                "password": "clave-123",
                "document_id": "1098765432",
            },
            "cards": [
                {"card_number": "4111 1111 1111 1111", "alias": "principal"},
                {"card_number": "5500-0000-0000-0004", "alias": "respaldo"},
            ],
        },
        "status": "ACTIVE",
    }
    snapshot = copy.deepcopy(payload)

    result = anonymizer.anonymize_map(payload)

    assert payload == snapshot
    assert result["customer"] is not payload["customer"]
    profile = result["customer"]["profile"]
    assert profile["email"] != "deep@example.com"
    assert profile["password"].startswith("hash:")
    assert profile["document_id"].startswith("hash:")
    assert [item["card_number"] for item in result["customer"]["cards"]] != [
        "4111 1111 1111 1111",
        "5500-0000-0000-0004",
    ]
    assert [item["alias"] for item in result["customer"]["cards"]] == [
        "principal",
        "respaldo",
    ]
    assert result["status"] == "ACTIVE"


def test_field_name_matching_is_case_insensitive() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "EMAIL": "UPPER@example.com",
        "Password": "ClaveSegura",
        "Access_Token": "token-value",
    }

    result = anonymizer.anonymize_map(payload)

    assert result["EMAIL"] != payload["EMAIL"]
    assert result["Password"].startswith("hash:")
    assert result["Access_Token"].startswith("hash:")


def test_preserves_none_and_primitive_types() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "none_value": None,
        "integer": 42,
        "float": 3.5,
        "boolean": True,
        "scalars": [1, 2, None, False, "texto sin pii"],
    }

    result = anonymizer.anonymize_map(payload)

    assert result == payload
    assert result is not payload
    assert result["scalars"] is not payload["scalars"]


def test_detects_pii_inside_free_text_values() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "notes": "Escribir a soporte@example.com o llamar; tarjeta 4111 1111 1111 1111",
    }

    result = anonymizer.anonymize_map(payload)

    assert "soporte@example.com" not in result["notes"]
    assert "4111 1111 1111 1111" not in result["notes"]
    assert "@example.com" in result["notes"]


def test_empty_dictionary_returns_new_empty_dictionary() -> None:
    anonymizer = _build_anonymizer()
    payload: dict[str, object] = {}

    result = anonymizer.anonymize_map(payload)

    assert result == {}
    assert result is not payload


def test_rejects_non_dictionary_input() -> None:
    anonymizer = _build_anonymizer()

    with pytest.raises(TypeError):
        anonymizer.anonymize_map(["no", "es", "dict"])  # type: ignore[arg-type]


def test_nested_dictionaries_and_lists_are_new_objects() -> None:
    anonymizer = _build_anonymizer()
    payload = {"a": {"b": [{"email": "n@example.com"}]}}

    result = anonymizer.anonymize_map(payload)

    assert result["a"] is not payload["a"]
    assert result["a"]["b"] is not payload["a"]["b"]
    assert result["a"]["b"][0] is not payload["a"]["b"][0]


def test_none_bool_and_unsupported_types_in_sensitive_fields_are_preserved() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "password": None,
        "token": True,
        "email": ("a@b.com",),
    }

    result = anonymizer.anonymize_map(payload)

    assert result["password"] is None
    assert result["token"] is True
    assert result["email"] == ("a@b.com",)
