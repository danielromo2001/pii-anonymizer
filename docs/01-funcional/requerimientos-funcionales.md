# Requerimientos funcionales

## 1. Convenciones

- **UC:** caso de uso de la API pública.
- **RF:** requerimiento funcional verificable.
- **Prioridad:** Must (obligatorio para 1.0.0), Should (deseable), Won't (fuera de alcance).
- Todas las operaciones se ejecutan **en memoria** y no mutan la entrada.

## 2. Resumen de casos de uso

| ID | Operación pública | Actor | Entrada | Salida | Prioridad |
| --- | --- | --- | --- | --- | --- |
| UC-01 | `anonymize_map(data)` | Servicio consumidor | `dict[str, Any]` anidado | `dict[str, Any]` sanitizado | Must |
| UC-02 | `anonymize_text(raw_text)` | Servicio consumidor | `str` | `str` sanitizado | Must |
| UC-03 | `register_rule(rule)` | Equipo de plataforma / seguridad | `AnonymizationRule` | `None` (efecto: alta o reemplazo) | Must |
| UC-04 | `audit_compliance(data)` | Equipo de auditoría | `dict[str, Any]` anidado | `ComplianceReport` agregado | Must |

## 3. Requerimientos detallados

### RF-01 — Anonimizar estructuras anidadas

**Caso de uso:** UC-01 `anonymize_map`.

**Descripción:** recorrer un diccionario que puede contener listas y diccionarios anidados, aplicar las reglas activas y retornar una copia sanitizada.

**Criterios de aceptación:**

1. El valor retornado es un `dict` nuevo; la raíz y todos los contenedores descendientes son objetos nuevos.
2. El diccionario de entrada y sus listas/diccionarios internos permanecen **exactamente iguales** después de la llamada.
3. Una clave que coincide con `field_names` de una regla, comparada sin distinguir mayúsculas, aplica la estrategia de esa regla al valor completo.
4. Si el valor de un campo sensible es `str`, se enmascara con `MaskingStrategy.mask`.
5. Si el valor de un campo sensible es `int` o `float`, se convierte a texto para enmascararlo y se retorna la cadena resultante.
6. Si el valor de un campo sensible es `None` o `bool`, se conserva sin cambios.
7. Los valores de texto de campos no sensibles se examinan con los detectores activos; si hay coincidencias, se enmascaran sin alterar el resto del texto.
8. Los valores primitivos no sensibles (`int`, `float`, `bool`, `None`) se conservan con su tipo.
9. Las listas se recorren elemento a elemento, incluyendo listas de diccionarios y anidamientos de tres o más niveles.
10. Un diccionario vacío retorna un diccionario vacío nuevo.
11. Una entrada que no sea `dict` lanza `TypeError`.
12. Los campos sin regla y sin coincidencias de detector se copian sin cambios.

**Excepciones:** `TypeError` si `data` no es un diccionario. Los errores de una estrategia personalizada se propagan sin envolver.

**Trazabilidad:** `tests/test_anonymize_map.py`.

---

### RF-02 — Anonimizar texto plano

**Caso de uso:** UC-02 `anonymize_text`.

**Descripción:** aplicar todos los detectores de las reglas activas sobre una cadena y reemplazar cada coincidencia con la estrategia asociada.

**Criterios de aceptación:**

1. Se detectan todas las coincidencias de todos los detectores activos.
2. Los reemplazos se resuelven de derecha a izquierda para no invalidar los índices.
3. Ante solapamiento, se conserva la coincidencia que inicia primero; a igual inicio, la de mayor longitud.
4. Las coincidencias con índices fuera de rango o rangos vacíos se ignoran sin lanzar excepción.
5. Una cadena vacía retorna una cadena vacía.
6. Un texto sin PII retorna exactamente el mismo contenido.
7. Se soportan múltiples correos y tarjetas en una misma línea.
8. La salida no contiene los valores originales de las coincidencias enmascaradas.
9. Se preservan los caracteres no afectados y el orden del texto.
10. Si no hay reglas con detector, el texto se retorna sin cambios.

**Excepciones:** las excepciones de detectores o estrategias personalizadas se propagan.

**Trazabilidad:** `tests/test_anonymize_text.py`, `tests/test_extensibility.py`.

---

### RF-03 — Registrar o reemplazar reglas

**Caso de uso:** UC-03 `register_rule`.

**Descripción:** incorporar dinámicamente una `AnonymizationRule` al repositorio en memoria, reemplazando otra con el mismo `rule_id`.

**Criterios de aceptación:**

1. Una regla válida queda disponible de inmediato para `anonymize_map`, `anonymize_text` y `audit_compliance`.
2. Registrar un `rule_id` existente reemplaza la regla anterior y conserva una única entrada para ese identificador.
3. Un `rule_id` vacío o compuesto solo por espacios lanza `InvalidRuleError` al construir la regla.
4. Una estrategia `None` lanza `InvalidRuleError`.
5. No definir `field_names` ni `detector` lanza `InvalidRuleError`.
6. Un nombre de campo vacío lanza `InvalidRuleError`.
7. `register_rule` con un objeto que no es `AnonymizationRule` lanza `InvalidRuleError`.
8. `AnonymizerBuilder.add_rule` valida el mismo contrato.
9. Los nombres de campo se normalizan eliminando espacios en los extremos; la comparación posterior ignora mayúsculas.
10. El orden de registro se conserva para el reporte y la resolución de reglas.

