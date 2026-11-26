"""Builder fluido y Composition Root del componente."""

from __future__ import annotations

from typing import Self

from pii_anonymizer._internal.application.facade import DefaultPiiAnonymizer
from pii_anonymizer._internal.application.ports import PiiAnonymizer
from pii_anonymizer._internal.application.use_cases.anonymize_map import (
    AnonymizeMapUseCase,
)
from pii_anonymizer._internal.application.use_cases.anonymize_text import (
    AnonymizeTextUseCase,
)
from pii_anonymizer._internal.application.use_cases.audit_compliance import (
    AuditComplianceUseCase,
)
from pii_anonymizer._internal.application.use_cases.register_rule import (
    RegisterRuleUseCase,
)
from pii_anonymizer._internal.domain.exceptions import InvalidRuleError
from pii_anonymizer._internal.domain.models import AnonymizationRule
from pii_anonymizer._internal.domain.ports import (
    MaskingStrategy,
    SaltProvider,
    SensitivePatternDetector,
)
from pii_anonymizer._internal.infrastructure.detectors.credit_card import (
    CreditCardDetector,
)
from pii_anonymizer._internal.infrastructure.detectors.email import EmailDetector
from pii_anonymizer._internal.infrastructure.persistence.in_memory_rule_repo import (
    InMemoryRuleRepository,
)
from pii_anonymizer._internal.infrastructure.strategies.hashing import (
    HashMaskStrategy,
)
from pii_anonymizer._internal.infrastructure.strategies.partial import (
    PartialMaskStrategy,
)
from pii_anonymizer._internal.infrastructure.strategies.salt import (
    RandomSaltProvider,
)
from pii_anonymizer._internal.infrastructure.traversal.composite import (
    CompositeStructureTraverser,
)


