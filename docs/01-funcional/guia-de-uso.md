# Guía de uso

Esta guía muestra las cuatro funcionalidades de la API pública con entradas, salidas y manejo de errores. Todos los ejemplos importan únicamente desde `pii_anonymizer.api`.

## 1. Instalación y primer uso

```bash
pip install -e ".[dev]"
```

```python
from pii_anonymizer.api import AnonymizerBuilder

anonymizer = AnonymizerBuilder().with_default_rules().build()
```

`build()` retorna un objeto que implementa el puerto `PiiAnonymizer`. Las reglas por defecto cubren correo, tarjeta, contraseña, token y documento de identidad.

## 2. `anonymize_map`: estructuras anidadas

### 2.1 Ejemplo básico

```python
payload = {
    "customer": {
        "name": "Ana",
        "email": "ana.lopez@example.com",
        "password": "ClaveSuperSecreta2026",
        "card_number": "4111 1111 1111 1111",
        "document_id": 1029384756,
    },
    "notes": ["Escribir a soporte@example.com"],
}

sanitized = anonymizer.anonymize_map(payload)

print(sanitized)
```

Salida orientativa:

```python
{
    "customer": {
        "name": "Ana",
        "email": "an*****ez@example.com",
        "password": "hash:3f9a0c7d2e11",
        "card_number": "***************1111",
        "document_id": "hash:7a12bc90de34",
    },
    "notes": ["Escribir a so***te@example.com"],
}
```

Observaciones:

- `name` no coincide con ninguna regla ni contiene PII detectable: se conserva.
- `email` y `card_number` se enmascaran de forma parcial porque así lo definen las reglas por defecto.
- `password` y `document_id` convierten el valor en un hash salado. El `document_id` numérico se transforma en cadena para poder enmascararlo.
- La nota libre se examina con los detectores activos aunque su campo no se llame `email`.

### 2.2 No mutación

```python
import copy

original = copy.deepcopy(payload)
result = anonymizer.anonymize_map(payload)

assert payload == original          # la entrada no cambió
assert result is not payload        # la raíz es nueva
assert result["customer"] is not payload["customer"]
```

El recorrido construye diccionarios y listas nuevos. Los objetos de valor inmutables (cadenas, números) se reutilizan sin riesgo.

### 2.3 Comparación de campos sin distinguir mayúsculas

```python
print(anonymizer.anonymize_map({
    "EMAIL": "upper@example.com",
    "Password": "clave",
    "Access_Token": "abc-123",
}))
```

`EMAIL`, `Password` y `Access_Token` coinciden con las reglas `email`, `password` y `token` respectivamente.

### 2.4 Valores especiales

| Valor de un campo sensible | Resultado |
| --- | --- |
| `"texto"` | Se pasa a la estrategia de la regla. |
| `123` / `3.14` | Se convierte a texto y se enmascara; se retorna la cadena. |
| `None` | Se conserva como `None`. |
| `True` / `False` | Se conserva el booleano. |
| `dict` / `list` | Se recorre como contenedor; la regla de campo no se aplica al contenedor. |

Un campo no sensible conserva su tipo original. Las listas se recorren completas, incluidas listas de diccionarios.

### 2.5 Uso de un *salt* determinista

El proveedor por defecto genera un *salt* aleatorio nuevo en cada llamada. Para pruebas o procesos que necesitan hashes estables:

```python
from pii_anonymizer.api import AnonymizerBuilder, SaltProvider


class FixedSaltProvider(SaltProvider):
    def get_salt(self) -> str:
        return "salt-de-pruebas-2026"


anonymizer = (
    AnonymizerBuilder()
    .with_default_rules()
    .with_salt_provider(FixedSaltProvider())
    .build()
)
```

> No use un *salt* fijo o público en producción. Un *salt* filtrado permitiría ataques de diccionario sobre espacios de valores pequeños.

## 3. `anonymize_text`: texto plano y logs

```python
log_line = (
    "INFO pago aprobado para ana.lopez@example.com con la tarjeta "
    "4111 1111 1111 1111; copia a compras@example.com"
)

print(anonymizer.anonymize_text(log_line))
```

