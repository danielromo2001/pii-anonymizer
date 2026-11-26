"""Pruebas de humo de la app de demostración del taller."""

from __future__ import annotations

import json

import pytest

from workshop_app import db
from workshop_app.app import create_app


@pytest.fixture()
def app(tmp_path):
    """Crea una app aislada con una base de datos temporal."""
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(tmp_path / "workshop-test.db"),
        }
    )
    yield application


@pytest.fixture()
def client(app):
    """Cliente HTTP de Flask para las pruebas."""
    return app.test_client()


def test_dashboard_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Taller El Motor" in response.get_data(as_text=True)
    assert "Órdenes recientes" in response.get_data(as_text=True)


def test_customer_creation(client):
    response = client.post(
        "/clientes/nuevo",
        data={
            "full_name": "Pedro Picapiedra",
            "email": "pedro.picapiedra@example.com",
            "phone": "301 222 3344",
            "document_id": "CC 9.999.888",
            "address": "Piedra Lisa 123",
        },
        follow_redirects=True,
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Cliente registrado correctamente." in text
    assert "pedro.picapiedra@example.com" in text


def test_privacy_mode_masks_customer_data(client):
    client.set_cookie("privacy", "1")
    response = client.get("/clientes")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "ana.perez@example.com" not in text
    assert "an*****ez@example.com" in text
    assert "300 123 4567" not in text
    assert "300*******67" in text


def test_audit_page_has_no_raw_pii(client):
    response = client.get("/auditoria")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Campos escaneados" in text
    assert "ana.perez@example.com" not in text
    assert "300 123 4567" not in text


def test_export_is_anonymized(client):
    response = client.get("/exportar")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "attachment" in response.headers["Content-Disposition"]

    data = json.loads(text)
    assert data["customers"]
    assert "ana.perez@example.com" not in text
    assert "an*****ez@example.com" in text
    assert "300 123 4567" not in text
    assert "4111 1111 1111 1111" not in text


def test_lab_masks_text(client):
    response = client.post(
        "/laboratorio",
        data={
            "text": (
                "Contacto: ana.perez@example.com, tarjeta "
                "4111 1111 1111 1111 y teléfono 300 123 4567."
            )
        },
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "an*****ez@example.com" in text
    assert "***************1111" in text
    assert "300*******67" in text

    result_panel = text.split('class="code-block result-panel">', 1)[1].split(
        "</pre>", 1
    )[0]
    assert "ana.perez@example.com" not in result_panel
    assert "4111 1111 1111 1111" not in result_panel
    assert "300 123 4567" not in result_panel


def test_logs_are_sanitized(client):
    response = client.get("/logs")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "ana.perez@example.com" not in text
    assert "an*****ez@example.com" in text


def test_vehicle_creation(client):
    response = client.post(
        "/vehiculos/nuevo",
        data={
            "customer_id": "1",
            "plate": "XYZ999",
            "make": "Honda",
            "model": "Civic",
            "year": "2022",
            "vin": "1HGCM82633A004352",
        },
        follow_redirects=True,
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Vehículo registrado correctamente." in text
    assert "XYZ999" in text


def test_work_order_creation(client):
    response = client.post(
        "/ordenes/nueva",
        data={
            "customer_id": "1",
            "vehicle_id": "1",
            "description": "Revisión general. Contacto: ana.perez@example.com.",
            "status": "Recibido",
            "cost": "50000",
        },
        follow_redirects=True,
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Orden de trabajo creada correctamente." in text
    assert "Revisión general" in text


def test_customer_edit(client):
    response = client.post(
        "/clientes/1/editar",
        data={
            "full_name": "Ana María Pérez Actualizada",
            "email": "ana.actualizada@example.com",
            "phone": "300 999 8877",
            "document_id": "CC 1.020.304.050",
            "address": "Nueva dirección 123",
        },
        follow_redirects=True,
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Cliente actualizado correctamente." in text
    assert "Ana María Pérez Actualizada" in text
    assert "ana.actualizada@example.com" in text


def test_customer_delete(client):
    response = client.post("/clientes/3/eliminar", follow_redirects=True)
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Cliente eliminado junto con sus vehículos y órdenes." in text
    assert "Laura Gómez" not in text


def test_work_order_rejects_vehicle_from_other_customer(client):
    response = client.post(
        "/ordenes/nueva",
        data={
            "customer_id": "1",
            "vehicle_id": "2",
            "description": "Prueba de validación",
            "status": "Recibido",
            "cost": "10000",
        },
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "El vehículo no pertenece al cliente seleccionado." in text


def test_privacy_toggle_sets_cookie(client):
    response = client.post("/privacidad", data={"next": "/clientes"})
    assert response.status_code == 302
    assert "privacy=1" in response.headers["Set-Cookie"]


def test_not_found(client):
    response = client.get("/clientes/9999")
    assert response.status_code == 404
    assert "No encontramos esa página." in response.get_data(as_text=True)


def test_reseed_works_after_deleting_all_customers(tmp_path):
    database = str(tmp_path / "reseed.db")
    first_app = create_app({"TESTING": True, "DATABASE": database})
    with first_app.app_context():
        connection = db.get_db()
        connection.execute("DELETE FROM customers")
        connection.commit()

    second_app = create_app({"TESTING": True, "DATABASE": database})
    client = second_app.test_client()

    customers_response = client.get("/clientes")
    customers_text = customers_response.get_data(as_text=True)
    assert customers_response.status_code == 200
    assert "Ana María Pérez" in customers_text

    vehicles_response = client.get("/vehiculos")
    vehicles_text = vehicles_response.get_data(as_text=True)
    assert vehicles_response.status_code == 200
    assert "ABC123" in vehicles_text