class AnonymizerBuilder:
    """Ensambla las capas internas y expone una API fluida.

    Es el único punto del paquete que conoce simultáneamente los adaptadores
    de infraestructura y los casos de uso. El cliente recibe un
    :class:`PiiAnonymizer` ya configurado y nunca importa ``_internal``.

    Examples:
        >>> anonymizer = (
        ...     AnonymizerBuilder()
        ...     .with_default_rules()
        ...     .build()
        ... )
        >>> anonymizer.anonymize_text("contacto: ana.lopez@example.com")
        'contacto: an*****ez@example.com'
    """

    def __init__(self) -> None:
        """Inicializa un builder sin reglas ni proveedor de *salt* explícito."""
        self._pending_rules: dict[str, AnonymizationRule] = {}
        self._salt_provider: SaltProvider | None = None
        self._include_defaults = False

    def with_default_rules(self) -> Self:
        """Incluye las reglas por defecto al construir.

        Las reglas cubren ``email``, ``credit_card``, ``password``, ``token``
        y ``document_id``. Una regla agregada posteriormente con el mismo
        ``rule_id`` tiene prioridad.

        Returns:
            La misma instancia para encadenar llamadas.
        """
        self._include_defaults = True
        return self

    def add_rule(self, rule: AnonymizationRule) -> Self:
        """Agrega o reemplaza una regla pendiente de registro.

        Args:
            rule: Regla válida del dominio.

        Returns:
            La misma instancia para encadenar llamadas.

        Raises:
            InvalidRuleError: Si ``rule`` no es una ``AnonymizationRule``.
        """
        if not isinstance(rule, AnonymizationRule):
            raise InvalidRuleError(
                "add_rule espera una instancia de AnonymizationRule."
            )
        self._pending_rules[rule.rule_id] = rule
        return self

    def with_salt_provider(self, provider: SaltProvider) -> Self:
        """Define el proveedor de *salt* usado por las reglas con hash.

        Args:
            provider: Implementación concreta de :class:`SaltProvider`.

        Returns:
            La misma instancia para encadenar llamadas.

        Raises:
            ValueError: Si ``provider`` es ``None``.
        """
        if provider is None:
            raise ValueError("provider es obligatorio.")
        self._salt_provider = provider
        return self

    def build(self) -> PiiAnonymizer:
        """Construye la fachada con todos los adaptadores cableados.

        Cada invocación crea un repositorio y un recorredor nuevos, por lo
        que el resultado es independiente de construcciones anteriores.

        Returns:
            Fachada lista para usarse a través del puerto primario.
        """
        salt_provider = self._salt_provider or RandomSaltProvider()
        repository = InMemoryRuleRepository()

        if self._include_defaults:
            for rule in self._default_rules(salt_provider):
                repository.save(rule)
        for rule in self._pending_rules.values():
            repository.save(rule)

        traverser = CompositeStructureTraverser()
        return DefaultPiiAnonymizer(
            anonymize_map_use_case=AnonymizeMapUseCase(repository, traverser),
            anonymize_text_use_case=AnonymizeTextUseCase(repository),
            register_rule_use_case=RegisterRuleUseCase(repository),
            audit_compliance_use_case=AuditComplianceUseCase(repository, traverser),
        )

    @staticmethod
    def partial_mask_strategy(
        visible_prefix: int = 2,
        visible_suffix: int = 2,
        mask_char: str = "*",
    ) -> MaskingStrategy:
        """Crea una estrategia de enmascaramiento parcial.

        Args:
            visible_prefix: Caracteres visibles al inicio.
            visible_suffix: Caracteres visibles al final.
            mask_char: Carácter de enmascaramiento.

        Returns:
            Nueva instancia de ``PartialMaskStrategy``.
        """
        return PartialMaskStrategy(visible_prefix, visible_suffix, mask_char)

    @staticmethod
    def hash_mask_strategy(
        salt_provider: SaltProvider | None = None,
        prefix_length: int = 12,
    ) -> MaskingStrategy:
        """Crea una estrategia de hash salado.

        Args:
            salt_provider: Proveedor de *salt*; si se omite se crea uno
                aleatorio.
            prefix_length: Longitud del prefijo hexadecimal conservado.

        Returns:
            Nueva instancia de ``HashMaskStrategy``.
        """
        provider = salt_provider if salt_provider is not None else RandomSaltProvider()
        return HashMaskStrategy(provider, prefix_length)

    @staticmethod
    def email_detector() -> SensitivePatternDetector:
        """Crea un detector de correos electrónicos."""
        return EmailDetector()

    @staticmethod
    def credit_card_detector() -> SensitivePatternDetector:
        """Crea un detector de números de tarjeta de crédito."""
        return CreditCardDetector()

    def _default_rules(self, salt_provider: SaltProvider) -> list[AnonymizationRule]:
        """Construye el conjunto de reglas por defecto."""
        email_strategy = self.partial_mask_strategy()
        card_strategy = self.partial_mask_strategy(visible_prefix=0, visible_suffix=4)
        hash_strategy = self.hash_mask_strategy(salt_provider)

        return [
            AnonymizationRule(
                rule_id="email",
                strategy=email_strategy,
                field_names=("email", "e_mail", "correo", "correo_electronico"),
                detector=self.email_detector(),
            ),
            AnonymizationRule(
                rule_id="credit_card",
                strategy=card_strategy,
                field_names=("credit_card", "card_number", "numero_tarjeta"),
                detector=self.credit_card_detector(),
            ),
            AnonymizationRule(
                rule_id="password",
                strategy=hash_strategy,
                field_names=("password", "passwd", "contrasena", "contraseña"),
            ),
            AnonymizationRule(
                rule_id="token",
                strategy=hash_strategy,
                field_names=("token", "access_token", "refresh_token", "api_key"),
            ),
            AnonymizationRule(
                rule_id="document_id",
                strategy=hash_strategy,
                field_names=("document_id", "documento", "cedula", "cédula", "dni", "nit"),
            ),
        ]