Salida orientativa:

```text
INFO pago aprobado para an*****ez@example.com con la tarjeta ***************1111; copia a co***as@example.com
```

Características:

- Se aplican todas las reglas con detector, no las reglas que solo declaran `field_names`.
- Varias coincidencias en la misma cadena se resuelven de derecha a izquierda.
- Si hay solapamiento, gana la coincidencia que inicia primero y, a igual inicio, la más larga.
- Un texto vacío retorna `""`; un texto sin PII retorna el mismo contenido.

Ejemplos adicionales:

```python
assert anonymizer.anonymize_text("") == ""
assert anonymizer.anonymize_text("servicio iniciado") == "servicio iniciado"

print(anonymizer.anonymize_text("a@x.com b@y.com c@z.com"))
# *@x.com *@y.com *@z.com
```

## 4. `register_rule`: reglas dinámicas

### 4.1 Regla por nombre de campo

```python
from pii_anonymizer.api import AnonymizationRule

anonymizer.register_rule(
    AnonymizationRule(
        rule_id="employee_code",
        strategy=AnonymizerBuilder.partial_mask_strategy(2, 2),
        field_names=("employee_code", "codigo_empleado"),
    )
)

print(anonymizer.anonymize_map({"Employee_Code": "EMP-2026"}))
# {'Employee_Code': 'EM****26'}
```

### 4.2 Regla por detector

```python
rule = AnonymizationRule(
    rule_id="email_redacted",
    strategy=AnonymizerBuilder.partial_mask_strategy(),
    detector=AnonymizerBuilder.email_detector(),
)

anonymizer.register_rule(rule)
print(anonymizer.anonymize_text("contacto ana@example.com"))
```

La regla se aplica a cualquier texto que el detector reconozca, sin depender del nombre del campo.

### 4.3 Reemplazo por identificador

```python
anonymizer.register_rule(
    AnonymizationRule(
        rule_id="employee_code",
        strategy=AnonymizerBuilder.hash_mask_strategy(),
        field_names=("employee_code",),
    )
)
```

Al registrar otra regla con `rule_id="employee_code"`, la anterior se reemplaza. El repositorio mantiene una sola regla por identificador.

### 4.4 Reglas por defecto y prioridad

```python
from pii_anonymizer.api import AnonymizationRule, MaskingStrategy


class Redact(MaskingStrategy):
    def mask(self, raw_value: str) -> str:
        return "[REDACTED]"


anonymizer = (
    AnonymizerBuilder()
    .with_default_rules()
    .add_rule(
        AnonymizationRule(
            rule_id="password",
            strategy=Redact(),
            field_names=("password",),
        )
    )
    .build()
)

assert anonymizer.anonymize_map({"password": "x"}) == {"password": "[REDACTED]"}
```

Una regla agregada con el mismo `rule_id` que una regla por defecto tiene prioridad, porque el builder guarda las reglas del usuario después de las predeterminadas.

## 5. `audit_compliance`: auditoría sin PII

```python
payload = {
    "email": "ana@example.com",
    "password": "secreto",
    "nested": {
        "card_number": "4111 1111 1111 1111",
        "note": "contactar a luis@test.co",
    },
    "age": 30,
}

report = anonymizer.audit_compliance(payload)

print(report.total_fields_scanned)      # 5
print(report.anonymized_fields_count)   # 4
print(report.detected_categories)       # {'EMAIL': 2, 'password': 1, 'CREDIT_CARD': 1}
print(report.applied_rule_ids)          # ('email', 'password', 'credit_card')
```

### 5.1 Semántica de los conteos

| Campo | Significado |
| --- | --- |
| `total_fields_scanned` | Valores escalares visitados (incluye `None`, booleanos y elementos de listas). |
| `anonymized_fields_count` | Valores escalares transformados al menos una vez. |
| `detected_categories` | Hallazgos por categoría o regla; un campo con dos correos suma 2 a `EMAIL`. |
| `applied_rule_ids` | Identificadores únicos de reglas aplicadas, en orden de uso. |

