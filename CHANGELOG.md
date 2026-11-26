# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto se adhiere a [Versionado Semántico](https://semver.org/lang/es/).

## Unreleased

### Added

- Aplicación de demostración `workshop_app/` con Flask y SQLite para gestionar
  clientes, vehículos y órdenes de un taller mecánico.
- Modo privacidad, auditoría, logs sanitizados, exportación JSON anonimizada y
  laboratorio de texto en la app de demostración.
- Reglas de ejemplo para teléfonos, nombres, direcciones y VIN usando solo la
  API pública de `pii-anonymizer`.
- Pruebas de humo de la app con Flask test client.

## 1.0.0 - 2026-11-24

### Added

- Paquete Python instalable `pii-anonymizer` con Python 3.11+ y cero dependencias de ejecución.
- Arquitectura Limpia con capas `domain`, `application`, `infrastructure` y frontera pública `api`.
- Objetos de valor inmutables `AnonymizationRule`, `TextMatch` y `ComplianceReport`.
- Excepciones de dominio `AnonymizerError` e `InvalidRuleError`.
- Puertos de extensión `MaskingStrategy`, `SensitivePatternDetector` y `SaltProvider`.
- Puerto primario `PiiAnonymizer` con las operaciones `anonymize_map`, `anonymize_text`, `register_rule` y `audit_compliance`.
- Casos de uso `AnonymizeMapUseCase`, `AnonymizeTextUseCase`, `RegisterRuleUseCase` y `AuditComplianceUseCase`.
- Fachada `DefaultPiiAnonymizer` como *Facade/Controller*.
- Cadena de detección `DetectorChain` con resolución de solapamientos y reemplazos de derecha a izquierda.
- Recorrido `Composite` con nodos `DataNode`, `DictNode`, `ListNode` y `ScalarNode`, y contexto *stateless* por invocación.
- Estrategias concretas `PartialMaskStrategy`, `HashMaskStrategy` y `RandomSaltProvider`.
- Detectores `EmailDetector` y `CreditCardDetector`.
- Repositorio `InMemoryRuleRepository` con búsqueda de campos *case-insensitive*.
- `AnonymizerBuilder` fluido con reglas por defecto, inyección de `SaltProvider` y fábricas de adaptadores.
- Reglas por defecto para `email`, `credit_card`, `password`, `token` y `document_id`.
- Suite de pruebas con 49 pruebas, dobles `FixedSaltProviderStub` y `SpyMaskingStrategy`, y cobertura del 97,70 %.
- Aplicación de ejemplo `examples/demo_cli.py` con extensión de teléfonos.
- Documentación funcional (problema, requerimientos, uso, extensión) y técnica (ISO/IEC 25010, C4, UML, SOLID/GRASP y cuatro ADR).

### Security

- La auditoría expone únicamente conteos y metadatos; no incluye valores PII en claro.
- Las operaciones sobre `dict` y `list` retornan copias y nunca mutan la entrada.
- El *salt* se obtiene mediante `secrets.token_hex(16)` en el proveedor por defecto.
