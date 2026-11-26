# ADR-002 — Patrón creacional Builder para el ensamblado

- **Estado:** Aceptado
- **Fecha:** 2026-11-24
- **Decisores:** Equipo de arquitectura y plataforma
- **Ámbito:** `AnonymizerBuilder`, configuración y Composition Root

## Contexto

Construir un `PiiAnonymizer` requiere coordinar:

- Un repositorio de reglas (`InMemoryRuleRepository`).
- Un recorredor de estructuras (`CompositeStructureTraverser`).
- Cuatro casos de uso con dependencias compartidas.
- Una fachada que implemente el puerto primario.
- Estrategias y detectores para las reglas por defecto.
- Un `SaltProvider` opcional para hashes deterministas.

El cliente no debe conocer `_internal`. Además, la configuración debe ser legible, permitir reglas por defecto, inyectar dobles en pruebas y mantener la posibilidad de construir instancias independientes.

Fuerzas:

- **Legibilidad:** el código de configuración se lee una vez y debe ser autoexplicativo.
- **Flexibilidad:** el orden de configuración (`with_default_rules`, `with_salt_provider`, `add_rule`) no debería producir resultados sorpresivos.
- **Testabilidad:** debe ser posible inyectar un `SaltProvider` fijo y reemplazar reglas.
- **Cero dependencias:** no se puede usar un framework de DI.
- **Aislamiento:** el ensamblado no debe filtrar clases internas al cliente.

## Decisión

Implementar `AnonymizerBuilder` en `api/builder.py` con una interfaz fluida:

- `with_default_rules()` activa la inclusión de las cinco reglas por defecto.
- `add_rule(rule)` acumula o reemplaza reglas por `rule_id`.
- `with_salt_provider(provider)` define el proveedor usado al construir.
- `build()` crea un grafo **nuevo** en cada invocación y retorna un `PiiAnonymizer`.
- Las fábricas `partial_mask_strategy`, `hash_mask_strategy`, `email_detector` y `credit_card_detector` permiten configurar adaptadores sin importar `_internal`.

Decisión clave: **las reglas por defecto se materializan en `build()`**, no en `with_default_rules()`. Así, el orden entre `with_default_rules()` y `with_salt_provider()` no altera los hashes.

Otras decisiones:

- `build()` no es un *singleton*: cada llamada produce un repositorio y un recorredor independientes.
- Las reglas del usuario se guardan después de las predeterminadas; un mismo `rule_id` las reemplaza.
- No se cachea el resultado del builder.
- No se expone el repositorio ni los casos de uso.

## Alternativas consideradas

| Alternativa | Ventajas | Desventajas | Decisión |
| --- | --- | --- | --- |
| Constructor manual en el cliente | Control total | El cliente importa `_internal`, viola la frontera, configuración repetitiva | Rechazada |
| Función `create_anonymizer(*args, **kwargs)` | Menos código | Muchos parámetros, orden ambiguo, difícil de extender | Rechazada |
| Service Locator global | Acceso cómodo | Estado global, dependencias ocultas, pruebas frágiles | Rechazada |
| Singleton del anonimizador | Una instancia compartida | Dificulta pruebas y aislamiento; el *salt* y las reglas se contaminan | Rechazada |
| Archivo de configuración YAML/JSON | Configuración externa | Requiere parser y validación; no aporta al caso de uso de librería | Pospuesta |
| Framework de DI | Automatización | Dependencia externa y magia de resolución | Rechazada |
| Builder que construye en cada método | Simplicidad conceptual | Reconstrucciones costosas y semántica confusa | Rechazada |

## Beneficios

- **Configuración legible:** una cadena de llamadas expresa la intención.
- **Orden robusto:** el *salt* se aplica en `build()` a las reglas por defecto.
- **Instancias independientes:** dos `build()` no comparten reglas.
- **Inyección de pruebas:** un `SaltProvider` fijo produce hashes deterministas.
- **Aislamiento:** el cliente no ve `_internal`.
- **Extensibilidad:** `add_rule` acepta cualquier `AnonymizationRule`.
- **Fábricas reutilizables:** estrategias y detectores disponibles sin *wiring* manual.

## Costos y trade-offs de implementación

| Costo | Impacto | Mitigación |
| --- | --- | --- |
| Estado mutable en el builder | No es seguro para configuración concurrente | Configurar al inicio; documentar que no es *thread-safe*. |
| `with_default_rules` difiere el trabajo | Un usuario podría esperar efecto inmediato | Docstring y documentación explican que se materializa en `build()`. |
| Cada `build()` reconstruye el grafo | Costo si se llama en cada request | Documentar que se construya una vez y se reutilice. |
| Dos formas de registrar reglas (`add_rule` y `register_rule`) | Posible confusión | `add_rule` configura antes de construir; `register_rule` opera en caliente. |
| El *salt* solo afecta a estrategias creadas en `build()` | Una estrategia de hash creada antes conserva su proveedor | Documentar que el proveedor se inyecta al crear la estrategia. |
| `build()` no devuelve la misma instancia | Dos llamadas no comparten estado | Es intencional; se prueba en la suite. |
| La fábrica `hash_mask_strategy()` sin proveedor crea uno aleatorio | Hashes no deterministas por defecto | Comportamiento seguro por defecto; documentado en la guía. |

## Consecuencias

- El builder es el único punto que importa simultáneamente `domain`, `application` e `infrastructure`.
- Las reglas por defecto deben poder crearse con el proveedor vigente en `build()`.
- Los consumidores que necesiten hashes estables deben configurar `with_salt_provider`.
- La API pública puede crecer con nuevas fábricas sin modificar el mecanismo de construcción.
- Las pruebas deben cubrir orden de configuración, reemplazo e independencia de instancias.

## Evidencia

- `tests/test_builder_and_rules.py` cubre fluidez, reglas por defecto, reemplazo, fábricas, independencia de builds y validaciones.
- `tests/test_extensibility.py` usa `add_rule` con estrategias y detectores externos.
- `examples/demo_cli.py` muestra la configuración típica con reglas por defecto.

## Referencias

- [Guía de uso](../../01-funcional/guia-de-uso.md)
- [Guía de extensión](../../01-funcional/guia-de-extension.md)
- [Matriz SOLID/GRASP](../matriz-solid-grasp.md)
