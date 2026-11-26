# pii-anonymizer

Componente de software reutilizable para **detectar, enmascarar y auditar Información Personal Identificable (PII)** en memoria, tanto en texto plano como en estructuras anidadas (`dict`, `list`).

La versión actual es **1.0.0** y está construida con Python 3.11+ y Arquitectura Limpia, sin dependencias de infraestructura externas.

---

## 1. Propósito

`pii-anonymizer` resuelve un problema frecuente en aplicaciones que registran trazas, exportan datos o alimentan modelos analíticos: evitar que correos, tarjetas, contraseñas, tokens o documentos de identidad lleguen a destinos no autorizados.

El componente ofrece cuatro capacidades estables:

| Operación | Entrada | Salida |
| --- | --- | --- |
| `anonymize_map` | Diccionario anidado | Copia sanitizada sin mutar la entrada |
| `anonymize_text` | Texto plano / línea de log | Texto con PII enmascarada |
| `register_rule` | `AnonymizationRule` | Regla registrada o reemplazada |
| `audit_compliance` | Diccionario anidado | `ComplianceReport` con conteos, sin valores PII |

## 2. Características principales

- **Arquitectura Limpia:** capas `domain`, `application`, `infrastructure` y una frontera pública `api`.
- **API mínima y estable:** todo el contrato se reexporta desde `pii_anonymizer.api`.
- **Extensible sin modificar el núcleo:** el cliente implementa `MaskingStrategy`, `SensitivePatternDetector` o `SaltProvider`.
- **Sin mutación:** los recorridos producen diccionarios y listas nuevos.
- **Auditoría segura:** el reporte contiene únicamente conteos y metadatos, nunca valores sensibles.
- **Cero dependencias de ejecución:** solo biblioteca estándar (`abc`, `dataclasses`, `hashlib`, `re`, `secrets`, `typing`, `copy`).
- **Cobertura de pruebas:** superior al 85 % exigido; la suite actual alcanza el 97,70 %.

## 3. Requisitos

- Python **3.11** o superior.
- `pip` actualizado.
- Para desarrollo: `pytest` y `pytest-cov` (incluidos en el extra `dev`).

## 4. Instalación

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

Si solo se requiere la librería en tiempo de ejecución:

```bash
pip install -e .
```

## 5. Quickstart

```python
from pii_anonymizer.api import AnonymizerBuilder

anonymizer = AnonymizerBuilder().with_default_rules().build()

payload = {
    "customer": {
        "email": "ana.lopez@example.com",
        "password": "ClaveSuperSecreta2026",
        "card_number": "4111 1111 1111 1111",
    },
    "notes": "Escribir a soporte@example.com",
}

# 1) Estructuras anidadas (sin mutar el original)
sanitized = anonymizer.anonymize_map(payload)
print(sanitized)

# 2) Texto plano
log_line = "INFO pago de ana.lopez@example.com con 4111 1111 1111 1111"
print(anonymizer.anonymize_text(log_line))

# 3) Auditoría sin datos sensibles
report = anonymizer.audit_compliance(payload)
print(report.total_fields_scanned)
print(report.detected_categories)
```

Salida orientativa:

```text
{'customer': {'email': 'an*****ez@example.com', 'password': 'hash:...', 'card_number': '***************1111'}, 'notes': 'Escribir a so***te@example.com'}
INFO pago de an*****ez@example.com con ***************1111
4
{'EMAIL': 2, 'password': 1, 'CREDIT_CARD': 1}
```

> El *hash* de contraseñas utiliza un *salt* aleatorio distinto en cada ejecución. Para pruebas deterministas se inyecta un `SaltProvider` fijo con `with_salt_provider(...)`.

### Registrar una regla propia

```python
from pii_anonymizer.api import AnonymizationRule, AnonymizerBuilder

anonymizer = AnonymizerBuilder().with_default_rules().build()

anonymizer.register_rule(
    AnonymizationRule(
        rule_id="employee_code",
        strategy=AnonymizerBuilder.partial_mask_strategy(1, 1),
        field_names=("employee_code", "codigo_empleado"),
    )
)

print(anonymizer.anonymize_map({"employee_code": "EMP-2026"}))
```

## 6. API pública

La superficie pública se exporta en `pii_anonymizer/__init__.py` y `pii_anonymizer/api/__init__.py` mediante `__all__`:

- `PiiAnonymizer` — puerto primario con las cuatro operaciones.
- `AnonymizerBuilder` — Builder fluido y Composition Root.
- `MaskingStrategy` — punto de extensión para transformar valores.
- `SensitivePatternDetector` — punto de extensión para detectar patrones.
- `SaltProvider` — abstracción del *salt* criptográfico.
- `AnonymizationRule` — regla inmutable por campo y/o detector.
- `TextMatch` — coincidencia detectada en texto.
- `ComplianceReport` — reporte agregado de auditoría.
- `AnonymizerError` — excepción base.
- `InvalidRuleError` — error de regla inválida.

### Reglas por defecto

`with_default_rules()` registra cinco reglas:

