# ADR-004 — Strategy y Chain of Responsibility para detección y enmascaramiento

- **Estado:** Aceptado
- **Fecha:** 2026-11-24
- **Decisores:** Equipo de arquitectura y plataforma
- **Ámbito:** `MaskingStrategy`, `SensitivePatternDetector`, `DetectorChain`

## Contexto

La detección de PII en texto no es un algoritmo único: correos, tarjetas y patrones propios del negocio conviven en la misma cadena. Cada categoría puede requerir una transformación distinta (parcial, hash, redacción total).

Además, varias coincidencias pueden:

- Aparecer en la misma línea.
- Solaparse entre categorías.
- Tener longitudes distintas.
- Provenir de detectores de terceros con errores de índices.

El reemplazo secuencial ingenuo (aplicar regla 1, luego regla 2 sobre el texto ya modificado) desplaza índices y puede enmascarar fragmentos ya transformados. Un `if/elif` por categoría cierra el diseño a nuevas extensiones.

## Decisión

Combinar dos patrones de comportamiento:

1. **Strategy** (`MaskingStrategy`): encapsula el algoritmo de transformación (`PartialMaskStrategy`, `HashMaskStrategy`, estrategias de terceros).
2. **Chain of Responsibility** (`DetectorChain` + `_DetectorHandler`): cada eslabón encapsula un `SensitivePatternDetector` y delega en el siguiente.

`DetectorChain` implementa el algoritmo de resolución:

1. Recolecta todas las `TextMatch` de todos los eslabones.
2. Descarta rangos inválidos (`start < 0`, `end > len`, `start >= end`).
3. Ordena por `start` ascendente y, a igual inicio, por longitud descendente.
4. Acepta una coincidencia solo si su `start` no se solapa con el `end` de la última aceptada.
5. Aplica los reemplazos de **derecha a izquierda** para conservar los índices.
6. Retorna el texto y una tupla de `AppliedMask` (`rule_id`, `category`, `start`, `end`) para la auditoría.

La estrategia aplicada proviene de la regla que aportó el detector. La categoría reportada es la del detector; el `rule_id` es el de la regla.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Decisión |
| --- | --- | --- | --- |
| `if/elif` por categoría | Fácil de leer al inicio | Viola OCP; cada nuevo patrón modifica la cadena; pruebas acopladas | Rechazada |
| Un único regex con alternancia | Una sola pasada, rápido | Difícil de mantener; categorías y estrategias por grupo; sin extensión externa | Rechazada |
| Aplicar cada regla secuencialmente con `str.replace` | Simple | Desplaza índices; vuelve a procesar texto ya enmascarado; no controla solapamientos | Rechazada |
| Pipeline funcional de detectores | Composable | No modela responsabilidades ni orden de forma explícita; metadatos dispersos | Rechazada |
| Motor DLP externo | Cobertura amplia | Dependencia, latencia, red, costo, difícil de auditar | Rechazada para 1.0.0 |
| Strategy + Chain con resolución derecha-izquierda | Extensible, determinista, auditable | Más clases y una política de solapamiento que documentar | **Aceptada** |

## Beneficios

- **OCP:** agregar un detector o estrategia no modifica el núcleo.
- **Determinismo:** la política de solapamiento es explícita y reproducible.
- **Sin desplazamiento de índices:** el reemplazo derecha-izquierda evita recalcular posiciones.
- **Auditoría:** `AppliedMask` permite contar hallazgos por categoría y regla sin exponer valores.
- **Aislamiento:** los detectores solo conocen su patrón; las estrategias solo transforman.
- **Pruebas:** cada estrategia y detector se prueba de forma independiente; la cadena se prueba con múltiples coincidencias y solapamientos.
- **Robustez:** los índices inválidos de terceros se ignoran en lugar de romper el proceso.

## Costos y trade-offs de implementación

| Costo | Impacto | Mitigación |
| --- | --- | --- |
| Construcción de la cadena por llamada de texto | Asignación de objetos por operación | Número de reglas pequeño; se puede optimizar con caché en el futuro. |
| Sensibilidad al orden de reglas | Ante mismo rango, gana la primera registrada | Documentar; registrar primero la regla prioritaria. |
| Política de solapamiento codificada | Un detector más específico puede ser descartado si inicia después | Revisar patrones; a futuro agregar prioridad explícita por regla. |
| `AppliedMask` no incluye prioridad | El reporte no explica qué se descartó | Documentar; los conteos reflejan solo lo aplicado. |
| Estrategias aplicadas sobre el fragmento actual | Si una estrategia devuelve texto con PII, no se re-detecta | Es responsabilidad de la estrategia; no se re-procesa por diseño. |
| Un detector lento afecta toda la cadena | Latencia acumulada | Mantener regex acotadas; monitorear; dividir reglas. |
| La cadena se evalúa sobre el texto original | Detección consistente, pero no sobre resultados intermedios | Es la semántica deseada para evitar doble enmascaramiento. |
| Categorías definidas por el detector | Una regla de campo puede reportar la categoría del detector | Documentado en la guía de uso; usar `rule_id` sin detector si se desea otra etiqueta. |

## Consecuencias

- `anonymize_text` obtiene solo reglas con detector; las reglas exclusivas de campo no participan.
- `DetectorChain` es stateless entre invocaciones: se reconstruye con las reglas vigentes en cada llamada, por lo que `register_rule` surte efecto de inmediato.
- La auditoría de mapas reutiliza la misma cadena a través de `TraversalContext`, garantizando coherencia entre texto y estructuras.
- Los detectores de terceros deben respetar el contrato de índices; la cadena los protege de fallos, no de patrones incorrectos.
- Una futura prioridad por regla requerirá ampliar `AnonymizationRule` o la política de orden, manteniendo compatibilidad.

## Evidencia

- `tests/test_anonymize_text.py`: múltiples correos, tarjetas, texto vacío y sin PII, reemplazos sin desplazamiento.
- `tests/test_extensibility.py`: estrategia de redacción, detector de cédulas, solapamiento y rangos inválidos.
- `tests/test_builder_and_rules.py`: sustitución de estrategia mediante `SpyMaskingStrategy` y hashes deterministas con `FixedSaltProviderStub`.
- `tests/test_compliance_audit.py`: conteo de hallazgos por categoría.

## Referencias

- [Guía de extensión](../../01-funcional/guia-de-extension.md)
- [Diagramas UML](../diagramas-uml.md)
- [Matriz SOLID/GRASP](../matriz-solid-grasp.md)
