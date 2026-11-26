# Matriz SOLID y GRASP

Este documento mapea los principios de diseño a las clases reales del componente. La columna **Capa** usa los paquetes de Arquitectura Limpia: `domain`, `application`, `infrastructure` y `api`.

## 1. Principios SOLID

| Principio | Clase(s) / artefacto(s) | Capa | Evidencia y justificación |
| --- | --- | --- | --- |
| **S** — Single Responsibility | `AnonymizeMapUseCase`, `AnonymizeTextUseCase`, `RegisterRuleUseCase`, `AuditComplianceUseCase` | `application` | Cada caso de uso ejecuta una sola operación y delega el resto. `AnonymizeMapUseCase` solo obtiene reglas y llama al recorredor; no enmascara ni audita. |
| **S** — Single Responsibility | `InMemoryRuleRepository`, `CompositeStructureTraverser`, `DetectorChain` | `infrastructure` / `application` | Persistencia, recorrido y detección/reemplazo son responsabilidades separadas. `DetectorChain` no conoce diccionarios; el recorredor no conoce regex. |
| **S** — Single Responsibility | `PartialMaskStrategy`, `HashMaskStrategy`, `EmailDetector`, `CreditCardDetector` | `infrastructure` | Cada adaptador tiene una única transformación o un único patrón. Cambiar el formato de hash no afecta al detector de correo. |
| **S** — Single Responsibility (excepción documentada) | `AnonymizerBuilder` | `api` | Concentra el *wiring* y las fábricas por ser el Composition Root. Es una concesión deliberada: centraliza el conocimiento de todas las capas en un único punto. |
| **O** — Open/Closed | `MaskingStrategy`, `SensitivePatternDetector`, `AnonymizerBuilder.add_rule` | `domain` / `api` | Se agregan estrategias y detectores nuevos sin modificar casos de uso ni recorredor. `tests/test_extensibility.py` lo demuestra con `RedactionTagStrategy` y `ColombianCedulaDetector`. |
| **O** — Open/Closed | `DetectorChain` | `application` | La cadena recorre cualquier colección de reglas con detector; no tiene un `if` por categoría. Un detector nuevo se enlaza por configuración. |
| **O** — Open/Closed | `_DetectorHandler` | `application` | Cada eslabón encapsula un detector y delega al siguiente; agregar un eslabón no altera los existentes. |
| **L** — Liskov Substitution | `PartialMaskStrategy` y `HashMaskStrategy` | `infrastructure` | Ambos cumplen `mask(str) -> str`, aceptan cadenas vacías y no lanzan excepciones no declaradas. Cualquiera puede sustituir al otro en una regla. |
| **L** — Liskov Substitution | `EmailDetector`, `CreditCardDetector` y detectores de terceros | `infrastructure` / extensión | Cumplen `category` y `detect(text) -> list[TextMatch]`. `DetectorChain` los trata de forma uniforme y descarta rangos inválidos de forma defensiva. |
| **L** — Liskov Substitution | `FixedSaltProviderStub`, `ConstantSaltProvider` | `tests` / extensión | Sustituyen a `RandomSaltProvider` sin que `HashMaskStrategy` cambie; `get_salt()` siempre retorna `str`. |
| **I** — Interface Segregation | `MaskingStrategy`, `SensitivePatternDetector`, `SaltProvider` | `domain` | Tres contratos pequeños en lugar de una interfaz monolítica. Un detector no necesita saber enmascarar y una estrategia no necesita detectar. |
| **I** — Interface Segregation | `RuleRepository` y `StructureTraverser` | `application` | Persistencia y recorrido se segregaron. `AnonymizeTextUseCase` solo usa `RuleRepository`; no se ve obligado a depender del recorredor. |
| **I** — Interface Segregation | `PiiAnonymizer` | `application` | El puerto primario expone exactamente las cuatro operaciones esenciales, sin filtrar detalles de implementación. |
| **D** — Dependency Inversion | `AnonymizationRule.strategy`, `AnonymizationRule.detector`, `HashMaskStrategy._salt_provider` | `domain` | Las políticas de alto nivel dependen de abstracciones. `HashMaskStrategy` recibe `SaltProvider`; no instancia `secrets` directamente (eso lo hace el adaptador concreto). |
| **D** — Dependency Inversion | `AnonymizeMapUseCase`, `AuditComplianceUseCase` | `application` | Reciben `RuleRepository` y `StructureTraverser` por constructor. No importan `InMemoryRuleRepository` ni `CompositeStructureTraverser`. |
| **D** — Dependency Inversion | `AnonymizerBuilder.build()` | `api` | Inyecta las implementaciones concretas en los casos de uso. Es el único lugar donde se invierte el control del ensamblado. |
| **D** — Dependency Inversion | Regla de imports | Global | `domain` no importa capas externas; `application` solo importa `domain`; `infrastructure` importa `domain` y `application`. Verificación en `arquitectura-c4.md`. |

### Nota sobre LSP y contratos

Python no verifica tipos en tiempo de ejecución, por lo que la conformidad LSP se garantiza mediante:

- `ABC` con `@abstractmethod` para impedir instanciar contratos incompletos.
- Pruebas de extensibilidad con implementaciones externas.
- Validación defensiva de rangos en `DetectorChain`.
- Normalización de entradas en `AnonymizationRule`.

## 2. Patrones GRASP

