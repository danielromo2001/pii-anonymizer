# Guía de extensión

Esta guía explica cómo agregar comportamientos propios **sin modificar la librería** y **sin importar `pii_anonymizer._internal`**. Es el mecanismo que materializa el principio Abierto/Cerrado (OCP).

## 1. Puntos de extensión

| Puerto | Propósito | Método obligatorio |
| --- | --- | --- |
| `MaskingStrategy` | Transformar un valor sensible | `mask(raw_value: str) -> str` |
| `SensitivePatternDetector` | Encontrar PII en texto | `category` (propiedad) y `detect(text) -> list[TextMatch]` |
| `SaltProvider` | Proveer el *salt* del hash | `get_salt() -> str` |

Los tres se reexportan desde `pii_anonymizer.api`. Una extensión correcta solo necesita implementar la interfaz y registrarse mediante una `AnonymizationRule`.

## 2. Paso 1: implementar una estrategia

```python
from pii_anonymizer.api import MaskingStrategy


class RedactionTagStrategy(MaskingStrategy):
    """Reemplaza cualquier valor por una etiqueta fija."""

    def __init__(self, tag: str = "[REDACTED]") -> None:
        self._tag = tag

    def mask(self, raw_value: str) -> str:
        return self._tag
```

Buenas prácticas:

- No registrar el valor original en logs ni en atributos persistentes.
- Retornar siempre una cadena.
- Mantener la estrategia sin estado mutable compartido, salvo que se sincronice explícitamente.
- Documentar el formato de salida para que el consumidor sepa qué esperar.

### Estrategia basada en fábricas existentes

Si no necesita una transformación nueva, reutilice las fábricas:

```python
partial = AnonymizerBuilder.partial_mask_strategy(2, 2)
hashed = AnonymizerBuilder.hash_mask_strategy(prefix_length=16)
```

## 3. Paso 2: implementar un detector

```python
import re

from pii_anonymizer.api import SensitivePatternDetector, TextMatch


class ColombianCedulaDetector(SensitivePatternDetector):
    """Detecta cédulas colombianas de 6 a 10 dígitos."""

    _PATTERN = re.compile(r"(?<!\d)\d{6,10}(?!\d)")

    @property
    def category(self) -> str:
        return "CO_CEDULA"

    def detect(self, text: str) -> list[TextMatch]:
        return [
            TextMatch(
                category=self.category,
                start=match.start(),
                end=match.end(),
                matched_text=match.group(0),
            )
            for match in self._PATTERN.finditer(text)
        ]
```

Reglas del contrato:

- `start` es inclusivo y `end` exclusivo, ambos referidos al texto original completo.
- `start` debe ser menor que `end`.
- Los índices fuera de rango se ignoran de forma defensiva, pero un detector correcto no debe producirlos.
- `category` debe ser estable y legible; se usa en `ComplianceReport.detected_categories`.
- No incluya `matched_text` en logs de auditoría.
- Evite expresiones regulares con retroceso catastrófico (ReDoS).

## 4. Paso 3 (opcional): proveer un *salt*

```python
from pii_anonymizer.api import SaltProvider


class ConstantSaltProvider(SaltProvider):
    """Solo para pruebas o demostraciones; no usar en producción."""

    def get_salt(self) -> str:
        return "auditor-salt-2026"
```

En producción, implemente un proveedor respaldado por un secreto gestionado (KMS, variable de entorno protegida o servicio de secretos) y no exponga el valor.

## 5. Paso 4: registrar la extensión

### 5.1 En el builder

```python
from pii_anonymizer.api import AnonymizationRule, AnonymizerBuilder

anonymizer = (
    AnonymizerBuilder()
    .with_default_rules()
    .add_rule(
        AnonymizationRule(
            rule_id="co_cedula",
            strategy=RedactionTagStrategy(),
            field_names=("cedula", "documento"),
            detector=ColombianCedulaDetector(),
        )
    )
    .build()
)
```

La regla anterior:

- Enmascara el valor completo de los campos `cedula` y `documento`.
- Detecta cédulas dentro de cualquier texto de campos no sensibles.
- Aporta la categoría `CO_CEDULA` al reporte.

### 5.2 En tiempo de ejecución

```python
anonymizer.register_rule(
    AnonymizationRule(
        rule_id="phone",
        strategy=RedactionTagStrategy("[PHONE]"),
        field_names=("phone", "telefono"),
        detector=PhoneNumberDetector(),
    )
)
```

`register_rule` reemplaza una regla existente con el mismo `rule_id`. Use identificadores estables y significativos.

## 6. Ejemplo completo ejecutable