| `rule_id` | Campos reconocidos (sin distinguir mayúsculas) | Estrategia | Detector |
| --- | --- | --- | --- |
| `email` | `email`, `e_mail`, `correo`, `correo_electronico` | Parcial con dominio visible | `EmailDetector` |
| `credit_card` | `credit_card`, `card_number`, `numero_tarjeta` | Parcial con últimos 4 | `CreditCardDetector` |
| `password` | `password`, `passwd`, `contrasena`, `contraseña` | Hash salado | — |
| `token` | `token`, `access_token`, `refresh_token`, `api_key` | Hash salado | — |
| `document_id` | `document_id`, `documento`, `cedula`, `cédula`, `dni`, `nit` | Hash salado | — |

## 7. Arquitectura Limpia

```text
pii-anonymizer/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── src/
│   └── pii_anonymizer/
│       ├── __init__.py
│       ├── api/                               # Frontera pública + Composition Root
│       │   ├── __init__.py
│       │   └── builder.py
│       └── _internal/                         # Implementación privada
│           ├── domain/                        # Núcleo puro
│           │   ├── exceptions.py
│           │   ├── models.py
│           │   └── ports.py
│           ├── application/                   # Casos de uso y servicios
│           │   ├── ports.py
│           │   ├── facade.py
│           │   ├── services/detector_chain.py
│           │   └── use_cases/
│           │       ├── anonymize_map.py
│           │       ├── anonymize_text.py
│           │       ├── register_rule.py
│           │       └── audit_compliance.py
│           └── infrastructure/                # Adaptadores concretos
│               ├── persistence/in_memory_rule_repo.py
│               ├── traversal/composite.py
│               ├── strategies/{partial,hashing,salt}.py
│               └── detectors/{email,credit_card}.py
├── tests/
├── examples/demo_cli.py
└── docs/
```

Regla de dependencias:

```text
domain ← application ← infrastructure
   ↑           ↑               ↑
   └────────── api ────────────┘
```

- `domain` no importa ninguna otra capa ni librerías externas.
- `application` solo depende de `domain`.
- `infrastructure` depende de `domain` y `application`.
- `api` conoce todas las capas y actúa como único *Composition Root*.

## 8. Pruebas y cobertura

```bash
python -m pytest --cov=pii_anonymizer --cov-report=term-missing
```

La suite cubre:

- Diccionarios simples, anidados a tres o más niveles y listas de diccionarios.
- No mutación de la entrada y manejo de `None` y primitivos.
- Múltiples correos y tarjetas en una misma línea de log.
- Conteos del reporte y ausencia estricta de PII en el mismo.
- Registro dinámico, reemplazo y validación de reglas.
- Extensibilidad con estrategias y detectores definidos solo con la API pública.

Configuración relevante de `pyproject.toml`: cobertura mínima `fail_under = 85`.

## 9. Demostración ejecutable

```bash
python examples/demo_cli.py
```

El script usa exclusivamente la API pública y muestra las cuatro funcionalidades, además de una extensión `PhoneNumberDetector` + `RedactionTagStrategy`.

## 10. Aplicación de ejemplo: taller mecánico

El repositorio incluye una app web local en `workshop_app/` para probar la
librería en un caso de uso realista: gestión de clientes, vehículos y órdenes de
trabajo de un taller mecánico.

```powershell
pip install -r workshop_app/requirements.txt
python -m workshop_app.app
```

Abre `http://127.0.0.1:5000`. La app incluye:

- modo privacidad global para enmascarar datos en listados y fichas;
- auditoría con `audit_compliance`;
- logs sanitizados con `anonymize_text`;
- exportación JSON anonimizada con `anonymize_map`;
- laboratorio de texto para probar detección de correos, tarjetas y teléfonos.

Consulta [workshop_app/README.md](workshop_app/README.md) para el recorrido
completo y las instrucciones de instalación.

## 11. Documentación

### Funcional

- [Problema y escenarios](docs/01-funcional/problema-y-escenarios.md)
- [Requerimientos funcionales](docs/01-funcional/requerimientos-funcionales.md)
- [Guía de uso](docs/01-funcional/guia-de-uso.md)
- [Guía de extensión](docs/01-funcional/guia-de-extension.md)

### Técnica

- [Calidad ISO/IEC 25010](docs/02-tecnica/calidad-iso25010.md)
- [Arquitectura C4](docs/02-tecnica/arquitectura-c4.md)
- [Diagramas UML](docs/02-tecnica/diagramas-uml.md)
- [Matriz SOLID/GRASP](docs/02-tecnica/matriz-solid-grasp.md)
- ADR-001: [Arquitectura Limpia y aislamiento de la API](docs/02-tecnica/adr/001-arquitectura-limpia-y-aislamiento-api.md)
- ADR-002: [Patrón creacional Builder](docs/02-tecnica/adr/002-patron-creacional-builder.md)
- ADR-003: [Patrón estructural Composite](docs/02-tecnica/adr/003-patron-estructural-composite.md)
- ADR-004: [Patrones de comportamiento Strategy y Chain](docs/02-tecnica/adr/004-patrones-comportamiento-strategy-chain.md)

## 12. Notas de seguridad

- Las estrategias parciales conservan extremos para mantener legibilidad operativa; no deben usarse como único control en datos de altísima sensibilidad.
- El *hash* es irreversible, pero un espacio de valores pequeño podría ser atacado por fuerza bruta si el *salt* se filtra. Proteja el `SaltProvider` en producción.
- `ComplianceReport` está diseñado para no contener valores PII; aun así, evite registrar el payload original junto al reporte.
- La comparación de nombres de campo es *case-insensitive*, pero no normaliza acentos ni alias arbitrarios: registre las variantes necesarias.
