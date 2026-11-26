# Taller El Motor — app de demostración

Aplicación web local para gestionar clientes, vehículos y órdenes de trabajo de
un taller mecánico. Su objetivo es **probar y entender `pii-anonymizer` en un
caso de uso realista**, sin construir un sistema complejo.

La app usa Flask + SQLite para la interfaz y la persistencia, y consume
`pii-anonymizer` **únicamente a través de su API pública**.

---

## 1. Qué demuestra

- **Modo privacidad:** un interruptor global enmascara nombres, correos,
  teléfonos, documentos, direcciones y VIN en listados y fichas.
- **Datos estructurados:** usa `anonymize_map` para limpiar clientes, vehículos
  y órdenes anidadas sin mutar la entrada.
- **Texto libre:** usa `anonymize_text` para sanitizar logs de actividad y el
  laboratorio de texto.
- **Auditoría:** usa `audit_compliance` para mostrar conteos por categoría sin
  exponer valores personales.
- **Exportación:** descarga un JSON completo que ya pasó por `anonymize_map`.
- **Extensibilidad:** registra reglas propias para teléfonos, nombres,
  direcciones y VIN usando solo la API pública.

## 2. Requisitos

- Python 3.11 o superior.
- `pii-anonymizer` instalado en modo editable.
- Flask (incluido en `workshop_app/requirements.txt`).

## 3. Instalación y ejecución

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
pip install -r workshop_app/requirements.txt

python -m workshop_app.app
```

Abre en el navegador:

```text
http://127.0.0.1:5000
```

La primera ejecución crea `workshop_app/workshop.db` y carga datos ficticios.

## 4. Recorrido recomendado

1. Entra a **Clientes** y abre la ficha de Ana María Pérez.
2. Activa **Privacidad ON** en la barra superior y observa cómo cambian los
   datos en la lista y en la ficha.
3. Abre **Órdenes** y revisa una descripción con correo y teléfono: en modo
   privacidad el texto también se sanitiza.
4. Entra a **Auditoría** para ver los conteos agregados y descarga el JSON
   anonimizado.
5. Abre **Logs** para ver mensajes que fueron sanitizados con
   `anonymize_text`.
6. Prueba **Laboratorio** con tus propios textos, correos, tarjetas y teléfonos.

## 5. Funcionalidades

### Clientes

- Crear, editar, listar, buscar y eliminar clientes.
- Campos: nombre, correo, teléfono, documento y dirección.
- Al eliminar un cliente se eliminan en cascada sus vehículos y órdenes.

### Vehículos

- Crear y listar vehículos asociados a un cliente.
- Campos: placa, marca, modelo, año y VIN.
- El VIN se enmascara en modo privacidad.

### Órdenes de trabajo

- Crear y consultar órdenes con cliente, vehículo, descripción, estado y costo.
- Estados: Recibido, En diagnóstico, En reparación, Listo para entrega y
  Entregado.
- La descripción es texto libre y puede contener correos, tarjetas o teléfonos;
  el modo privacidad los enmascara.

### Auditoría

- Reporte agregado de todo el dataset.
- Muestra campos escaneados, campos anonimizados, categorías y reglas aplicadas.
- No incluye valores PII en claro.

### Exportación

- `GET /exportar` descarga `clientes_taller_anonimizado.json`.
- El JSON se genera con `anonymize_map`, así que los datos sensibles ya están
  transformados.

### Laboratorio

- Permite pegar un texto y ver el resultado de `anonymize_text`.
- Útil para entender qué patrones detecta la librería y cómo los reemplaza.

## 6. Cómo se integra con la librería

El punto de entrada es `workshop_app/pii_service.py`:

```python
from pii_anonymizer.api import AnonymizationRule, AnonymizerBuilder

anonymizer = (
    AnonymizerBuilder()
    .with_default_rules()
    .add_rule(
        AnonymizationRule(
            rule_id="phone",
            strategy=AnonymizerBuilder.partial_mask_strategy(3, 2),
            field_names=("phone", "telefono", "teléfono", "celular"),
            detector=PhoneNumberDetector(),
        )
    )
    .build()
)
```

Reglas añadidas por la app:

| Regla | Campos | Estrategia |
| --- | --- | --- |
| `phone` | `phone`, `telefono`, `teléfono`, `celular` | Parcial + detector de teléfonos |
| `full_name` | `full_name`, `nombre`, `customer_name` | Parcial, solo primera letra visible |
| `address` | `address`, `direccion`, `dirección` | Etiqueta fija `[DIRECCIÓN OCULTA]` |
| `vin` | `vin` | Parcial, últimos 4 caracteres visibles |

Las reglas por defecto (`email`, `credit_card`, `password`, `token`,
`document_id`) siguen activas.

## 7. Estructura

```text
workshop_app/
├── app.py                  # Flask app, rutas y presentación
├── db.py                   # SQLite, esquema y datos ficticios
├── pii_service.py          # Integración con pii-anonymizer
├── schema.sql              # Tablas de la base de datos
├── requirements.txt        # Flask
├── static/style.css        # Estilos
├── templates/              # Vistas Jinja
└── tests/test_app.py       # Pruebas de humo con Flask test client
```

## 8. Pruebas

```powershell
python -m pytest workshop_app/tests -q
```

Resultado esperado: **15 pruebas aprobadas**.

Las pruebas usan una base de datos temporal y verifican, entre otras cosas:

- creación de clientes, vehículos y órdenes;
- enmascaramiento en modo privacidad;
- ausencia de PII en auditoría y exportación;
- sanitización de logs y del laboratorio;
- cookies del interruptor de privacidad;
- página 404.

## 9. Reiniciar los datos

Detén el servidor y elimina la base local:

```powershell
Remove-Item workshop_app\workshop.db
```

La próxima ejecución vuelve a crear el esquema y carga los datos ficticios.

## 10. Limitaciones

Esta app es una demostración local, no un sistema listo para producción:

- No tiene autenticación ni control de usuarios.
- No implementa CSRF ni protección contra fuerza bruta.
- Guarda los datos en SQLite local sin cifrado.
- Los datos de ejemplo son ficticios.
- El modo privacidad es una ayuda visual; no reemplaza controles de acceso,
  cifrado ni políticas de retención.
