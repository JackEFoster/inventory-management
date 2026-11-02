"""
Tests for the restocking order endpoints.

Orders are kept in an in-memory list on the server module, so each test
clears it first to stay independent of execution order.
"""
from datetime import datetime

import pytest

import main


@pytest.fixture(autouse=True)
def clear_restocking_orders():
    """Reset in-memory restocking orders before and after each test."""
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


class TestDemandForecastPricing:
    """Forecast entries must carry the pricing fields used for restocking."""

    def test_forecasts_include_unit_cost_and_lead_time(self, client):
        response = client.get("/api/demand")
        assert response.status_code == 200
        for forecast in response.json():
            assert forecast["unit_cost"] is not None
            assert forecast["unit_cost"] > 0
            assert isinstance(forecast["lead_time_days"], int)
            assert forecast["lead_time_days"] > 0


class TestCreateRestockingOrder:

    def test_valid_order_computes_totals_and_lead_time(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [
                {"sku": "WDG-001", "quantity": 100},  # 12.50 x 100, 7 days
                {"sku": "MTR-304", "quantity": 2},    # 285.00 x 2, 21 days
            ],
            "budget": 5000,
        })
        assert response.status_code == 201
        order = response.json()

        assert order["status"] == "Submitted"
        assert order["budget"] == 5000
        assert order["total_value"] == pytest.approx(1820.00)
        assert order["lead_time_days"] == 21  # slowest item

        by_sku = {item["sku"]: item for item in order["items"]}
        assert by_sku["WDG-001"]["unit_cost"] == pytest.approx(12.50)
        assert by_sku["WDG-001"]["line_total"] == pytest.approx(1250.00)
        assert by_sku["WDG-001"]["lead_time_days"] == 7
        assert by_sku["MTR-304"]["line_total"] == pytest.approx(570.00)

    def test_expected_delivery_is_submit_time_plus_max_lead_time(self, client):
        before = datetime.now().replace(microsecond=0)
        response = client.post("/api/restocking-orders", json={
            "items": [
                {"sku": "GSK-203", "quantity": 10},  # 5 days
                {"sku": "CTL-330", "quantity": 1},   # 14 days
            ],
        })
        after = datetime.now().replace(microsecond=0)
        assert response.status_code == 201
        order = response.json()

        created = datetime.fromisoformat(order["created_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert before <= created <= after
        assert (expected - created).days == 14

    def test_order_number_and_id_increment(self, client):
        payload = {"items": [{"sku": "FLT-405", "quantity": 1}]}
        first = client.post("/api/restocking-orders", json=payload).json()
        second = client.post("/api/restocking-orders", json=payload).json()

        year = datetime.now().year
        assert first["order_number"] == f"RST-{year}-0001"
        assert second["order_number"] == f"RST-{year}-0002"
        assert first["id"] != second["id"]

    def test_no_budget_allows_any_total(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "MTR-304", "quantity": 1000}],
        })
        assert response.status_code == 201
        assert response.json()["budget"] is None

    def test_total_equal_to_budget_is_accepted(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 100}],  # 1250.00
            "budget": 1250.00,
        })
        assert response.status_code == 201

    def test_unknown_sku_returns_400(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "NOPE-999", "quantity": 1}],
        })
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]

    # Quantity bounds are enforced by the Pydantic model, so these are 422s
    def test_zero_quantity_is_rejected(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 0}],
        })
        assert response.status_code == 422

    def test_negative_quantity_is_rejected(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": -5}],
        })
        assert response.status_code == 422

    def test_empty_items_returns_400(self, client):
        response = client.post("/api/restocking-orders", json={"items": []})
        assert response.status_code == 400

    def test_duplicate_sku_returns_400(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [
                {"sku": "WDG-001", "quantity": 1},
                {"sku": "WDG-001", "quantity": 2},
            ],
        })
        assert response.status_code == 400

    def test_over_budget_returns_400_and_stores_nothing(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 100}],  # 1250.00
            "budget": 1000,
        })
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"]
        assert main.restocking_orders == []

    def test_negative_budget_returns_400(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 1}],
            "budget": -1,
        })
        assert response.status_code == 400

    def test_nan_budget_returns_400_and_stores_nothing(self, client):
        # Python's json module accepts NaN, so the request body can carry it
        response = client.post(
            "/api/restocking-orders",
            content=b'{"items":[{"sku":"WDG-001","quantity":1000}],"budget":NaN}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert main.restocking_orders == []

    def test_quantity_above_limit_returns_422(self, client):
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 1_000_001}],
        })
        assert response.status_code == 422

    def test_oversized_quantity_integer_returns_422_not_500(self, client):
        response = client.post(
            "/api/restocking-orders",
            content=b'{"items":[{"sku":"WDG-001","quantity":' + b"1" + b"0" * 400 + b'}]}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_client_supplied_price_is_ignored(self, client):
        # Extra fields are not part of the request model, so the server price wins.
        response = client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 10, "unit_cost": 0.01}],
        })
        assert response.status_code == 201
        assert response.json()["items"][0]["unit_cost"] == pytest.approx(12.50)


class TestListRestockingOrders:

    def test_empty_list_when_no_orders(self, client):
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_lists_orders_newest_first(self, client):
        client.post("/api/restocking-orders", json={
            "items": [{"sku": "WDG-001", "quantity": 1}],
        })
        client.post("/api/restocking-orders", json={
            "items": [{"sku": "GSK-203", "quantity": 1}],
        })

        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) == 2
        assert orders[0]["items"][0]["sku"] == "GSK-203"
        assert orders[1]["items"][0]["sku"] == "WDG-001"
