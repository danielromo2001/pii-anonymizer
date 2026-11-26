"""Persistencia SQLite y datos ficticios de demostración."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

CUSTOMERS = [
    (
        "Ana María Pérez",
        "ana.perez@example.com",
        "300 123 4567",
        "CC 1.020.304.050",
        "Calle 12 #34-56, Valledupar",
    ),
    (
        "Carlos Rodríguez",
        "carlos.rodriguez@example.com",
        "310 555 7788",
        "CC 1.098.765.432",
        "Carrera 9 #12-34, Valledupar",
    ),
    (
        "Laura Gómez",
        "laura.gomez@example.com",
        "320 444 1122",
        "CC 1.112.223.334",
        "Transversal 5 #6-78, Valledupar",
    ),
]

VEHICLES = [
    (1, "ABC123", "Toyota", "Corolla", 2018, "JTDBR32E720123456"),
    (2, "DEF456", "Renault", "Logan", 2020, "LRD5F2E1A01234567"),
    (3, "GHI789", "Mazda", "3", 2021, "JM1BPALM2M1234567"),
]

WORK_ORDERS = [
    (
        1,
        1,
        "Cambio de aceite y filtros. Contactar a ana.perez@example.com o al 300 123 4567.",
        "En reparación",
        180000,
    ),
    (
        2,
        2,
        "Revisión de frenos. El cliente autorizó el cambio con la tarjeta 4111 1111 1111 1111.",
        "En diagnóstico",
        320000,
    ),
    (
        3,
        3,
        "Alineación y balanceo. Enviar la factura a laura.gomez@example.com.",
        "Listo para entrega",
        95000,
    ),
]

LOGS = [
    "Cliente ana.perez@example.com registrado con teléfono 300 123 4567.",
    "Vehículo ABC123 asociado a carlos.rodriguez@example.com.",
    "Orden #2 creada para carlos.rodriguez@example.com con el vehículo DEF456.",
    "Pago de prueba registrado con la tarjeta 4111 1111 1111 1111.",
]


def get_db() -> sqlite3.Connection:
    """Retorna la conexión SQLite asociada al contexto de la aplicación.

    Returns:
        Conexión con ``row_factory`` configurado para acceder por nombre.
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    """Cierra la conexión SQLite al finalizar la petición.

    Args:
        exception: Excepción no controlada, si existe.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    """Crea las tablas y carga los datos de demostración si están vacías."""
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    total = db.execute("SELECT COUNT(*) AS total FROM customers").fetchone()["total"]
    if total == 0:
        _seed(db)
    db.commit()


def init_app(app) -> None:
    """Registra el cierre de conexiones e inicializa la base de datos.

    Args:
        app: Instancia Flask de la aplicación.
    """
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()


def _seed(db: sqlite3.Connection) -> None:
    """Inserta clientes, vehículos, órdenes y logs ficticios.

    Args:
        db: Conexión SQLite abierta.
    """
    customer_ids: list[int] = []
    for customer in CUSTOMERS:
        cursor = db.execute(
            """
            INSERT INTO customers (full_name, email, phone, document_id, address)
            VALUES (?, ?, ?, ?, ?)
            """,
            customer,
        )
        customer_ids.append(cursor.lastrowid)

    vehicle_ids: list[int] = []
    for customer_number, plate, make, model, year, vin in VEHICLES:
        cursor = db.execute(
            """
            INSERT INTO vehicles (customer_id, plate, make, model, year, vin)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                customer_ids[customer_number - 1],
                plate,
                make,
                model,
                year,
                vin,
            ),
        )
        vehicle_ids.append(cursor.lastrowid)

    for customer_number, vehicle_number, description, status, cost in WORK_ORDERS:
        db.execute(
            """
            INSERT INTO work_orders (customer_id, vehicle_id, description, status, cost)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                customer_ids[customer_number - 1],
                vehicle_ids[vehicle_number - 1],
                description,
                status,
                cost,
            ),
        )

    for message in LOGS:
        db.execute("INSERT INTO logs (message) VALUES (?)", (message,))
