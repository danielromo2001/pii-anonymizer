"""Pruebas del builder, las reglas y las fábricas de adaptadores."""

from __future__ import annotations

import hashlib

import pytest

from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    AnonymizerError,
    InvalidRuleError,
    PiiAnonymizer,
)
from tests.doubles import FixedSaltProviderStub, SpyMaskingStrategy


def test_builder_is_fluent_and_returns_pii_anonymizer() -> None:
    builder = AnonymizerBuilder()

    assert builder.with_default_rules() is builder
    assert builder.with_salt_provider(FixedSaltProviderStub()) is builder
    anonymizer = builder.build()

    assert isinstance(anonymizer, PiiAnonymizer)


def test_builder_without_default_rules_does_not_detect() -> None:
    anonymizer = AnonymizerBuilder().build()

    assert anonymizer.anonymize_text("ana@example.com") == "ana@example.com"
    assert anonymizer.anonymize_map({"email": "ana@example.com"}) == {
        "email": "ana@example.com"
    }


def test_register_rule_dynamically() -> None:
    anonymizer = AnonymizerBuilder().build()
    rule = AnonymizationRule(
        rule_id="nickname",
        strategy=AnonymizerBuilder.partial_mask_strategy(visible_prefix=1, visible_suffix=1),
        field_names=("nickname",),
    )

    anonymizer.register_rule(rule)
    result = anonymizer.anonymize_map({"NickName": "abcdef"})

    assert result == {"NickName": "a****f"}


def test_registering_same_rule_id_replaces_previous_rule() -> None:
    anonymizer = (
        AnonymizerBuilder()
        .with_salt_provider(FixedSaltProviderStub())
        .build()
    )
    anonymizer.register_rule(
        AnonymizationRule(
            "custom",
            AnonymizerBuilder.partial_mask_strategy(1, 1),
            field_names=("code",),
        )
    )
    assert anonymizer.anonymize_map({"code": "abcdef"}) == {"code": "a****f"}

    replacement = AnonymizationRule(
        "custom",
        AnonymizerBuilder.hash_mask_strategy(FixedSaltProviderStub()),
        field_names=("code",),
    )
    anonymizer.register_rule(replacement)
    result = anonymizer.anonymize_map({"code": "abcdef"})

    assert result["code"].startswith("hash:")
    assert result["code"] != "a****f"


def test_builder_add_rule_and_custom_detector_override() -> None:
    spy = SpyMaskingStrategy()
    override = AnonymizationRule(
        "email",
        spy,
        detector=AnonymizerBuilder.email_detector(),
    )
    anonymizer = AnonymizerBuilder().with_default_rules().add_rule(override).build()

    text_result = anonymizer.anonymize_text("contacto ana@example.com")
    map_result = anonymizer.anonymize_map({"email": "ana@example.com"})

    assert text_result == "contacto [SPY:1]"
    assert map_result == {"email": "[SPY:2]"}
    assert spy.calls == ["ana@example.com", "ana@example.com"]


def test_build_returns_independent_instances() -> None:
    builder = AnonymizerBuilder().with_default_rules()
    first = builder.build()
    second = builder.build()
    first.register_rule(
        AnonymizationRule(
            "pin",
            AnonymizerBuilder.partial_mask_strategy(0, 0),
            field_names=("pin",),
        )
    )

    assert first.anonymize_map({"pin": "1234"}) == {"pin": "****"}
    assert second.anonymize_map({"pin": "1234"}) == {"pin": "1234"}


def test_invalid_rule_construction_raises_domain_error() -> None:
    strategy = AnonymizerBuilder.partial_mask_strategy()

    with pytest.raises(InvalidRuleError):
        AnonymizationRule("   ", strategy, field_names=("email",))
    with pytest.raises(InvalidRuleError):
        AnonymizationRule("x", None, field_names=("email",))  # type: ignore[arg-type]
    with pytest.raises(InvalidRuleError):
        AnonymizationRule("x", strategy)
    with pytest.raises(InvalidRuleError):
        AnonymizationRule("x", strategy, field_names=("email", " "))

    assert issubclass(InvalidRuleError, AnonymizerError)


def test_rule_normalizes_identifier_and_field_names() -> None:
    rule = AnonymizationRule(
        "  legacy_id  ",
        AnonymizerBuilder.partial_mask_strategy(),
        field_names=" email ",
    )

    assert rule.rule_id == "legacy_id"
    assert rule.field_names == ("email",)


