"""Pruebas del reporte de cumplimiento y su ausencia de datos sensibles."""

from __future__ import annotations

import dataclasses
import json

from pii_anonymizer.api import AnonymizerBuilder
from tests.doubles import FixedSaltProviderStub


def _build_anonymizer():
    return (
        AnonymizerBuilder()
        .with_default_rules()
        .with_salt_provider(FixedSaltProviderStub())
        .build()
    )


def test_report_counts_fields_categories_and_rules() -> None:
    anonymizer = _build_anonymizer()
    payload = {
        "email": "ana@example.com",
        "password": "super-secreto",
        "nested": {
            "card_number": "4111 1111 1111 1111",
            "note": "contactar a luis@test.co",
        },
        "age": 30,
        "missing": None,
        "tags": ["uno", "dos"],
    }

    report = anonymizer.audit_compliance(payload)

    assert report.total_fields_scanned == 8
    assert report.anonymized_fields_count == 4
    assert report.detected_categories == {
        "EMAIL": 2,
        "password": 1,
        "CREDIT_CARD": 1,
    }
    assert report.applied_rule_ids == ("email", "password", "credit_card")


def test_report_never_contains_original_pii_values() -> None:
    anonymizer = _build_anonymizer()
    sensitive_values = [
        "ana@example.com",
        "luis@test.co",
        "super-secreto",
        "4111 1111 1111 1111",
    ]
    payload = {
        "email": sensitive_values[0],
        "password": sensitive_values[2],
        "nested": {
            "card_number": sensitive_values[3],
            "note": f"escribir a {sensitive_values[1]}",
        },
    }

    report = anonymizer.audit_compliance(payload)
    serialized = repr(report) + json.dumps(
        dataclasses.asdict(report),
        ensure_ascii=False,
        default=str,
    )

    for value in sensitive_values:
        assert value not in serialized


def test_report_counts_each_detection_but_one_field() -> None:
    anonymizer = _build_anonymizer()
    payload = {"log": "a@x.com b@y.com"}

    report = anonymizer.audit_compliance(payload)

    assert report.total_fields_scanned == 1
    assert report.anonymized_fields_count == 1
    assert report.detected_categories == {"EMAIL": 2}
    assert report.applied_rule_ids == ("email",)


def test_empty_payload_produces_zeroed_report() -> None:
    anonymizer = _build_anonymizer()

    report = anonymizer.audit_compliance({})

    assert report.total_fields_scanned == 0
    assert report.anonymized_fields_count == 0
    assert report.detected_categories == {}
    assert report.applied_rule_ids == ()


def test_audit_does_not_mutate_payload() -> None:
    anonymizer = _build_anonymizer()
    payload = {"email": "ana@example.com", "nested": {"token": "abc"}}

    anonymizer.audit_compliance(payload)

    assert payload == {"email": "ana@example.com", "nested": {"token": "abc"}}


def test_document_id_numeric_is_anonymized() -> None:
    anonymizer = _build_anonymizer()

    report = anonymizer.audit_compliance({"document_id": 1029384756})

    assert report.total_fields_scanned == 1
    assert report.anonymized_fields_count == 1
    assert report.applied_rule_ids == ("document_id",)
    assert report.detected_categories == {"document_id": 1}
