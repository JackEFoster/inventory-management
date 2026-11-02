"""
Tests for the reports endpoints, including the global filters they now honour
(warehouse, category, status, month) like /api/orders does.
"""
import pytest


def _orders(client, **params):
    return client.get("/api/orders", params=params).json()


class TestQuarterlyReports:
    def test_unfiltered_shape_and_order(self, client):
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200
        data = response.json()
        assert [q["quarter"] for q in data] == sorted(
            (q["quarter"] for q in data), key=lambda s: (s[3:], s[:2])
        )
        for q in data:
            assert set(q) >= {"quarter", "total_orders", "total_revenue", "avg_order_value", "fulfillment_rate"}
            assert q["total_orders"] > 0
            assert 0 <= q["fulfillment_rate"] <= 100

    def test_totals_match_orders(self, client):
        data = client.get("/api/reports/quarterly").json()
        assert sum(q["total_orders"] for q in data) == len(_orders(client))

    @pytest.mark.parametrize(
        "params",
        [
            {"warehouse": "Tokyo"},
            {"category": "Sensors"},
            {"status": "Delivered"},
            {"month": "Q2-2025"},
            {"warehouse": "London", "category": "Actuators"},
        ],
    )
    def test_filters_match_orders_endpoint(self, client, params):
        data = client.get("/api/reports/quarterly", params=params).json()
        assert sum(q["total_orders"] for q in data) == len(_orders(client, **params))

    def test_month_filter_limits_to_one_quarter(self, client):
        data = client.get("/api/reports/quarterly", params={"month": "2025-02"}).json()
        assert [q["quarter"] for q in data] == ["Q1-2025"]

    def test_all_is_treated_as_no_filter(self, client):
        assert client.get("/api/reports/quarterly", params={"warehouse": "all"}).json() == client.get(
            "/api/reports/quarterly"
        ).json()

    def test_unknown_warehouse_returns_empty(self, client):
        assert client.get("/api/reports/quarterly", params={"warehouse": "Atlantis"}).json() == []


class TestMonthlyTrends:
    def test_unfiltered_sorted_by_month(self, client):
        data = client.get("/api/reports/monthly-trends").json()
        months = [m["month"] for m in data]
        assert months == sorted(months)
        assert sum(m["order_count"] for m in data) == len(_orders(client))

    @pytest.mark.parametrize("params", [{"warehouse": "San Francisco"}, {"status": "Shipped"}, {"category": "Controllers"}])
    def test_filters_match_orders_endpoint(self, client, params):
        data = client.get("/api/reports/monthly-trends", params=params).json()
        assert sum(m["order_count"] for m in data) == len(_orders(client, **params))

    def test_single_month_filter(self, client):
        data = client.get("/api/reports/monthly-trends", params={"month": "2025-01"}).json()
        assert [m["month"] for m in data] == ["2025-01"]

    def test_revenue_is_rounded_to_cents(self, client):
        for m in client.get("/api/reports/monthly-trends").json():
            assert round(m["revenue"], 2) == m["revenue"]
