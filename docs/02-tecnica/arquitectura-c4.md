# Arquitectura C4

Este documento describe el componente en tres niveles C4: contexto (C1), contenedores (C2) y componentes (C3). Los diagramas reflejan los paquetes y clases reales de la versión 1.0.0.

## 1. Nivel C1 — Contexto

```mermaid
flowchart LR
    Platform["Equipo de plataforma<br/>configura reglas y salt"]
    Consumer["Aplicación consumidora<br/>servicio, job o portal"]
    Auditor["Equipo de seguridad / auditoría<br/>extiende y verifica"]
    Library["pii-anonymizer<br/>librería Python 3.11+<br/>en memoria"]
    Stdlib["Biblioteca estándar de Python<br/>abc, dataclasses, hashlib, re, secrets"]
    Sinks["Destinos<br/>logs, BI, soporte"]

    Platform -->|"construye y configura"| Library
    Auditor -->|"implementa puertos y registra reglas"| Library
    Consumer -->|"anonymize_map / anonymize_text"| Library
    Library -->|"usa"| Stdlib
    Consumer -->|"copia sanitizada"| Sinks
    Consumer -->|"reporte agregado"| Auditor
```

**Lectura:** la librería no depende de servicios externos. El consumidor decide qué hacer con la salida sanitizada. El equipo de auditoría interactúa mediante los puertos públicos y el reporte agregado.

## 2. Nivel C2 — Contenedores

En este contexto, el “sistema” es un único paquete instalable. Los contenedores lógicos son las capas de Arquitectura Limpia.

```mermaid
flowchart TB
    subgraph Client["Proceso del cliente"]
        Service["Servicio / script Python"]
    end

    subgraph Package["pii-anonymizer (paquete instalado)"]
        API["api<br/>Frontera pública + Composition Root<br/>AnonymizerBuilder, __all__"]
        APP["application<br/>Casos de uso, fachada, DetectorChain<br/>puertos primario y secundarios"]
        DOM["domain<br/>AnonymizationRule, TextMatch,<br/>ComplianceReport, excepciones, puertos"]
        INF["infrastructure<br/>Repositorio, Composite,<br/>estrategias y detectores"]
    end

    Service -->|"importa solo api"| API
    API -->|"compone y delega"| APP
    API -->|"instancia adaptadores"| INF
    APP -->|"depende de"| DOM
    INF -->|"implementa puertos de"| APP
    INF -->|"implementa puertos de"| DOM
```

### Contenedores y responsabilidades

| Contenedor | Responsabilidad | Dependencias permitidas |
| --- | --- | --- |
| `api` | Reexportar contratos, construir el grafo de objetos | `domain`, `application`, `infrastructure` |
| `application` | Orquestar casos de uso, cadena de detección y fachada | `domain` |
| `domain` | Modelos inmutables, excepciones y puertos | Ninguna capa; solo biblioteca estándar |
| `infrastructure` | Adaptadores concretos: persistencia, recorrido, estrategias, detectores | `domain`, `application` |

## 3. Nivel C3 — Componentes por capa

```mermaid
flowchart TB
    subgraph API["Capa api (frontera pública)"]
        Builder["AnonymizerBuilder<br/>with_default_rules()<br/>add_rule()<br/>with_salt_provider()<br/>build()<br/>fábricas estáticas"]
        Exports["api/__init__.py y pii_anonymizer/__init__.py<br/>__all__"]
    end

    subgraph APP["Capa application"]
        Facade["DefaultPiiAnonymizer<br/>(Facade/Controller)"]
        MapUC["AnonymizeMapUseCase"]
        TextUC["AnonymizeTextUseCase"]
        RegisterUC["RegisterRuleUseCase"]
        AuditUC["AuditComplianceUseCase"]
        Chain["DetectorChain<br/>(Chain of Responsibility)"]
        AppPorts["PiiAnonymizer<br/>RuleRepository<br/>StructureTraverser"]
    end

    subgraph DOM["Capa domain (núcleo puro)"]
        Models["AnonymizationRule<br/>TextMatch<br/>ComplianceReport"]
        DomPorts["MaskingStrategy<br/>SensitivePatternDetector<br/>SaltProvider"]
        Errors["AnonymizerError<br/>InvalidRuleError"]
    end

    subgraph INF["Capa infrastructure"]
        Repo["InMemoryRuleRepository"]
        Traverser["CompositeStructureTraverser"]
        Nodes["DataNode / DictNode<br/>ListNode / ScalarNode<br/>TraversalContext"]
        Strategies["PartialMaskStrategy<br/>HashMaskStrategy<br/>RandomSaltProvider"]
        Detectors["EmailDetector<br/>CreditCardDetector"]
    end

    Exports -.->|"reexporta PiiAnonymizer"| AppPorts
    Exports -.->|"reexporta modelos"| Models
    Exports -.->|"reexporta puertos"| DomPorts
    Exports -.->|"reexporta excepciones"| Errors
    Builder -->|"crea"| Repo
    Builder -->|"crea"| Traverser
    Builder -->|"crea"| MapUC
    Builder -->|"crea"| TextUC
    Builder -->|"crea"| RegisterUC
    Builder -->|"crea"| AuditUC
    Builder -->|"crea"| Facade
    Builder -->|"instancia"| Strategies
    Builder -->|"instancia"| Detectors

    Facade -->|"delega"| MapUC
    Facade -->|"delega"| TextUC
    Facade -->|"delega"| RegisterUC
    Facade -->|"delega"| AuditUC
    MapUC -->|"usa"| AppPorts
    TextUC -->|"usa"| Chain
    RegisterUC -->|"usa"| AppPorts
    AuditUC -->|"usa"| AppPorts

    MapUC -->|"depende de modelos"| Models
    TextUC -->|"depende de modelos"| Models
    RegisterUC -->|"depende de modelos"| Models
    AuditUC -->|"depende de modelos"| Models
    Chain -->|"usa"| DomPorts
    Chain -->|"lee reglas"| Models

    Repo -.->|"implementa"| AppPorts
    Traverser -.->|"implementa"| AppPorts
    Traverser -->|"compone"| Nodes
    Traverser -->|"usa"| Chain
    Nodes -->|"aplica"| DomPorts
    Strategies -.->|"implementan"| DomPorts
    Detectors -.->|"implementan"| DomPorts
```