| Patrón | Clase(s) | Capa | Aplicación y justificación |
| --- | --- | --- | --- |
| **Facade / Controller** | `DefaultPiiAnonymizer` | `application` | Ofrece una interfaz única y delega en el caso de uso correcto. No contiene lógica de negocio ni conoce adaptadores concretos. Actúa como punto de entrada del puerto primario. |
| **Creator** | `AnonymizerBuilder` | `api` | Crea `InMemoryRuleRepository`, `CompositeStructureTraverser`, los cuatro casos de uso, `DefaultPiiAnonymizer` y las estrategias/detectores. Tiene la información de configuración y el ciclo de vida del grafo. |
| **Creator** | `CompositeStructureTraverser` / `DictNode` | `infrastructure` | El recorredor crea `TraversalContext` porque lo posee durante la invocación. `DictNode` crea nodos hijos (`DictNode`, `ListNode`, `ScalarNode`) porque conoce la forma del valor y su ciclo de vida. |
| **Creator** | `AnonymizeTextUseCase` | `application` | Crea `DetectorChain` a partir de las reglas con detector, que son su dato de inicialización inmediato. |
| **Polymorphism** | `MaskingStrategy`, `SensitivePatternDetector` | `domain` | El comportamiento varía por subtipo y se invoca mediante la abstracción. No hay condicionales por categoría ni por tipo de estrategia en los casos de uso. |
| **Polymorphism** | `DataNode`, `DictNode`, `ListNode`, `ScalarNode` | `infrastructure` | `process(context)` se despacha polimórficamente según el nodo; el recorredor no inspecciona tipos con `if/elif` a nivel de recorrido. |
| **Information Expert** | `InMemoryRuleRepository` | `infrastructure` | Es quien conoce el índice de reglas y su orden; por eso implementa `find_by_field` y `get_detector_rules`. |
| **Information Expert** | `TraversalContext` | `infrastructure` | Es el experto en los conteos de la invocación: acumula campos, categorías y reglas aplicadas sin estado global. |
| **Information Expert** | `HashMaskStrategy` | `infrastructure` | Es el experto en la transformación hash y en el uso del `SaltProvider`; nadie más necesita conocer el algoritmo. |
| **Information Expert** | `DetectorChain` | `application` | Es el experto en resolver coincidencias, solapamientos y reemplazos de derecha a izquierda. |
| **Information Expert** | `AnonymizationRule` | `domain` | Es el experto en sus propias invariantes; las valida en `__post_init__` en lugar de dispersar validaciones. |
| **Low Coupling** | Casos de uso y puertos | `application` | Los casos de uso dependen de `RuleRepository` y `StructureTraverser`, no de implementaciones. Cambiar el recorrido o la persistencia no requiere editarlos. |
| **Low Coupling** | `DetectorChain` y eslabones | `application` | La cadena solo conoce `SensitivePatternDetector` y `MaskingStrategy`; no conoce el origen de las reglas ni la estructura de datos. |
| **Low Coupling** | `pii_anonymizer.api` | `api` | El cliente solo importa la fachada; `_internal` puede evolucionar sin afectar contratos. |
| **High Cohesion** | Los cuatro casos de uso | `application` | Cada clase agrupa exclusivamente las operaciones de su escenario; no comparten estado ni utilidades ajenas. |
| **High Cohesion** | `PartialMaskStrategy`, `HashMaskStrategy` | `infrastructure` | Cada estrategia contiene un único algoritmo y sus validaciones. |
| **High Cohesion** | `CompositeStructureTraverser` + nodos | `infrastructure` | El recorrido y la representación de nodos están cohesionados en un mismo módulo; no se mezclan con detección o persistencia. |
| **High Cohesion** | `ComplianceReport` | `domain` | Agrupa exclusivamente los metadatos de auditoría y protege su inmutabilidad. |
| **Indirection** (complementario) | `SaltProvider` | `domain` | Interpone una abstracción entre la estrategia de hash y la fuente de aleatoriedad, permitiendo dobles y rotación de secretos. |
| **Protected Variations** (complementario) | Puertos de dominio y aplicación | Global | Los puntos de variación (algoritmo, patrón, origen del salt, persistencia, recorrido) se protegen detrás de interfaces estables. |
| **Pure Fabrication** (complementario) | `InMemoryRuleRepository`, `CompositeStructureTraverser` | `infrastructure` | No son entidades del negocio, pero se crean para preservar cohesión y bajo acoplamiento en el dominio. |

## 3. Trazabilidad a pruebas

| Principio / patrón | Prueba que lo evidencia |
| --- | --- |
| OCP / Strategy / Chain | `tests/test_extensibility.py` |
| DIP / sustitución de *salt* | `tests/test_builder_and_rules.py` (`FixedSaltProviderStub`) |
| DIP / espía de estrategia | `tests/test_builder_and_rules.py` (`SpyMaskingStrategy`) |
| LSP de detectores | `tests/test_anonymize_text.py`, `tests/test_extensibility.py` |
| SRP de casos de uso | `tests/test_anonymize_map.py`, `tests/test_anonymize_text.py`, `tests/test_compliance_audit.py` |
| Information Expert / Composite | `tests/test_anonymize_map.py`, `tests/test_compliance_audit.py` |
| Low Coupling / Facade | Toda la suite usa solo `pii_anonymizer.api` |

## 4. Balance de diseño

- **Fortaleza:** el núcleo está protegido por interfaces pequeñas y los adaptadores son reemplazables.
- **Concesión:** `AnonymizerBuilder` concentra el conocimiento de todas las capas; se acepta porque es el Composition Root y no participa en el flujo de negocio.
- **Concesión:** `_DetectorHandler` es una clase privada con estado de enlace mutable durante la construcción; después de construir la cadena no se modifica.
- **Riesgo controlado:** el orden de las reglas con detector influye en solapamientos. Está documentado y se prueba con ventanas superpuestas.
