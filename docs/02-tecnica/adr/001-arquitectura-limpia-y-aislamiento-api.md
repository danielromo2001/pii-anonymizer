# ADR-001 — Arquitectura Limpia y aislamiento de la API pública

- **Estado:** Aceptado
- **Fecha:** 2026-11-24
- **Decisores:** Equipo de arquitectura y plataforma
- **Ámbito:** Estructura general del paquete `pii-anonymizer` 1.0.0

## Contexto

El componente debe reutilizarse en servicios, jobs y portales con necesidades distintas. La sanitización de PII es sensible: un cambio accidental en un detector o en una estrategia no debe obligar a los consumidores a recompilar su lógica, y las pruebas no deben acoplarse a clases internas.

Fuerzas en juego:

- **Mantenibilidad:** la lógica de detección, recorrido y enmascaramiento evoluciona a ritmos distintos.
- **Extensibilidad:** terceros deben agregar estrategias y detectores sin modificar el núcleo.
- **Testabilidad:** los casos de uso deben poder probarse con dobles.
- **Aislamiento:** la implementación interna no debe filtrarse al contrato público.
- **Cero dependencias:** no se permite un framework de inyección ni un motor externo.
- **Python 3.11+:** no hay módulos privados reales; la privacidad se logra por convención y estructura.

## Decisión

Adoptar Arquitectura Limpia con cuatro capas:

1. `_internal/domain`: objetos de valor inmutables, excepciones y puertos de extensión. No importa otras capas ni librerías externas.
2. `_internal/application`: cuatro casos de uso, puertos secundarios, `DetectorChain` y `DefaultPiiAnonymizer`. Solo depende de `domain`.
3. `_internal/infrastructure`: repositorio, recorrido Composite, estrategias, detectores y proveedor de *salt*. Depende de `domain` y `application`.
4. `api`: frontera pública y **Composition Root**. Reexporta contratos y expone `AnonymizerBuilder`.

Reglas complementarias:

- Todo lo interno vive bajo `pii_anonymizer._internal`.
- La superficie pública se declara con `__all__` en `api/__init__.py` y `pii_anonymizer/__init__.py`.
- Pruebas y ejemplos importan exclusivamente `pii_anonymizer.api` o `pii_anonymizer`.
- El cliente nunca instancia adaptadores concretos; usa el builder o las fábricas.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Decisión |
| --- | --- | --- | --- |
| Módulo único `pii_anonymizer.py` | Menos archivos, inicio rápido | Bajo cohesión, imposible sustituir piezas, pruebas acopladas | Rechazada |
| Paquete plano que exporta todo | Comodidad para el cliente | Expone implementación, rompe encapsulamiento, cambios internos se vuelven públicos | Rechazada |
| Framework de inyección de dependencias | Configuración declarativa, *scopes* | Dependencia externa, curva de aprendizaje, magia difícil de depurar | Rechazada |
| Arquitectura hexagonal sin `api` explícita | Puertos/adaptadores claros | El cliente debe ensamblar adaptadores y conoce detalles | Rechazada |
| Plugins vía *entry points* | Descubrimiento dinámico | Complejidad prematura para 1.0.0; difícil de auditar | Pospuesta |

## Beneficios

- **Sustituibilidad:** estrategias, detectores, repositorio y recorrido son reemplazables.
- **Evolución controlada:** la implementación puede cambiar sin romper el contrato.
- **Pruebas limpias:** los casos de uso se prueban con puertos y dobles.
- **Claridad conceptual:** cada capa tiene una responsabilidad y una dirección de dependencia.
- **Onboarding:** la estructura refleja el flujo de una llamada.

## Costos y trade-offs de implementación

| Costo | Impacto | Mitigación |
| --- | --- | --- |
| Más archivos y *boilerplate* de reexportación | Curva inicial mayor | README con árbol y Quickstart; `__all__` explícito. |
| Indirección en cada llamada | Depuración menos directa | Nombres alineados, docstrings, diagramas de secuencia. |
| `api` conoce todas las capas | Único punto acoplado al ensamblado | Se limita a `builder.py`; no contiene lógica de negocio. |
| Riesgo de imports circulares | Fallos de importación | `domain` sin imports externos; `TYPE_CHECKING` para anotaciones; capas unidireccionales. |
| `_internal` no es privado en Python | Un cliente podría importarlo | Convención, revisión de código, pruebas que verifican imports y documentación explícita. |
| Duplicación de firmas en exports | Mantenimiento | Pocos contratos estables; pruebas de API pública. |

También se acepta que `AnonymizerBuilder` tenga un rol amplio: es el único lugar donde se permite conocer todas las implementaciones. Esta concesión evita dispersar el *wiring* por la aplicación.

## Consecuencias

- Cualquier nueva capacidad debe evaluarse primero en qué capa vive.
- Un adaptador nuevo no debe requerir cambios en casos de uso.
- Las pruebas de arquitectura deben ejecutarse en revisión o CI.
- Si el paquete crece, se evaluará `import-linter` o una prueba dedicada de reglas de importación.

## Evidencia y verificación

```bash
# Dominio puro
grep -r "pii_anonymizer\._internal\.\(application\|infrastructure\|api\)" src/pii_anonymizer/_internal/domain

# Aplicación sin infraestructura ni api
grep -r "pii_anonymizer\._internal\.\(infrastructure\|api\)" src/pii_anonymizer/_internal/application

# Consumidores sin acceso a _internal
grep -r "pii_anonymizer\._internal" tests examples
```

- `tests/test_extensibility.py` usa únicamente `pii_anonymizer.api`.
- `src/pii_anonymizer/api/__init__.py` declara `__all__`.
- `src/pii_anonymizer/__init__.py` reexporta la misma superficie.

## Referencias

- [Arquitectura C4](../arquitectura-c4.md)
- [Diagramas UML](../diagramas-uml.md)
- [Matriz SOLID/GRASP](../matriz-solid-grasp.md)
- [Guía de extensión](../../01-funcional/guia-de-extension.md)