### Mapa de clases por componente

| Componente | Clases / interfaces principales |
| --- | --- |
| Frontera | `AnonymizerBuilder`, exports de `api/__init__.py` |
| Aplicación | `DefaultPiiAnonymizer`, los cuatro casos de uso, `DetectorChain`, `AppliedMask` |
| Dominio | `AnonymizationRule`, `TextMatch`, `ComplianceReport`, `AnonymizerError`, `InvalidRuleError`, `MaskingStrategy`, `SensitivePatternDetector`, `SaltProvider` |
| Persistencia | `InMemoryRuleRepository` |
| Recorrido | `CompositeStructureTraverser`, `TraversalContext`, `DataNode`, `DictNode`, `ListNode`, `ScalarNode` |
| Estrategias | `PartialMaskStrategy`, `HashMaskStrategy`, `RandomSaltProvider` |
| Detectores | `EmailDetector`, `CreditCardDetector` |

## 4. Justificación de la Regla de Dependencia

La Regla de Dependencia exige que las dependencias de código fuente apunten hacia políticas de más alto nivel. En este diseño:

1. **`domain` no conoce a nadie.** Contiene los objetos de valor y los puertos que describen *qué* necesita el negocio (`mask`, `detect`, `get_salt`). No importa `application`, `infrastructure` ni `api`.
2. **`application` solo conoce `domain`.** Los casos de uso orquestan reglas y estructuras, pero no saben si el repositorio es en memoria o si el recorrido usa Composite.
3. **`infrastructure` conoce `domain` y `application`.** Implementa los puertos con `re`, `hashlib`, `secrets` y estructuras de Python. Es reemplazable sin tocar los casos de uso.
4. **`api` conoce todas las capas.** Es el *Composition Root*: el único lugar donde se permite conocer simultáneamente interfaces e implementaciones para ensamblar el grafo. Esta excepción es deliberada y localizada.
5. **El cliente solo conoce `api`.** No importa `_internal`, por lo que la implementación puede evolucionar sin romper contratos.

### Verificación de la regla

```bash
# Debe devolver vacío: dominio no importa capas externas
grep -r "pii_anonymizer\._internal\.\(application\|infrastructure\|api\)" src/pii_anonymizer/_internal/domain

# Debe devolver vacío: aplicación no importa infraestructura ni api
grep -r "pii_anonymizer\._internal\.\(infrastructure\|api\)" src/pii_anonymizer/_internal/application

# Debe devolver vacío: pruebas y ejemplo no importan _internal
grep -r "pii_anonymizer\._internal" tests examples
```

En Windows PowerShell puede usarse `Select-String` con patrones equivalentes.

## 5. Flujo de una llamada

```text
Cliente
  → api.AnonymizerBuilder.build()              (una vez)
  → PiiAnonymizer.anonymize_map(data)
  → DefaultPiiAnonymizer
  → AnonymizeMapUseCase
  → RuleRepository.get_all()
  → StructureTraverser.traverse(data, rules)
  → CompositeStructureTraverser + DictNode/ListNode/ScalarNode
  → MaskingStrategy / DetectorChain / SensitivePatternDetector
  → ComplianceReport
```

La secuencia detallada se encuentra en [`diagramas-uml.md`](diagramas-uml.md).

## 6. Decisiones de despliegue

- El paquete se distribuye como *wheel* puro (`py3-none-any`) generado por `setuptools`.
- No requiere servicios, puertos ni credenciales para operar.
- El *salt* se obtiene en tiempo de ejecución; si se usa un proveedor externo, el cliente lo inyecta.
- La librería es adecuada para procesos síncronos y de corta duración. Para *streams* masivos, el consumidor debe fragmentar la entrada y monitorear memoria.
