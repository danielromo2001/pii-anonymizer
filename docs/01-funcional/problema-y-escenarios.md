# Problema y escenarios de reutilización

## 1. Contexto

Las aplicaciones modernas generan y transportan datos personales en múltiples formatos: trazas de *log*, eventos de auditoría, exportaciones hacia *data warehouses*, respuestas de soporte y mensajes hacia modelos de lenguaje. Una parte de esos datos es **Información Personal Identificable (PII)**: correos electrónicos, números de tarjeta, documentos de identidad, contraseñas, tokens de acceso y teléfonos.

La exposición accidental de PII produce tres tipos de impacto:

1. **Cumplimiento normativo:** incumplimiento de leyes de protección de datos y obligaciones de seguridad de la información.
2. **Riesgo operativo:** credenciales filtradas en logs que permiten acceso no autorizado.
3. **Riesgo reputacional:** datos de clientes visibles en herramientas de observabilidad, soporte o analítica.

Con frecuencia la sanitización se implementa de forma ad hoc en cada servicio, con expresiones regulares duplicadas, comportamientos distintos y sin trazabilidad. Esto genera deuda técnica y dificulta demostrar que un flujo de datos fue tratado correctamente.

## 2. Problema central

No existe un componente único, reutilizable y auditable que:

- Detecte PII en texto plano y en estructuras anidadas.
- Enmascare con estrategias intercambiables y seguras.
- Garantice que la estructura de entrada no se muta.
- Produzca un reporte de cumplimiento sin exponer valores sensibles.
- Permita agregar nuevos patrones y estrategias sin modificar el núcleo.

`pii-anonymizer` cubre exactamente ese espacio: una librería en memoria, sin dependencias externas, con Arquitectura Limpia y una API pública mínima.

## 3. Objetivos

- **OBJ-01:** ofrecer cuatro operaciones estables (`anonymize_map`, `anonymize_text`, `register_rule`, `audit_compliance`).
- **OBJ-02:** aislar los contratos públicos de la implementación interna.
- **OBJ-03:** permitir extensiones de terceros mediante polimorfismo.
- **OBJ-04:** no mutar las estructuras de entrada.
- **OBJ-05:** producir evidencia agregada de anonimización sin PII.
- **OBJ-06:** mantener una cobertura de pruebas superior al 85 %.

## 4. Alcance

### Incluido

- Sanitización en memoria de `dict` y `list` anidados.
- Sanitización de cadenas de texto.
- Reglas por nombre de campo y reglas por detector.
- Estrategias parcial, hash salado y extensiones del cliente.
- Detectores de correo y tarjeta de crédito incluidos.
- Auditoría con conteos por categoría y reglas aplicadas.
- Registro dinámico y reemplazo de reglas por `rule_id`.

### Excluido de la versión 1.0.0

- Persistencia en bases de datos o archivos.
- Cifrado reversible o gestión de claves.
- Detección semántica con modelos de lenguaje.
- Análisis de imágenes, audio o documentos binarios.
- Cumplimiento normativo automático de una jurisdicción específica.

## 5. Escenarios concretos de reutilización

### Escenario A — Sanitización de trazas de log

**Situación:** un servicio de pagos registra líneas como:

```text
INFO pago aprobado para ana.perez@example.com con la tarjeta 4111 1111 1111 1111
```

El equipo de observabilidad necesita conservar la utilidad operativa del log sin almacenar PII.

**Uso del componente:**

1. El servicio construye una sola instancia con `AnonymizerBuilder().with_default_rules().build()`.
2. Antes de entregar la traza al *logger*, invoca `anonymize_text(line)`.
3. La salida conserva el nivel, el mensaje y los dominios de correo, pero oculta la parte local y los dígitos de la tarjeta.

**Beneficios:**

- Un único punto de política para todos los servicios.
- Sin cambios en el formato del log.
- Las reglas `email` y `credit_card` aportan detectores reutilizables.
- El costo por línea es lineal respecto de la longitud del texto.

**Consideración:** el componente sanitiza, pero no reemplaza controles de acceso al sistema de logs.