**Excepciones:** `InvalidRuleError` en todos los casos anteriores.

**Trazabilidad:** `tests/test_builder_and_rules.py`.

---

### RF-04 — Auditar cumplimiento

**Caso de uso:** UC-04 `audit_compliance`.

**Descripción:** ejecutar el mismo recorrido de `anonymize_map`, descartar la copia sanitizada y retornar únicamente un `ComplianceReport`.

**Criterios de aceptación:**

1. `total_fields_scanned` cuenta cada valor escalar visitado, incluidos `None`, booleanos y elementos de listas.
2. `anonymized_fields_count` cuenta cada valor escalar transformado al menos una vez.
3. `detected_categories` cuenta **hallazgos**: un campo con dos correos aporta 2 a `EMAIL`, aunque cuente como 1 campo anonimizado.
4. Las reglas de campo usan la categoría del detector si existe; en caso contrario usan su `rule_id`.
5. `applied_rule_ids` contiene identificadores únicos en el orden en que se aplicaron.
6. El reporte **no contiene** valores PII, fragmentos sensibles ni la estructura de entrada.
7. La auditoría no muta el diccionario analizado.
8. Un diccionario vacío produce conteos en cero, diccionario vacío y tupla vacía.
9. El reporte es inmutable a nivel de atributos.
10. La auditoría puede ejecutarse con independencia de llamadas previas (sin estado residual).

**Excepciones:** `TypeError` si `data` no es un diccionario.

**Trazabilidad:** `tests/test_compliance_audit.py`.

## 4. Requerimientos de configuración

| ID | Requerimiento | Criterio de aceptación |
| --- | --- | --- |
| RF-05 | Reglas por defecto | `with_default_rules()` registra `email`, `credit_card`, `password`, `token` y `document_id`. |
| RF-06 | Inyección de *salt* | `with_salt_provider(provider)` usa el proveedor en las reglas con hash; un `None` lanza `ValueError`. |
| RF-07 | Fábricas públicas | `partial_mask_strategy`, `hash_mask_strategy`, `email_detector` y `credit_card_detector` retornan adaptadores utilizables sin importar `_internal`. |
| RF-08 | Construcciones independientes | Cada `build()` crea un repositorio y un recorredor nuevos; registrar reglas en una instancia no afecta a otra. |
| RF-09 | Reemplazo por `rule_id` | Una regla agregada al builder con un `rule_id` de las reglas por defecto tiene prioridad. |

## 5. Requerimientos no funcionales

| ID | Categoría | Requerimiento |
| --- | --- | --- |
| RNF-01 | Compatibilidad | Python 3.11 o superior; sin dependencias de ejecución. |
| RNF-02 | Arquitectura | `domain` no importa otras capas; `application` solo importa `domain`; `infrastructure` importa `domain` y `application`; `api` es la única frontera pública. |
| RNF-03 | Seguridad | El reporte no expone PII; el *salt* por defecto usa `secrets.token_hex(16)`. |
| RNF-04 | Inmutabilidad | Ninguna operación muta `dict` o `list` de entrada. |
| RNF-05 | Calidad | Cobertura de líneas ≥ 85 % y pruebas automatizadas de todos los casos de uso. |
| RNF-06 | Extensibilidad | Un tercero puede agregar estrategias y detectores importando solo `pii_anonymizer.api`. |
| RNF-07 | Documentación | Docstrings estilo Google y documentación funcional/técnica en español. |
| RNF-08 | Rendimiento | Recorrido lineal respecto de la cantidad de nodos y de la longitud del texto analizado. |

## 6. Reglas de negocio

1. La comparación de nombres de campo es *case-insensitive* y no normaliza acentos; se deben registrar las variantes necesarias.
2. Un campo sensible con estrategia de hash produce `hash:<hex>` con longitud de prefijo configurable (12 por defecto).
3. La estrategia parcial conserva el dominio de un correo y enmascara el centro de la parte local; si la cadena es demasiado corta, se enmascara completa.
4. Un número de tarjeta se detecta con 13 a 19 dígitos, con espacios o guiones opcionales.
5. Un correo se detecta con el patrón habitual `local@dominio.tld`.
6. El reporte es evidencia agregada; no certifica por sí solo el cumplimiento legal.

## 7. Fuera de alcance de 1.0.0

- Persistencia de reglas entre procesos.
- Cifrado reversible o KMS.
- Detección de PII en binarios, imágenes o audio.
- Normalización semántica de nombres de campo (sinónimos, plurales, idiomas).
- Validación Luhn de tarjetas.
- API asíncrona o procesamiento distribuido.
