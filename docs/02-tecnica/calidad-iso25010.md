# Evaluación de calidad según ISO/IEC 25010

## 1. Alcance y método

Este documento evalúa `pii-anonymizer` 1.0.0 frente a las subcaracterísticas de calidad de ISO/IEC 25010 priorizadas por la especificación:

- **Mantenibilidad:** modularidad, reusabilidad, analizabilidad, capacidad de modificación y capacidad de prueba.
- **Seguridad:** confidencialidad.

La evaluación es **cualitativa y basada en evidencia del repositorio**: estructura de paquetes, imports, pruebas automatizadas, cobertura y documentación. No constituye una certificación formal.

Escala de valoración:

| Nivel | Significado |
| --- | --- |
| 5 — Excelente | Mecanismo explícito, verificable y con evidencia automatizada. |
| 4 — Alto | Mecanismo sólido con limitaciones menores documentadas. |
| 3 — Adecuado | Cubre la necesidad con trade-offs relevantes. |
| 2 — Bajo | Depende de disciplina manual o tiene brechas. |
| 1 — Insuficiente | No hay mecanismo o no es verificable. |

## 2. Resumen

| Subcaracterística | ISO 25010 | Valoración | Evidencia principal |
| --- | --- | --- | --- |
| Modularidad | Mantenibilidad | 5 | Cuatro capas, paquetes por responsabilidad, `_internal` aislado. |
| Reusabilidad | Mantenibilidad | 5 | Puertos ABC, reglas configurables, extensiones sin tocar el núcleo. |
| Analizabilidad | Mantenibilidad | 4 | Trazabilidad por capas y reporte; falta telemetría interna. |
| Capacidad de modificación | Mantenibilidad | 5 | DIP, Strategy, Factory Method en fábricas, builder centralizado. |
| Capacidad de prueba | Mantenibilidad | 5 | 49 pruebas, dobles, cobertura 97,70 %, bajo acoplamiento. |
| Confidencialidad | Seguridad | 4 | Enmascaramiento y auditoría sin PII; el *salt* y la configuración son responsabilidad del cliente. |

## 3. Modularidad

**Definición:** grado en que el software se compone de módulos discretos con acoplamiento bajo y cohesión alta.

**Mecanismos del diseño:**

- Paquetes `domain`, `application`, `infrastructure` y `api` con dependencias unidireccionales.
- Implementación privada bajo `pii_anonymizer._internal`.
- Puertos pequeños y específicos: `MaskingStrategy`, `SensitivePatternDetector`, `SaltProvider`, `RuleRepository`, `StructureTraverser`.
- Un caso de uso por archivo y una única responsabilidad.
- Adaptadores de infraestructura separados por tipo: persistencia, recorrido, estrategias y detectores.

**Evidencia:**

- El dominio no importa capas externas; puede verificarse con búsqueda de imports.
- `application` no conoce `infrastructure` ni `api`.
- La única clase que conoce todas las capas es `AnonymizerBuilder`, confinada a la frontera.

**Limitación:** Python no impone privacidad real; el aislamiento de `_internal` depende de convención, revisión y pruebas de arquitectura.

**Valoración: 5.**

## 4. Reusabilidad

**Definición:** grado en que un activo puede utilizarse en más de un sistema o contexto.

**Mecanismos:**

- API pública mínima y estable reexportada con `__all__`.
- Configuración mediante reglas, no mediante herencia obligatoria.
- Estrategias y detectores intercambiables por polimorfismo.
- Reglas por defecto para casos frecuentes y fábricas para configuraciones comunes.
- Cero dependencias de ejecución y compatibilidad con Python 3.11+.

**Evidencia:**

- `tests/test_extensibility.py` implementa `RedactionTagStrategy` y `ColombianCedulaDetector` importando solo `pii_anonymizer.api`.
- `examples/demo_cli.py` reutiliza la librería en un flujo de consola sin conocer `_internal`.
- Tres escenarios documentados: logs, exportación analítica y portal de soporte.

**Limitación:** la librería está orientada a datos en memoria; no cubre *streams* distribuidos ni persistencia.

**Valoración: 5.**

## 5. Analizabilidad

**Definición:** facilidad para diagnosticar deficiencias, causas de fallos o identificar partes a modificar.

**Mecanismos:**

- Nombres de clases alineados con responsabilidades y patrones.
- Excepciones de dominio (`AnonymizerError`, `InvalidRuleError`) con mensajes contextuales.
- `ComplianceReport` con conteos y reglas aplicadas.
- Docstrings Google y type hints completos.
- Diagramas C4, UML y ADR que enlazan decisiones con clases.

**Evidencia:**

- Un fallo de regla se localiza en `AnonymizationRule.__post_init__` o `RegisterRuleUseCase`.
- Un fallo de detección se localiza en `DetectorChain` o en el detector concreto.
- Un fallo de recorrido se localiza en `CompositeStructureTraverser` y sus nodos.
- La cobertura por archivo identifica rutas no ejercitadas.

**Limitación:** no hay *logging* interno ni códigos de error estructurados; el diagnóstico se apoya en excepciones y en el consumidor.

**Valoración: 4.**

## 6. Capacidad de modificación

