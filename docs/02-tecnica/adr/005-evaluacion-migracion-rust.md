# ADR-005: Evaluación de migración del componente a Rust

- **Estado:** Propuesto (recomendación: mantener Python en la serie 1.x).
- **Fecha:** 2026-11-28.
- **Decisores:** Equipo PII Anonymizer.
- **Relacionado:** ADR-001 (Arquitectura Limpia), ADR-002 (Builder), ADR-003 (Composite), ADR-004 (Strategy y Chain).

## Contexto

`pii-anonymizer` es una librería Python 3.11+ que detecta, enmascara y audita
PII en estructuras en memoria. No usa base de datos, red ni servicios externos:
toda la operación ocurre en el proceso del cliente. La app de demostración
(`pii-anonymizer-workshop-app`) es Flask + SQLite y consume la librería a través
de `pii_anonymizer.api`.

Se evalúa migrar el componente a Rust para obtener un artefacto más ligero,
mayor rendimiento y un binario único. La pregunta relevante no es solo
"¿Rust es más rápido?", sino "¿el beneficio justifica el coste de cambiar el
contrato, el empaquetado y la integración con la app?".

## Métricas del componente actual

| Métrica | Valor |
| --- | --- |
| Lenguaje | Python 3.11+ |
| Archivos fuente | 30 |
| Líneas en `src/` | 1.656 |
| Líneas de pruebas | 885 |
| Pruebas | 49 |
| Cobertura | 97,70 % |
| Dependencias de ejecución | 0 |
| Persistencia / red | Ninguna; todo en memoria |
| API pública | `PiiAnonymizer`, `AnonymizerBuilder`, `MaskingStrategy`, `SensitivePatternDetector`, `SaltProvider`, `AnonymizationRule`, `TextMatch`, `ComplianceReport`, `AnonymizerError`, `InvalidRuleError` |

El componente es pequeño, sin dependencias externas y con una arquitectura ya
separada en `api`, `application`, `domain` e `infrastructure`. Es un candidato
técnicamente viable para Rust, pero también es un componente ya terminado,
probado y documentado.

## Opciones evaluadas

### Opción 1: Mantener Python (recomendada)

- **Ventajas:** cero coste de migración; la API y la app siguen funcionando;
  el equipo mantiene una sola base de código y un solo conjunto de pruebas;
  el despliegue actual (`pip install`) ya está resuelto.
- **Desventajas:** mayor consumo de memoria y menor rendimiento que Rust en
  cargas muy grandes; requiere intérprete de Python.
- **Cuándo tiene sentido:** el caso de uso es una librería de apoyo para una app
  Flask y los volúmenes de datos son moderados. Es el escenario actual.

### Opción 2: Reescritura completa en Rust

- **Ventajas:** rendimiento, memoria predecible, binario único, sin intérprete.
- **Desventajas:** rompe la API Python; obliga a reescribir la app o a crear
  puentes FFI; hay que replicar 49 pruebas y la documentación; se pierde la
  integración directa con Flask; el equipo asume la curva de aprendizaje de
  Rust y el mantenimiento de dos ecosistemas.
- **Coste estimado:** 4 a 8 semanas para alcanzar paridad funcional, más el
  trabajo de empaquetado y de integración con la app.
- **Cuándo tiene sentido:** el producto deja de ser una librería Python y se
  convierte en un CLI o servicio independiente con requisitos de rendimiento
  demostrados.

### Opción 3: Núcleo Rust + PyO3 (híbrido)

- **Ventajas:** conserva la API Python; el núcleo de cálculo (regex, hash,
  recorrido) se ejecuta en Rust; se puede introducir por detrás de la fachada
  actual sin cambiar a los consumidores.
- **Desventajas:** agrega `maturin`/`pyo3`, compilación por plataforma y
  *wheels* específicos; la depuración cruza dos lenguajes; la ganancia solo se
  justifica si el *profiling* muestra que el cuello de botella está en Python.
- **Coste estimado:** 2 a 4 semanas para un núcleo con paridad y *golden tests*.
- **Cuándo tiene sentido:** hay una necesidad real de rendimiento y se quiere
  mantener compatibilidad con los clientes Python.

