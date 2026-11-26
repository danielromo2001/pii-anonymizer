"""App web de demostración: clientes, vehículos y órdenes de un taller."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from workshop_app import db
from workshop_app.pii_service import WorkshopPiiService

STATUSES = (
    "Recibido",
    "En diagnóstico",
    "En reparación",
    "Listo para entrega",
    "Entregado",
)

STATUS_CLASSES = {
    "Recibido": "status-received",
    "En diagnóstico": "status-diagnosis",
    "En reparación": "status-repair",
    "Listo para entrega": "status-ready",
    "Entregado": "status-delivered",
}

DEFAULT_DATABASE = Path(__file__).with_name("workshop.db")


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Crea y configura la aplicación Flask.

    Args:
        test_config: Configuración alternativa para pruebas.

    Returns:
        Aplicación lista para ejecutarse.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "taller-demo-secret"),
        DATABASE=os.environ.get("WORKSHOP_DB", str(DEFAULT_DATABASE)),
    )
    if test_config:
        app.config.update(test_config)

    app.extensions["pii"] = WorkshopPiiService()
    db.init_app(app)
    register_routes(app)
    return app


def pii() -> WorkshopPiiService:
    """Retorna el servicio de privacidad de la aplicación actual."""
    return current_app.extensions["pii"]


def privacy_enabled() -> bool:
    """Indica si el modo privacidad está activo en la petición actual."""
    return request.cookies.get("privacy") == "1"


def present_customer(row: Any) -> dict[str, Any]:
    """Convierte un cliente en diccionario y lo enmascara si aplica.

    Args:
        row: Fila de SQLite o diccionario con los campos del cliente.

    Returns:
        Diccionario listo para la plantilla.
    """
    data = dict(row)
    if privacy_enabled():
        masked = pii().mask_map(
            {
                "full_name": data["full_name"],
                "email": data["email"],
                "phone": data["phone"],
                "document_id": data["document_id"],
                "address": data["address"],
            }
        )
        data.update(masked)
    return data


def present_vehicle(row: Any) -> dict[str, Any]:
    """Convierte un vehículo en diccionario y enmascara VIN y cliente.

    Args:
        row: Fila de SQLite o diccionario con los campos del vehículo.

    Returns:
        Diccionario listo para la plantilla.
    """
    data = dict(row)
    if privacy_enabled():
        payload: dict[str, Any] = {"vin": data["vin"]}
        if "customer_name" in data:
            payload["full_name"] = data["customer_name"]
        masked = pii().mask_map(payload)
        data["vin"] = masked["vin"]
        if "customer_name" in data:
            data["customer_name"] = masked["full_name"]
    return data


def present_order(row: Any) -> dict[str, Any]:
    """Convierte una orden en diccionario y enmascara nombre y descripción.

    Args:
        row: Fila de SQLite o diccionario con los campos de la orden.

    Returns:
        Diccionario listo para la plantilla.
    """
    data = dict(row)
    if privacy_enabled():
        payload: dict[str, Any] = {"description": data["description"]}
        if "customer_name" in data:
            payload["full_name"] = data["customer_name"]
        masked = pii().mask_map(payload)
        data["description"] = masked["description"]
        if "customer_name" in data:
            data["customer_name"] = masked["full_name"]
    return data


def build_full_payload() -> dict[str, Any]:
    """Construye la estructura completa que se audita y exporta.

    Returns:
        Diccionario anidado con clientes, vehículos y órdenes.
    """
    connection = db.get_db()
    customers = connection.execute("SELECT * FROM customers ORDER BY id").fetchall()
    vehicles = connection.execute("SELECT * FROM vehicles ORDER BY id").fetchall()
    orders = connection.execute(
        """
        SELECT wo.*, c.full_name AS customer_name, v.plate AS vehicle_plate
        FROM work_orders wo
        JOIN customers c ON c.id = wo.customer_id
        JOIN vehicles v ON v.id = wo.vehicle_id
        ORDER BY wo.id
        """
    ).fetchall()

    return {
        "customers": [
            {
                "full_name": customer["full_name"],
                "email": customer["email"],
                "phone": customer["phone"],
                "document_id": customer["document_id"],
                "address": customer["address"],
            }
            for customer in customers
        ],
        "vehicles": [
            {
                "plate": vehicle["plate"],
                "make": vehicle["make"],
                "model": vehicle["model"],
                "year": vehicle["year"],
                "vin": vehicle["vin"],
            }
            for vehicle in vehicles
        ],
        "work_orders": [
            {
                "description": order["description"],
                "status": order["status"],
                "cost": order["cost"],
                "customer": {"full_name": order["customer_name"]},
                "vehicle": {"plate": order["vehicle_plate"]},
            }
            for order in orders
        ],
    }


def _customer_form_data() -> dict[str, str]:
    """Extrae y normaliza los campos del formulario de cliente."""
    return {
        "full_name": request.form.get("full_name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "document_id": request.form.get("document_id", "").strip(),
        "address": request.form.get("address", "").strip(),
    }


def _validate_customer(data: dict[str, str]) -> str | None:
    """Valida los datos de un cliente.

    Args:
        data: Campos normalizados.

    Returns:
        Mensaje de error o ``None`` si es válido.
    """
    if not data["full_name"]:
        return "El nombre es obligatorio."
    if not data["email"] or "@" not in data["email"]:
        return "El correo electrónico no es válido."
    if not data["phone"]:
        return "El teléfono es obligatorio."
    if not data["document_id"]:
        return "El documento de identidad es obligatorio."
    return None


def _vehicle_form_data() -> dict[str, str]:
    """Extrae y normaliza los campos del formulario de vehículo."""
    return {
        "customer_id": request.form.get("customer_id", "").strip(),
        "plate": request.form.get("plate", "").strip().upper(),
        "make": request.form.get("make", "").strip(),
        "model": request.form.get("model", "").strip(),
        "year": request.form.get("year", "").strip(),
        "vin": request.form.get("vin", "").strip().upper(),
    }


def _validate_vehicle(data: dict[str, str], connection: Any) -> str | None:
    """Valida los datos de un vehículo.

    Args:
        data: Campos normalizados.
        connection: Conexión SQLite.

    Returns:
        Mensaje de error o ``None`` si es válido.
    """
    if not data["customer_id"].isdigit():
        return "Selecciona un cliente."
    if connection.execute(
        "SELECT id FROM customers WHERE id = ?", (int(data["customer_id"]),)
    ).fetchone() is None:
        return "El cliente seleccionado no existe."
    if not data["plate"]:
        return "La placa es obligatoria."
    if not data["make"]:
        return "La marca es obligatoria."
    if not data["model"]:
        return "El modelo es obligatorio."
    if not data["year"].isdigit() or not 1900 <= int(data["year"]) <= 2100:
        return "El año debe ser un número entre 1900 y 2100."
    return None


def _work_order_form_data() -> dict[str, str]:
    """Extrae y normaliza los campos del formulario de orden."""
    return {
        "customer_id": request.form.get("customer_id", "").strip(),
        "vehicle_id": request.form.get("vehicle_id", "").strip(),
        "description": request.form.get("description", "").strip(),
        "status": request.form.get("status", "").strip(),
        "cost": request.form.get("cost", "0").strip(),
    }


def _validate_work_order(data: dict[str, str], connection: Any) -> str | None:
    """Valida los datos de una orden de trabajo.

    Args:
        data: Campos normalizados.
        connection: Conexión SQLite.

    Returns:
        Mensaje de error o ``None`` si es válido.
    """
    if not data["customer_id"].isdigit():
        return "Selecciona un cliente."
    if not data["vehicle_id"].isdigit():
        return "Selecciona un vehículo."
    vehicle = connection.execute(
        "SELECT customer_id FROM vehicles WHERE id = ?", (int(data["vehicle_id"]),)
    ).fetchone()
    if vehicle is None:
        return "El vehículo seleccionado no existe."
    if vehicle["customer_id"] != int(data["customer_id"]):
        return "El vehículo no pertenece al cliente seleccionado."
    if not data["description"]:
        return "La descripción es obligatoria."
    if data["status"] not in STATUSES:
        return "El estado seleccionado no es válido."
    try:
        cost = float(data["cost"])
    except ValueError:
        return "El costo debe ser un número."
    if cost < 0:
        return "El costo no puede ser negativo."
    return None


def register_routes(app: Flask) -> None:
    """Registra todas las rutas de la aplicación.

    Args:
        app: Instancia Flask.
    """

    @app.context_processor
    def inject_globals() -> dict[str, Any]:
        return {
            "privacy": privacy_enabled(),
            "statuses": STATUSES,
            "app_name": "Taller El Motor",
        }

    @app.template_filter("currency")
    def currency(value: Any) -> str:
        try:
            return f"${float(value):,.0f}".replace(",", ".")
        except (TypeError, ValueError):
            return "$0"

    @app.template_filter("status_class")
    def status_class(status: str) -> str:
        return STATUS_CLASSES.get(status, "status-received")

    @app.get("/")
    def dashboard():
        connection = db.get_db()
        stats = {
            "customers": connection.execute(
                "SELECT COUNT(*) AS total FROM customers"
            ).fetchone()["total"],
            "vehicles": connection.execute(
                "SELECT COUNT(*) AS total FROM vehicles"
            ).fetchone()["total"],
            "orders": connection.execute(
                "SELECT COUNT(*) AS total FROM work_orders"
            ).fetchone()["total"],
            "open_orders": connection.execute(
                "SELECT COUNT(*) AS total FROM work_orders WHERE status != 'Entregado'"
            ).fetchone()["total"],
        }
        rows = connection.execute(
            """
            SELECT wo.*, c.full_name AS customer_name, v.plate AS vehicle_plate
            FROM work_orders wo
            JOIN customers c ON c.id = wo.customer_id
            JOIN vehicles v ON v.id = wo.vehicle_id
            ORDER BY wo.id DESC
            LIMIT 5
            """
        ).fetchall()
        return render_template(
            "dashboard.html",
            stats=stats,
            recent_orders=[present_order(row) for row in rows],
        )

    @app.get("/clientes")
    def customers():
        query = request.args.get("q", "").strip()
        connection = db.get_db()
        if query:
            like = f"%{query}%"
            rows = connection.execute(
                """
                SELECT * FROM customers
                WHERE full_name LIKE ? OR email LIKE ?
                   OR phone LIKE ? OR document_id LIKE ?
                ORDER BY full_name
                """,
                (like, like, like, like),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM customers ORDER BY full_name"
            ).fetchall()
        return render_template(
            "customers.html",
            customers=[present_customer(row) for row in rows],
            query=query,
        )

    @app.route("/clientes/nuevo", methods=["GET", "POST"])
    def customer_create():
        form: dict[str, Any] = {}
        if request.method == "POST":
            form = _customer_form_data()
            error = _validate_customer(form)
            if error:
                flash(error, "error")
            else:
                connection = db.get_db()
                cursor = connection.execute(
                    """
                    INSERT INTO customers
                        (full_name, email, phone, document_id, address)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        form["full_name"],
                        form["email"],
                        form["phone"],
                        form["document_id"],
                        form["address"],
                    ),
                )
                connection.execute(
                    "INSERT INTO logs (message) VALUES (?)",
                    (
                        f"Cliente {form['email']} registrado con teléfono "
                        f"{form['phone']}.",
                    ),
                )
                connection.commit()
                flash("Cliente registrado correctamente.", "success")
                return redirect(
                    url_for("customer_detail", customer_id=cursor.lastrowid)
                )
        return render_template("customer_form.html", customer=None, form=form)

    @app.get("/clientes/<int:customer_id>")
    def customer_detail(customer_id: int):
        connection = db.get_db()
        customer = connection.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if customer is None:
            abort(404)
        vehicles = connection.execute(
            "SELECT * FROM vehicles WHERE customer_id = ? ORDER BY plate",
            (customer_id,),
        ).fetchall()
        orders = connection.execute(
            """
            SELECT wo.*, c.full_name AS customer_name, v.plate AS vehicle_plate
            FROM work_orders wo
            JOIN customers c ON c.id = wo.customer_id
            JOIN vehicles v ON v.id = wo.vehicle_id
            WHERE wo.customer_id = ?
            ORDER BY wo.id DESC
            """,
            (customer_id,),
        ).fetchall()
        return render_template(
            "customer_detail.html",
            customer=present_customer(customer),
            vehicles=[present_vehicle(vehicle) for vehicle in vehicles],
            orders=[present_order(order) for order in orders],
        )

    @app.route("/clientes/<int:customer_id>/editar", methods=["GET", "POST"])
    def customer_edit(customer_id: int):
        connection = db.get_db()
        customer = connection.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if customer is None:
            abort(404)

        if request.method == "POST":
            form = _customer_form_data()
            error = _validate_customer(form)
            if error:
                flash(error, "error")
            else:
                connection.execute(
                    """
                    UPDATE customers
                    SET full_name = ?, email = ?, phone = ?,
                        document_id = ?, address = ?
                    WHERE id = ?
                    """,
                    (
                        form["full_name"],
                        form["email"],
                        form["phone"],
                        form["document_id"],
                        form["address"],
                        customer_id,
                    ),
                )
                connection.execute(
                    "INSERT INTO logs (message) VALUES (?)",
                    (f"Cliente {form['email']} actualizado.",),
                )
                connection.commit()
                flash("Cliente actualizado correctamente.", "success")
                return redirect(
                    url_for("customer_detail", customer_id=customer_id)
                )
        else:
            form = dict(customer)

        return render_template(
            "customer_form.html", customer=customer, form=form
        )

    @app.post("/clientes/<int:customer_id>/eliminar")
    def customer_delete(customer_id: int):
        connection = db.get_db()
        customer = connection.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if customer is None:
            abort(404)
        connection.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        connection.execute(
            "INSERT INTO logs (message) VALUES (?)",
            (f"Cliente {customer['email']} eliminado.",),
        )
        connection.commit()
        flash("Cliente eliminado junto con sus vehículos y órdenes.", "success")
        return redirect(url_for("customers"))

    @app.get("/vehiculos")
    def vehicles():
        rows = db.get_db().execute(
            """
            SELECT v.*, c.full_name AS customer_name
            FROM vehicles v
            JOIN customers c ON c.id = v.customer_id
            ORDER BY v.plate
            """
        ).fetchall()
        return render_template(
            "vehicles.html", vehicles=[present_vehicle(row) for row in rows]
        )

    @app.route("/vehiculos/nuevo", methods=["GET", "POST"])
    def vehicle_create():
        connection = db.get_db()
        customers = [
            dict(row)
            for row in connection.execute(
                "SELECT id, full_name, email FROM customers ORDER BY full_name"
            ).fetchall()
        ]
        if not customers:
            flash("Primero registra al menos un cliente.", "error")
            return redirect(url_for("customer_create"))

        if request.method == "POST":
            form = _vehicle_form_data()
            error = _validate_vehicle(form, connection)
            if error:
                flash(error, "error")
            else:
                customer = connection.execute(
                    "SELECT email FROM customers WHERE id = ?",
                    (int(form["customer_id"]),),
                ).fetchone()
                cursor = connection.execute(
                    """
                    INSERT INTO vehicles
                        (customer_id, plate, make, model, year, vin)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(form["customer_id"]),
                        form["plate"],
                        form["make"],
                        form["model"],
                        int(form["year"]),
                        form["vin"],
                    ),
                )
                connection.execute(
                    "INSERT INTO logs (message) VALUES (?)",
                    (
                        f"Vehículo {form['plate']} asociado a "
                        f"{customer['email']}.",
                    ),
                )
                connection.commit()
                flash("Vehículo registrado correctamente.", "success")
                return redirect(
                    url_for("customer_detail", customer_id=int(form["customer_id"]))
                )
        else:
            form = {
                "customer_id": request.args.get("customer_id", ""),
                "plate": "",
                "make": "",
                "model": "",
                "year": "",
                "vin": "",
            }

        return render_template(
            "vehicle_form.html", customers=customers, form=form
        )

    @app.get("/ordenes")
    def work_orders():
        rows = db.get_db().execute(
            """
            SELECT wo.*, c.full_name AS customer_name, v.plate AS vehicle_plate
            FROM work_orders wo
            JOIN customers c ON c.id = wo.customer_id
            JOIN vehicles v ON v.id = wo.vehicle_id
            ORDER BY wo.id DESC
            """
        ).fetchall()
        return render_template(
            "work_orders.html", orders=[present_order(row) for row in rows]
        )

    @app.route("/ordenes/nueva", methods=["GET", "POST"])
    def work_order_create():
        connection = db.get_db()
        customers = [
            dict(row)
            for row in connection.execute(
                "SELECT id, full_name, email FROM customers ORDER BY full_name"
            ).fetchall()
        ]
        vehicles = [
            dict(row)
            for row in connection.execute(
                """
                SELECT v.id, v.plate, v.make, v.model, v.customer_id,
                       c.full_name AS customer_name
                FROM vehicles v
                JOIN customers c ON c.id = v.customer_id
                ORDER BY v.plate
                """
            ).fetchall()
        ]
        if not customers or not vehicles:
            flash(
                "Necesitas al menos un cliente y un vehículo para crear una orden.",
                "error",
            )
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            form = _work_order_form_data()
            error = _validate_work_order(form, connection)
            if error:
                flash(error, "error")
            else:
                customer = connection.execute(
                    "SELECT email FROM customers WHERE id = ?",
                    (int(form["customer_id"]),),
                ).fetchone()
                vehicle = connection.execute(
                    "SELECT plate FROM vehicles WHERE id = ?",
                    (int(form["vehicle_id"]),),
                ).fetchone()
                cursor = connection.execute(
                    """
                    INSERT INTO work_orders
                        (customer_id, vehicle_id, description, status, cost)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        int(form["customer_id"]),
                        int(form["vehicle_id"]),
                        form["description"],
                        form["status"],
                        float(form["cost"]),
                    ),
                )
                connection.execute(
                    "INSERT INTO logs (message) VALUES (?)",
                    (
                        f"Orden #{cursor.lastrowid} creada para "
                        f"{customer['email']} con el vehículo {vehicle['plate']}.",
                    ),
                )
                connection.commit()
                flash("Orden de trabajo creada correctamente.", "success")
                return redirect(
                    url_for("work_order_detail", order_id=cursor.lastrowid)
                )
        else:
            form = {
                "customer_id": request.args.get("customer_id", ""),
                "vehicle_id": request.args.get("vehicle_id", ""),
                "description": "",
                "status": STATUSES[0],
                "cost": "0",
            }

        return render_template(
            "work_order_form.html",
            customers=customers,
            vehicles=vehicles,
            form=form,
        )

    @app.get("/ordenes/<int:order_id>")
    def work_order_detail(order_id: int):
        row = db.get_db().execute(
            """
            SELECT wo.*,
                   c.full_name AS customer_name,
                   c.email AS customer_email,
                   c.phone AS customer_phone,
                   c.document_id AS customer_document_id,
                   c.address AS customer_address,
                   v.plate AS vehicle_plate,
                   v.make AS vehicle_make,
                   v.model AS vehicle_model,
                   v.year AS vehicle_year,
                   v.vin AS vehicle_vin
            FROM work_orders wo
            JOIN customers c ON c.id = wo.customer_id
            JOIN vehicles v ON v.id = wo.vehicle_id
            WHERE wo.id = ?
            """,
            (order_id,),
        ).fetchone()
        if row is None:
            abort(404)

        customer = {
            "id": row["customer_id"],
            "full_name": row["customer_name"],
            "email": row["customer_email"],
            "phone": row["customer_phone"],
            "document_id": row["customer_document_id"],
            "address": row["customer_address"],
        }
        vehicle = {
            "id": row["vehicle_id"],
            "plate": row["vehicle_plate"],
            "make": row["vehicle_make"],
            "model": row["vehicle_model"],
            "year": row["vehicle_year"],
            "vin": row["vehicle_vin"],
        }
        order = {
            "id": row["id"],
            "status": row["status"],
            "cost": row["cost"],
            "created_at": row["created_at"],
            "description": row["description"],
        }

        if privacy_enabled():
            customer = pii().mask_map(customer)
            vehicle = pii().mask_map(vehicle)
            order["description"] = pii().mask_map(
                {"description": order["description"]}
            )["description"]

        return render_template(
            "work_order_detail.html",
            order=order,
            customer=customer,
            vehicle=vehicle,
        )

    @app.get("/auditoria")
    def audit():
        payload = build_full_payload()
        report = pii().audit(payload)
        sample = (
            pii().mask_map(payload["customers"][0])
            if payload["customers"]
            else None
        )
        return render_template("audit.html", report=report, sample=sample)

    @app.get("/logs")
    def logs():
        rows = db.get_db().execute(
            "SELECT id, message, created_at FROM logs ORDER BY id DESC LIMIT 100"
        ).fetchall()
        entries = [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "message": pii().mask_text(row["message"]),
            }
            for row in rows
        ]
        return render_template("logs.html", logs=entries)

    @app.route("/laboratorio", methods=["GET", "POST"])
    def lab():
        sample = (
            "El cliente ana.perez@example.com reporta un cobro con la tarjeta "
            "4111 1111 1111 1111. Contacto: 300 123 4567."
        )
        original = sample
        sanitized = ""
        if request.method == "POST":
            original = request.form.get("text", "")
            sanitized = pii().mask_text(original)
        return render_template(
            "lab.html", original=original, sanitized=sanitized
        )

    @app.get("/exportar")
    def export():
        sanitized = pii().mask_map(build_full_payload())
        body = json.dumps(sanitized, ensure_ascii=False, indent=2)
        response = app.response_class(body, mimetype="application/json")
        response.headers["Content-Disposition"] = (
            "attachment; filename=clientes_taller_anonimizado.json"
        )
        return response

    @app.post("/privacidad")
    def toggle_privacy():
        next_url = request.form.get("next", "/")
        if not next_url.startswith("/") or next_url.startswith("//"):
            next_url = url_for("dashboard")
        response = redirect(next_url)
        response.set_cookie(
            "privacy",
            "0" if privacy_enabled() else "1",
            max_age=60 * 60 * 24 * 30,
            samesite="Lax",
        )
        return response

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404


if __name__ == "__main__":
    create_app().run(
        host="127.0.0.1",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