```python
import re

from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    MaskingStrategy,
    SensitivePatternDetector,
    TextMatch,
)


class RedactionTagStrategy(MaskingStrategy):
    def mask(self, raw_value: str) -> str:
        return "[REDACTED]"


class ColombianCedulaDetector(SensitivePatternDetector):
    _PATTERN = re.compile(r"(?<!\d)\d{6,10}(?!\d)")

    @property
    def category(self) -> str:
        return "CO_CEDULA"

    def detect(self, text: str) -> list[TextMatch]:
        return [
            TextMatch(self.category, match.start(), match.end(), match.group(0))
            for match in self._PATTERN.finditer(text)
        ]


anonymizer = (
    AnonymizerBuilder()
    .with_default_rules()
    .add_rule(
        AnonymizationRule(
            rule_id="co_cedula",
            strategy=RedactionTagStrategy(),
            field_names=("cedula", "documento"),
            detector=ColombianCedulaDetector(),
        )
    )
    .build()
)

print(anonymizer.anonymize_map({"cedula": "1029384756"}))
# {'cedula': '[REDACTED]'}

print(anonymizer.anonymize_text("Cliente con cédula 1029384756"))
# Cliente con cédula [REDACTED]

print(anonymizer.audit_compliance({"cedula": "1029384756"}))
# ComplianceReport(total_fields_scanned=1, anonymized_fields_count=1,
#                  detected_categories={'CO_CEDULA': 1},
#                  applied_rule_ids=('co_cedula',))
```

## 7. Probar la extensión con dobles

```python
import pytest

from pii_anonymizer.api import (
    AnonymizationRule,
    AnonymizerBuilder,
    MaskingStrategy,
    SaltProvider,
)


class SpyStrategy(MaskingStrategy):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def mask(self, raw_value: str) -> str:
        self.calls.append(raw_value)
        return "[SPY]"


class FixedSalt(SaltProvider):
    def get_salt(self) -> str:
        return "salt-fijo"


def test_extension_es_reemplazable() -> None:
    spy = SpyStrategy()
    anonymizer = (
        AnonymizerBuilder()
        .with_salt_provider(FixedSalt())
        .add_rule(
            AnonymizationRule(
                "custom",
                spy,
                field_names=("secret",),
            )
        )
        .build()
    )

    assert anonymizer.anonymize_map({"secret": "valor"}) == {"secret": "[SPY]"}
    assert spy.calls == ["valor"]
```

La prueba valida el comportamiento observable y demuestra que la dependencia es sustituible.

## 8. Interacción con la cadena de detección

Cuando varias reglas con detector coinciden sobre el mismo texto:

1. Cada detector reporta sus coincidencias.
2. Se descartan rangos inválidos o vacíos.
3. Se ordenan por inicio ascendente y, a igual inicio, por longitud descendente.
4. Se acepta la primera coincidencia y se descartan las que se solapan con ella.
5. Los reemplazos se aplican de derecha a izquierda para conservar los índices.
6. Las categorías y reglas aplicadas se agregan al reporte de auditoría.

Consecuencia práctica: **el orden de registro importa** cuando dos detectores reportan exactamente el mismo rango. Registre primero la regla cuya estrategia deba ganar.

## 9. Checklist de una extensión lista para producción

- [ ] Implementa el puerto correcto y todos sus métodos.
- [ ] Usa type hints completos y docstrings estilo Google.
- [ ] Importa únicamente desde `pii_anonymizer.api`.
- [ ] No accede a `pii_anonymizer._internal`.
- [ ] `rule_id` es único y estable.
- [ ] La categoría del detector es consistente y no contiene PII.
- [ ] El detector no produce rangos inválidos ni vacíos.
- [ ] La estrategia no registra el valor original.
- [ ] El *salt* de producción no está codificado en el repositorio.
- [ ] Existe una prueba con un doble que demuestre la sustituibilidad.
- [ ] Se evaluó el rendimiento del patrón con textos largos.
- [ ] Se documentaron los falsos positivos y falsos negativos conocidos.

## 10. Errores frecuentes

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| La regla no se aplica a un campo | El nombre no está en `field_names` o tiene otra variante | Agregue la variante exacta; la comparación no normaliza acentos. |
| La regla no se aplica en texto | No tiene `detector` | Agregue un `SensitivePatternDetector`. |
| Se lanza `InvalidRuleError` | Falta `field_names`, falta `detector`, `rule_id` vacío o estrategia nula | Complete el criterio de aplicación. |
| El reemplazo se desplaza | Índices calculados sobre texto modificado | Retorne índices absolutos sobre el texto original. |
| Una coincidencia se ignora | Rango vacío, fuera de límites o solapado | Revise el patrón y el orden de las reglas. |
| El hash cambia entre ejecuciones | `RandomSaltProvider` genera un *salt* nuevo | Inyecte un proveedor estable. |
| El reporte muestra una categoría inesperada | La regla de campo usa la categoría del detector si existe | Use `rule_id` sin detector o ajuste la categoría. |

## 11. Compatibilidad

La extensión debe compilar y ejecutarse con Python 3.11 o superior. No agregue dependencias obligatorias al paquete; si su extensión las necesita, gestione su instalación en su propio proyecto consumidor.