### Opción 4: Servicio Rust (Axum) y app como cliente HTTP

- **Ventajas:** desacopla el motor de la app; se puede escalar por separado;
  el componente deja de depender del runtime de Python.
- **Desventajas:** añade un salto de red, despliegue, autenticación,
  observabilidad y manejo de errores distribuidos; para una app local de
  demostración es sobredimensionado; la latencia de red puede anular la ganancia
  de Rust.
- **Coste estimado:** 4 a 6 semanas, sin contar operación.
- **Cuándo tiene sentido:** el motor se comparte entre varios servicios o se
  necesita escalar horizontalmente.

## Comparación

| Criterio | Python actual | Rust completo | Rust + PyO3 | Servicio Rust |
| --- | --- | --- | --- | --- |
| Compatibilidad con la API actual | Total | Nula | Total | Parcial (HTTP) |
| Rendimiento en payloads grandes | Medio | Alto | Alto | Alto |
| Consumo de memoria | Medio | Bajo | Bajo | Medio |
| Complejidad de despliegue | Baja | Media | Media-alta | Alta |
| Curva de aprendizaje | Baja | Alta | Alta | Alta |
| Coste de migración | Nulo | Alto | Medio | Alto |
| Riesgo para la app Flask | Nulo | Alto | Bajo | Medio |
| Madurez del ecosistema para este caso | Alta | Alta | Alta | Alta |

## Decisión

**No migrar el componente a Rust en la serie 1.x.** El componente actual cumple
los requisitos funcionales, no tiene dependencias de ejecución y su rendimiento
es suficiente para el caso de uso previsto (una app Flask local y payloads de
tamaño moderado). Una reescritura completa introduciría un riesgo alto sin una
necesidad medida.

Si en el futuro aparece un requisito concreto de rendimiento o distribución, la
ruta de menor riesgo es la **Opción 3 (núcleo Rust + PyO3)**, precedida por un
*benchmark* reproducible. La Opción 2 solo se justifica si el producto cambia de
naturaleza (CLI o servicio independiente) y la app deja de ser el cliente
principal.

## Consecuencias

- Se mantiene la API pública y la app sigue consumiendo `pii_anonymizer.api`.
- No se agregan dependencias de compilación ni *wheels* específicos.
- La decisión se revisa si cambia alguno de estos supuestos:
  - payloads habituales mayores a decenas de MB;
  - necesidad de miles de operaciones por segundo;
  - distribución como binario único sin Python;
  - el equipo decide estandarizar todos los componentes en Rust.
- Se documenta la evaluación para evitar repetir el análisis sin datos.

## Plan de migración si se aprueba

1. **Medir primero.** Crear un *benchmark* con payloads representativos
   (diccionarios anidados, listas, textos con muchos correos y tarjetas) y
   registrar tiempo, memoria y CPU del componente Python actual.
2. **Congelar el contrato.** Convertir las 49 pruebas en *golden tests* de
   entrada/salida JSON, incluyendo errores, reglas por defecto, solapamientos y
   auditoría.
3. **Crear el núcleo Rust.** Implementar `domain` (reglas, `TextMatch`,
   `ComplianceReport`), `application` (casos de uso, cadena de detectores),
   `infrastructure` (regex, hash, salt, recorrido) y una fachada equivalente.
   Crates previstos: `regex`, `sha2`, `rand`, `serde_json`, `thiserror`.
4. **Exponer a Python.** Usar `pyo3` + `maturin` para publicar un módulo que
   respete `pii_anonymizer.api`; mantener la fachada Python como envoltorio
   delgado.
5. **Validar paridad.** Ejecutar los *golden tests* contra la implementación
   Rust y comparar resultados y mensajes de error.
6. **Medir de nuevo.** Aceptar la migración solo si la mejora es significativa
   para el caso de uso real y el coste de empaquetado es asumible.
7. **Liberar con bandera.** Publicar la versión híbrida como *opt-in* y mantener
   la implementación Python como *fallback* durante al menos una versión menor.

## Referencias

- [PyO3](https://pyo3.rs/)
- [maturin](https://www.maturin.rs/)
- [Rust regex](https://docs.rs/regex/)
- [Serde](https://serde.rs/)