def test_rule_accepts_none_field_names_when_detector_is_present() -> None:
    rule = AnonymizationRule(
        "detector_only",
        AnonymizerBuilder.partial_mask_strategy(),
        field_names=None,  # type: ignore[arg-type]
        detector=AnonymizerBuilder.email_detector(),
    )

    assert rule.field_names == ()


def test_register_rule_rejects_non_rule_objects() -> None:
    anonymizer = AnonymizerBuilder().build()

    with pytest.raises(InvalidRuleError):
        anonymizer.register_rule(None)  # type: ignore[arg-type]
    with pytest.raises(InvalidRuleError):
        AnonymizerBuilder().add_rule("no-es-regla")  # type: ignore[arg-type]


def test_builder_rejects_none_salt_provider() -> None:
    with pytest.raises(ValueError):
        AnonymizerBuilder().with_salt_provider(None)  # type: ignore[arg-type]


def test_partial_mask_strategy_factory() -> None:
    strategy = AnonymizerBuilder.partial_mask_strategy()

    assert strategy.mask("john.doe@example.com") == "jo****oe@example.com"
    assert strategy.mask("abcdef") == "ab**ef"
    assert strategy.mask("ab") == "**"
    assert strategy.mask("") == ""


def test_partial_mask_strategy_with_custom_parameters() -> None:
    strategy = AnonymizerBuilder.partial_mask_strategy(0, 4, "#")

    assert strategy.mask("4111111111111111") == "############1111"


def test_partial_mask_strategy_validates_parameters() -> None:
    with pytest.raises(ValueError):
        AnonymizerBuilder.partial_mask_strategy(visible_prefix=-1)
    with pytest.raises(ValueError):
        AnonymizerBuilder.partial_mask_strategy(visible_suffix=-1)
    with pytest.raises(ValueError):
        AnonymizerBuilder.partial_mask_strategy(mask_char="**")


def test_hash_mask_strategy_is_deterministic_with_fixed_salt() -> None:
    strategy = AnonymizerBuilder.hash_mask_strategy(
        FixedSaltProviderStub(),
        prefix_length=12,
    )
    expected = "hash:" + hashlib.sha256(
        "fixed-test-salt-2026super-secreto".encode("utf-8")
    ).hexdigest()[:12]

    assert strategy.mask("super-secreto") == expected
    assert strategy.mask("super-secreto") == expected


def test_hash_mask_strategy_respects_prefix_length() -> None:
    strategy = AnonymizerBuilder.hash_mask_strategy(
        FixedSaltProviderStub(),
        prefix_length=8,
    )

    result = strategy.mask("x")

    assert result.startswith("hash:")
    assert len(result) == len("hash:") + 8


def test_hash_mask_strategy_defaults_to_random_salt_provider() -> None:
    strategy = AnonymizerBuilder.hash_mask_strategy()

    assert strategy.mask("valor").startswith("hash:")


def test_hash_mask_strategy_validates_prefix_length() -> None:
    with pytest.raises(ValueError):
        AnonymizerBuilder.hash_mask_strategy(prefix_length=0)
    with pytest.raises(ValueError):
        AnonymizerBuilder.hash_mask_strategy(prefix_length=65)


def test_email_detector_returns_text_matches() -> None:
    detector = AnonymizerBuilder.email_detector()

    matches = detector.detect("hola ana@example.com y luis@test.co")

    assert detector.category == "EMAIL"
    assert [match.matched_text for match in matches] == [
        "ana@example.com",
        "luis@test.co",
    ]
    assert matches[0].category == "EMAIL"
    assert matches[0].start == 5
    assert matches[0].end == 20


def test_credit_card_detector_returns_text_matches() -> None:
    detector = AnonymizerBuilder.credit_card_detector()

    matches = detector.detect("pago 4111-1111-1111-1111 fin")

    assert detector.category == "CREDIT_CARD"
    assert len(matches) == 1
    assert matches[0].matched_text == "4111-1111-1111-1111"
    assert detector.detect("no 123456789012") == []


def test_default_rules_can_be_overridden_by_id() -> None:
    spy = SpyMaskingStrategy(tag="OVERRIDE")
    override = AnonymizationRule(
        "password",
        spy,
        field_names=("password",),
    )
    anonymizer = AnonymizerBuilder().with_default_rules().add_rule(override).build()

    assert anonymizer.anonymize_map({"password": "secreto"}) == {
        "password": "[OVERRIDE:1]"
    }