### Escenario B — Exportación de datos a analítica o BI

**Situación:** un proceso nocturno exporta un `payload` de clientes hacia un *data warehouse*:

```json
{
  "customer": {
    "email": "ana@example.com",
    "document_id": "1029384756",
    "password": "ClaveSuperSecreta2026"
  },
  "orders": [{"id": "ORD-1", "email": "compras@example.com"}]
}
```

**Uso del componente:**

1. El job lee el registro original.
2. Invoca `anonymize_map(payload)` y envía **solo la copia sanitizada** al destino analítico.
3. Opcionalmente invoca `audit_compliance(payload)` para registrar cuántos campos y categorías se trataron.
4. El reporte se envía al sistema de auditoría; nunca incluye valores en claro.

**Beneficios:**

- La entrada original permanece intacta para otros consumidores autorizados.
- El reporte permite evidenciar el tratamiento aplicado.
- El hash salado evita reconstruir contraseñas o documentos directamente.
- Las listas de diccionarios se recorren sin lógica adicional del cliente.

**Consideración:** si el destino necesita correlación entre registros, utilice un `SaltProvider` estable y protegido; con el proveedor aleatorio por defecto, el mismo valor produce hashes distintos.

### Escenario C — Portal de soporte y atención al cliente

**Situación:** un portal interno muestra tickets con notas libres donde los agentes escriben correos y teléfonos. Algunos perfiles solo deben ver información parcial.

**Uso del componente:**

1. El backend construye el `AnonymizerBuilder` con reglas por defecto y una regla adicional de teléfono registrada con `register_rule`.
2. Para perfiles restringidos, aplica `anonymize_map` sobre el ticket antes de serializar la respuesta.
3. Para perfiles con permiso de auditoría, `audit_compliance` entrega métricas de exposición sin revelar el contenido.
4. Un equipo externo puede aportar un `MaskingStrategy` con etiqueta `[REDACTED]` para campos de altísima sensibilidad, sin tocar el núcleo.

**Beneficios:**

- Política de exposición uniforme entre módulos.
- La extensión de teléfonos se implementa fuera de la librería y se registra dinámicamente.
- El reporte facilita métricas como “campos con PII por categoría”.
- La API pública evita que el portal dependa de clases internas.

**Consideración:** el dominio de un correo se conserva por defecto para facilitar soporte; si el dominio también es sensible, registre una estrategia `RedactionTagStrategy` para ese campo.

## 6. Actores

| Actor | Interacción |
| --- | --- |
| Equipo de plataforma | Construye y configura el componente; define reglas y *salt*. |
| Servicios consumidores | Invocan las cuatro operaciones de la API. |
| Equipo de seguridad / auditoría | Extiende estrategias y detectores, revisa reportes. |
| Operaciones / observabilidad | Consume logs y métricas ya sanitizados. |

## 7. Supuestos

- Los datos caben en memoria; no se procesan *streams* ilimitados.
- Los valores sensibles relevantes son texto o números convertibles a texto.
- Los nombres de campo son conocidos o detectables mediante patrones.
- El cliente es responsable de proteger el `SaltProvider` y los canales de salida.

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Regla incompleta deja PII en claro | Auditabilidad, reglas por defecto y pruebas de extensión. |
| Falso positivo enmascara datos útiles | Estrategias parciales, configuración de reglas y revisión de patrones. |
| *Salt* filtrado | Gestionar el proveedor como secreto y rotarlo cuando corresponda. |
| Reporte usado como sustituto de controles | El reporte es evidencia agregada; no reemplaza autorización ni cifrado. |
| Crecimiento excesivo de estructuras | El recorrido es lineal y crea copias; dimensionar memoria según el caso de uso. |

## 9. Métricas de éxito

- Porcentaje de servicios que sanitizan antes de persistir o exportar.
- Cantidad de hallazgos por categoría detectados en auditorías.
- Incidentes de PII en logs o exportaciones, con tendencia a cero.
- Cobertura de pruebas ≥ 85 % y suite estable en integración continua.
- Tiempo de incorporación de una regla nueva sin modificar el núcleo.