Para reglas de campo se usa la categoría del detector si existe; si no, se usa el `rule_id`. Por eso una contraseña aparece como `password` y una tarjeta como `CREDIT_CARD`.

### 5.2 Garantía de no exposición

```python
import dataclasses
import json

serialized = json.dumps(dataclasses.asdict(report), ensure_ascii=False)
assert "ana@example.com" not in serialized
assert "luis@test.co" not in serialized
assert "secreto" not in serialized
```

El reporte contiene solo números, identificadores de reglas y nombres de categorías. No contiene valores de entrada ni la copia sanitizada.

## 6. Manejo de errores

### 6.1 `InvalidRuleError`

Se lanza al construir una regla inválida o al registrar un objeto que no es una regla:

```python
from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    InvalidRuleError,
    MaskingStrategy,
)

strategy = AnonymizerBuilder.partial_mask_strategy()

try:
    AnonymizationRule("", strategy)              # sin field_names ni detector
except InvalidRuleError as error:
    print(error)

try:
    AnonymizationRule("x", None, ("email",))     # estrategia nula
except InvalidRuleError as error:
    print(error)

try:
    AnonymizerBuilder().build().register_rule(None)
except InvalidRuleError as error:
    print(error)
```

### 6.2 `AnonymizerError`

`InvalidRuleError` hereda de `AnonymizerError`, por lo que puede capturarse de forma genérica:

```python
from pii_anonymizer.api import AnonymizerError

try:
    anonymizer.register_rule(None)
except AnonymizerError:
    ...
```

### 6.3 `ValueError` y `TypeError`

- `ValueError`: parámetros inválidos de las fábricas, por ejemplo `visible_prefix=-1`, `mask_char="**"`, `prefix_length=0` o un `with_salt_provider(None)`.
- `TypeError`: `anonymize_map` o `audit_compliance` reciben algo distinto de un `dict`.

```python
try:
    anonymizer.anonymize_map(["no", "es", "un", "dict"])
except TypeError:
    ...
```

### 6.4 Tabla de excepciones

| Excepción | Origen | Ejemplo |
| --- | --- | --- |
| `InvalidRuleError` | Invariantes de `AnonymizationRule` / `register_rule` | `rule_id` vacío, estrategia nula, sin criterios. |
| `AnonymizerError` | Base de errores de dominio | Captura genérica. |
| `ValueError` | Configuración de adaptadores | Máscara inválida, longitudes negativas. |
| `TypeError` | Contrato de entrada | `anonymize_map("texto")`. |

## 7. Fábricas de adaptadores

| Método estático | Retorna | Uso |
| --- | --- | --- |
| `AnonymizerBuilder.partial_mask_strategy(prefix, suffix, char)` | `MaskingStrategy` | Conserva extremos y oculta el centro. |
| `AnonymizerBuilder.hash_mask_strategy(provider, length)` | `MaskingStrategy` | Genera `hash:<sha256[:length]>`. |
| `AnonymizerBuilder.email_detector()` | `SensitivePatternDetector` | Detecta correos. |
| `AnonymizerBuilder.credit_card_detector()` | `SensitivePatternDetector` | Detecta tarjetas de 13 a 19 dígitos. |

Estas fábricas permiten configurar extensiones sin importar `pii_anonymizer._internal`.

## 8. Buenas prácticas

1. Construya el anonimizador una vez al iniciar el servicio y reutilícelo.
2. Registre reglas adicionales durante la configuración; el repositorio en memoria no está pensado para escrituras concurrentes intensivas.
3. Inyecte un `SaltProvider` gestionado como secreto si necesita hashes estables.
4. Audite antes de exportar y conserve el reporte, nunca el *payload* original, en sistemas de observabilidad.
5. Revise los falsos positivos de los detectores antes de aplicarlos a datos de negocio críticos.
6. Para campos de altísima sensibilidad, prefiera una estrategia de redacción total sobre una parcial.
7. No dependa de `pii_anonymizer._internal`: cualquier símbolo fuera de `pii_anonymizer.api` es privado y puede cambiar.