**Definición:** grado en que el software permite cambios eficaces sin introducir defectos.

**Mecanismos:**

- Inversión de dependencias: los casos de uso dependen de abstracciones.
- Strategy para cambiar el algoritmo de enmascaramiento.
- Chain of Responsibility para agregar detectores sin editar la cadena.
- Builder como único punto de cableado.
- Reglas tratadas como datos inmutables, no como código.

**Evidencia:**

- Agregar un detector requiere una clase nueva, una regla y ninguna modificación al dominio.
- Cambiar la estrategia de un campo existente se logra registrando una regla con el mismo `rule_id`.
- Sustituir el *salt* no afecta a `HashMaskStrategy` ni a los casos de uso.

**Limitación:** el orden de las reglas con detectores puede afectar el resultado ante solapamientos; es una decisión de configuración documentada.

**Valoración: 5.**

## 7. Capacidad de prueba

**Definición:** facilidad para establecer criterios de prueba y ejecutarlas.

**Mecanismos:**

- Puertos abstractos que permiten *stubs*, espías y mocks.
- `FixedSaltProviderStub` para hashes deterministas.
- `SpyMaskingStrategy` para verificar invocaciones y valores recibidos.
- Casos de uso pequeños con dependencias inyectadas.
- Suite organizada por funcionalidad y prueba de extensibilidad aislada.
- Cobertura mínima configurada en `pyproject.toml` (`fail_under = 85`).

**Evidencia:**

| Métrica | Resultado |
| --- | --- |
| Pruebas | 49 aprobadas |
| Cobertura total | 97,70 % |
| Ramas parciales | 3 de 92 |
| Archivos con 100 % | 27 de 30 |
| Dobles obligatorios | `FixedSaltProviderStub`, `SpyMaskingStrategy` |

Comando:

```bash
python -m pytest --cov=pii_anonymizer --cov-report=term-missing
```

**Limitación:** no hay pruebas de propiedad (*property-based*) ni pruebas de rendimiento o concurrencia.

**Valoración: 5.**

## 8. Confidencialidad

**Definición:** grado en que el software asegura que los datos solo son accesibles a entidades autorizadas.

**Mecanismos:**

- Enmascaramiento parcial, hash salado y redacción total configurables.
- `HashMaskStrategy` usa SHA-256 con *salt* inyectado.
- `RandomSaltProvider` obtiene 128 bits de entropía mediante `secrets.token_hex(16)`.
- `ComplianceReport` contiene solo conteos, categorías e identificadores de reglas.
- Las operaciones no mutan la entrada, lo que evita efectos laterales sobre el dato original.
- El reporte no incluye la copia sanitizada ni fragmentos de valores.

**Evidencia:**

- `tests/test_compliance_audit.py` verifica que ningún valor sensible aparece en `repr(report)` ni en `dataclasses.asdict(report)`.
- `tests/test_anonymize_map.py` verifica la no mutación y la ausencia de PII en la salida.
- Las estrategias parciales conservan únicamente extremos y el dominio del correo.

**Limitaciones:**

- El hash con un espacio de valores pequeño es vulnerable a fuerza bruta si el *salt* se filtra.
- La conservación del dominio en correos puede ser sensible en algunos contextos.
- La librería no gestiona secretos, TLS, autorización ni retención.
- La detección por regex puede tener falsos negativos.

**Valoración: 4.** El diseño protege la confidencialidad en el procesamiento, pero la seguridad operativa depende de la configuración y del entorno del cliente.

## 9. Matriz de trazabilidad

| Subcaracterística | Archivos / clases | Pruebas |
| --- | --- | --- |
| Modularidad | `_internal/domain`, `_internal/application`, `_internal/infrastructure`, `api` | Imports verificables; suite completa |
| Reusabilidad | `api/builder.py`, `domain/ports.py`, `application/ports.py` | `test_extensibility.py`, `test_builder_and_rules.py` |
| Analizabilidad | `domain/exceptions.py`, `domain/models.py`, `facade.py` | `test_compliance_audit.py` |
| Capacidad de modificación | `strategies/`, `detectors/`, `DetectorChain`, `AnonymizerBuilder` | `test_extensibility.py` |
| Capacidad de prueba | `tests/doubles.py`, puertos ABC | Toda la suite |
| Confidencialidad | `hashing.py`, `salt.py`, `partial.py`, `ComplianceReport` | `test_compliance_audit.py`, `test_anonymize_map.py` |

## 10. Amenazas a la validez

- La cobertura mide ejecución de líneas y ramas, no corrección semántica.
- Las valoraciones son estimaciones de diseño, no resultados de un laboratorio ISO.
- No se evaluaron características como rendimiento, portabilidad o usabilidad, fuera del alcance de esta versión.
- Los escenarios de producción pueden introducir restricciones (por ejemplo, latencia estricta) no modeladas aquí.

## 11. Conclusión

El componente cumple con un nivel alto en las subcaracterísticas de mantenibilidad evaluadas, sustentado en la separación de capas, la inversión de dependencias y una suite de pruebas con cobertura del 97,70 %. La confidencialidad está soportada por diseño en el procesamiento y la auditoría, con responsabilidades claramente delegadas al consumidor en materia de gestión de secretos y controles perimetrales.
