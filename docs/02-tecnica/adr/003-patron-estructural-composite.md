# ADR-003 — Patrón estructural Composite para el recorrido de datos

- **Estado:** Aceptado
- **Fecha:** 2026-11-24
- **Decisores:** Equipo de arquitectura y plataforma
- **Ámbito:** `CompositeStructureTraverser`, nodos y `TraversalContext`

## Contexto

La entrada puede ser un diccionario con listas, diccionarios anidados a profundidad arbitraria, escalares y `None`. El componente debe:

- Aplicar reglas por nombre de campo.
- Aplicar detectores a cadenas de campos no sensibles.
- Contabilizar campos y categorías para la auditoría.
- No mutar la entrada.
- Mantener el recorrido separado de la detección y de la persistencia.
- Soportar nuevas formas de nodo sin reescribir los casos de uso.

Las soluciones ingenuas mezclan recursión, reglas y conteos en una sola función, lo que reduce cohesión y dificulta las pruebas.

## Decisión

Implementar el patrón **Composite** en `_internal/infrastructure/traversal/composite.py`:

- `DataNode` (ABC) define `process(context) -> Any`.
- `DictNode` recorre un diccionario y construye uno nuevo.
- `ListNode` recorre una lista y construye una nueva.
- `ScalarNode` representa hojas y aplica la regla de campo o los detectores.
- `_node_for(value)` selecciona el nodo adecuado.
- `TraversalContext` se crea **por invocación** y acumula:
  - `field_rules`, `detector_rules`
  - `total_fields_scanned`
  - `anonymized_fields_count`
  - `detected_categories`
  - `applied_rule_ids`

Reglas de comportamiento:

1. Cada valor escalar visitado incrementa `total_fields_scanned`.
2. Si la clave coincide con una regla y el valor es escalar:
   - `str` se pasa directamente a `mask`;
   - `int` y `float` se convierten a texto para enmascarar;
   - `None` y `bool` se preservan;
   - el resultado enmascarado se contabiliza.
3. Si la clave coincide pero el valor es `dict` o `list`, se recorre como contenedor; la estrategia de campo no se aplica al contenedor completo.
4. Los textos de campos no sensibles se procesan con `DetectorChain`.
5. Se preservan las claves y el orden de inserción del diccionario.
6. Se crean nuevas listas y diccionarios en todos los niveles.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Decisión |
| --- | --- | --- | --- |
| Funciones recursivas sueltas | Menos clases, inicio rápido | Mezcla responsabilidades, difícil extender tipos, conteos dispersos | Rechazada |
| `copy.deepcopy` y mutar la copia | Sencillo para no mutar | Requiere recorrer igualmente para reglas; mutación temporal; difícil de auditar | Rechazada |
| Serializar a JSON y reconstruir | Uniformidad | Pierde tipos, falla con objetos no serializables, costo alto, no aplica reglas por campo | Rechazada |
| Visitante externo sobre tipos nativos | Separa algoritmo | `isinstance` disperso, más difícil de extender que el polimorfismo | Rechazada |
| Librería externa de recorrido | Menos código | Dependencia, comportamiento difícil de controlar, no cumple “cero dependencias” | Rechazada |
| Composite con contexto por invocación | Polimorfismo, estado local, extensible | Más clases y asignaciones | **Aceptada** |

## Beneficios

- **Uniformidad:** diccionarios, listas y escalares se procesan con la misma interfaz.
- **Extensibilidad:** un nuevo tipo de nodo puede agregarse sin tocar los casos de uso.
- **Sin mutación:** cada `process` construye una nueva estructura.
- **Auditoría centralizada:** el contexto es el único dueño de los conteos.
- **Stateless entre llamadas:** no hay estado compartido en el recorredor.
- **Testabilidad:** el recorrido se prueba a través de la API pública con estructuras representativas.
- **Bajo acoplamiento:** los nodos solo conocen el contexto y los puertos, no el repositorio ni la fachada.

## Costos y trade-offs de implementación

| Costo | Impacto | Mitigación |
| --- | --- | --- |
| Asignación de un nodo por valor | Mayor uso de memoria y CPU que una función recursiva | El recorrido es lineal; para payloads masivos, fragmentar la entrada. |
| Recursión del intérprete | `RecursionError` en estructuras extremadamente profundas | Documentar el límite práctico de Python; aplanar antes si es necesario. |
| `tuple` y `set` se tratan como escalares | No se recorren sus elementos | Fuera de alcance 1.0.0; documentado como limitación. |
| Regla de campo no aplica a contenedores | Un `password: {...}` no se redacta completo | Validar el contrato de datos; agregar una futura política para contenedores. |
| `TraversalContext` conoce `DetectorChain` | Acoplamiento interno entre recorrido y aplicación | Se acepta: infraestructura puede depender de aplicación; el contexto encapsula la llamada. |
| Conversión de números a texto | Cambia el tipo de salida de un campo sensible | Es intencional: prioriza no filtrar el valor; documentado. |
| Copia de estructuras | Memoria proporcional al tamaño de entrada | Requisito de no mutación; el consumidor controla el tamaño. |

## Consecuencias

- El reporte y la sanitización comparten exactamente el mismo recorrido, lo que evita divergencias entre `anonymize_map` y `audit_compliance`.
- Cualquier nuevo comportamiento de recorrido debe implementarse en un nodo o en el contexto, no en los casos de uso.
- La profundidad máxima está limitada por la pila de Python; se recomienda validar la entrada en escenarios hostiles.
- Los diccionarios con claves no `str` se preservan y se recorren, aunque no pueden coincidir con `field_names`.
- El orden de las claves se conserva, lo que facilita comparar salidas y depurar.

## Evidencia

- `tests/test_anonymize_map.py`: anidamiento a tres niveles, listas de diccionarios, `None`, primitivos, no mutación e identidad de contenedores.
- `tests/test_compliance_audit.py`: conteo de escalares, categorías y no mutación.
- `tests/test_extensibility.py`: detectores externos aplicados durante el recorrido.

## Referencias

- [Diagramas UML](../diagramas-uml.md)
- [Arquitectura C4](../arquitectura-c4.md)
- [Requerimientos funcionales](../../01-funcional/requerimientos-funcionales.md)
