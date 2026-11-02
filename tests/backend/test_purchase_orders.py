"""
Tests for the purchase order endpoints.

Purchase orders are kept in an in-memory list on the server module (the same
list /api/backlog reads), so each test clears it to stay order-independent.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def clear_purchase_orders():
    """Reset in-memory purchase orders before and after each test."""
    main.purchase_orders.clear()
    yield
    main.purchase_orders.clear()


def make_payload(**overrides):
    payload = {
        "backlog_item_id": "1",
        "supplier_name": "Acme Filters Ltd",
        "quantity": 350,
        "unit_cost": 8.75,
        "expected_delivery_date": "2025-12-15",
        "notes": "Expedite if possible",
    }
    payload.update(overrides)
    return payload


def backlog_by_id(client):
    response = client.get("/api/backlog")
    assert response.status_code == 200
    return {item["id"]: item for item in response.json()}


class TestCreatePurchaseOrder:

    def test_valid_po_returns_201_with_fields(self, client):
        response = client.post("/api/purchase-orders", json=make_payload())
        assert response.status_code == 201
        po = response.json()

        assert po["id"]
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Filters Ltd"
        assert po["quantity"] == 350
        assert po["unit_cost"] == pytest.approx(8.75)
        assert po["expected_delivery_date"] == "2025-12-15"
        assert po["status"] == "Submitted"
        assert po["created_date"]
        assert po["notes"] == "Expedite if possible"

    def test_notes_are_optional(self, client):
        payload = make_payload()
        del payload["notes"]
        response = client.post("/api/purchase-orders", json=payload)
        assert response.status_code == 201
        assert response.json()["notes"] is None

    def test_zero_unit_cost_is_accepted(self, client):
        response = client.post("/api/purchase-orders", json=make_payload(unit_cost=0))
        assert response.status_code == 201

    def test_backlog_reports_purchase_order(self, client):
        before = backlog_by_id(client)
        assert before["1"]["has_purchase_order"] is False
        assert before["1"]["purchase_order_id"] is None

        po = client.post("/api/purchase-orders", json=make_payload()).json()

        after = backlog_by_id(client)
        assert after["1"]["has_purchase_order"] is True
        assert after["1"]["purchase_order_id"] == po["id"]
        # Other backlog items are unaffected
        for item_id, item in after.items():
            if item_id != "1":
                assert item["has_purchase_order"] is False
                assert item["purchase_order_id"] is None

    def test_second_po_for_same_backlog_item_returns_409(self, client):
        assert client.post("/api/purchase-orders", json=make_payload()).status_code == 201
        response = client.post("/api/purchase-orders", json=make_payload(supplier_name="Other Co"))
        assert response.status_code == 409
        assert len(main.purchase_orders) == 1

    def test_unknown_backlog_item_returns_404(self, client):
        response = client.post("/api/purchase-orders", json=make_payload(backlog_item_id="does-not-exist"))
        assert response.status_code == 404
        assert main.purchase_orders == []

    @pytest.mark.parametrize("quantity", [0, -5, 1_000_001])
    def test_invalid_quantity_returns_422(self, client, quantity):
        response = client.post("/api/purchase-orders", json=make_payload(quantity=quantity))
        assert response.status_code == 422
        assert main.purchase_orders == []

    def test_negative_unit_cost_returns_400(self, client):
        response = client.post("/api/purchase-orders", json=make_payload(unit_cost=-0.01))
        assert response.status_code == 400
        assert main.purchase_orders == []

    def test_nan_unit_cost_returns_400_not_500(self, client):
        response = client.post(
            "/api/purchase-orders",
            content=(
                b'{"backlog_item_id":"1","supplier_name":"Acme","quantity":1,'
                b'"unit_cost":NaN,"expected_delivery_date":"2025-12-15"}'
            ),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert main.purchase_orders == []

    @pytest.mark.parametrize("supplier_name", ["", "   "])
    def test_blank_supplier_returns_400(self, client, supplier_name):
        response = client.post("/api/purchase-orders", json=make_payload(supplier_name=supplier_name))
        assert response.status_code == 400
        assert main.purchase_orders == []

    @pytest.mark.parametrize("bad_date", ["", "not-a-date", "2025-13-01"])
    def test_invalid_delivery_date_returns_400(self, client, bad_date):
        response = client.post("/api/purchase-orders", json=make_payload(expected_delivery_date=bad_date))
        assert response.status_code == 400
        assert main.purchase_orders == []

    def test_missing_required_field_returns_422(self, client):
        payload = make_payload()
        del payload["supplier_name"]
        response = client.post("/api/purchase-orders", json=payload)
        assert response.status_code == 422


class TestGetPurchaseOrder:

    def test_get_returns_created_po(self, client):
        created = client.post("/api/purchase-orders", json=make_payload(backlog_item_id="2")).json()

        response = client.get("/api/purchase-orders/2")
        assert response.status_code == 200
        assert response.json() == created

    def test_get_without_po_returns_404(self, client):
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 404
