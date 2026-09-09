"""
Tests for restocking API endpoints (recommendations + order submission).

Note: `orders` is a module-level list shared across the whole test session
(no database, no per-test reset), so any restocking order created by a test
persists for the rest of the run. Never assert an absolute order count —
always capture a "before" count in the same test, act, then assert a
relative delta.
"""
import pytest


class TestRestockingRecommendations:
    """Test suite for the budget-based restocking recommendation endpoint."""

    def test_recommendations_requires_positive_budget(self, client):
        """Test that missing, zero, or negative budgets are rejected."""
        for params in ["", "?budget=0", "?budget=-100"]:
            response = client.get(f"/api/restocking/recommendations{params}")
            assert response.status_code == 400
            assert "detail" in response.json()

    def test_recommendations_budget_5000_returns_single_item(self, client):
        """Test that a $5000 budget only funds the most urgent item (WDG-001)."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 1

        item = data["items"][0]
        assert item["item_sku"] == "WDG-001"
        assert item["quantity"] == 111
        assert abs(data["total_estimated_cost"] - 4995.00) < 0.01
        assert abs(data["remaining_budget"] - 5.00) < 0.01

    def test_recommendations_budget_10000_funds_all_gap_items(self, client):
        """Test that a large budget funds every item with a positive forecast gap."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        assert response.status_code == 200

        data = response.json()
        skus = [item["item_sku"] for item in data["items"]]

        assert len(data["items"]) == 8
        assert "MTR-304" not in skus, "MTR-304 has a negative gap and should never be recommended"
        assert abs(data["total_estimated_cost"] - 8918.48) < 0.01
        assert abs(data["remaining_budget"] - 1081.52) < 0.01

    def test_recommendations_respects_warehouse_filter(self, client):
        """Test filtering recommendations by warehouse."""
        response = client.get("/api/restocking/recommendations?budget=10000&warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["warehouse"] == "Tokyo"

    def test_recommendations_respects_category_filter(self, client):
        """Test filtering recommendations by category."""
        response = client.get("/api/restocking/recommendations?budget=10000&category=circuit boards")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert item["category"].lower() == "circuit boards"

    def test_recommendations_excludes_zero_gap_items(self, client):
        """Test that items with forecasted_demand <= current_demand are never recommended."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()

        for item in data["items"]:
            assert item["forecasted_demand"] > item["current_demand"] or item["quantity"] > 0

    def test_recommendations_sorted_by_urgency_desc(self, client):
        """Test that items are ordered by forecast gap descending (most urgent first)."""
        response = client.get("/api/restocking/recommendations?budget=100000")
        data = response.json()

        gaps = [item["recommended_quantity"] for item in data["items"]]
        assert gaps == sorted(gaps, reverse=True)

    def test_recommendation_line_totals_match_quantity_times_cost(self, client):
        """Test that each line's total is quantity * unit_cost."""
        response = client.get("/api/restocking/recommendations?budget=10000")
        data = response.json()

        for item in data["items"]:
            expected_total = round(item["quantity"] * item["unit_cost"], 2)
            assert abs(item["line_total"] - expected_total) < 0.01


class TestRestockingOrders:
    """Test suite for submitting and listing restocking orders."""

    def test_create_restocking_order_success(self, client):
        """Test successfully placing a restocking order."""
        response = client.post("/api/restocking/orders", json={
            "budget": 5000,
            "items": [
                {
                    "item_sku": "WDG-001",
                    "item_name": "Industrial Widget Type A",
                    "quantity": 111,
                    "unit_cost": 45.00,
                    "warehouse": "San Francisco",
                    "category": "Circuit Boards"
                }
            ]
        })
        assert response.status_code == 200

        order = response.json()
        assert order["order_type"] == "Restocking"
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] == 10
        assert order["total_value"] == pytest.approx(4995.00)
        assert order["order_number"].startswith("ORD-2025-")
        assert order["customer"] == "Internal Restocking"

    def test_created_order_appears_in_restocking_orders_endpoint(self, client):
        """Test that a submitted order shows up in GET /api/restocking/orders."""
        before = client.get("/api/restocking/orders").json()
        before_count = len(before)

        response = client.post("/api/restocking/orders", json={
            "budget": 100,
            "items": [
                {"item_sku": "CTL-330", "item_name": "Logic Controller Board", "quantity": 1, "unit_cost": 14.50}
            ]
        })
        assert response.status_code == 200
        new_order_number = response.json()["order_number"]

        after = client.get("/api/restocking/orders").json()
        assert len(after) == before_count + 1
        assert any(o["order_number"] == new_order_number for o in after)
        for order in after:
            assert "lead_time_days" in order

    def test_created_order_excluded_from_main_orders_endpoint(self, client):
        """Test that a submitted restocking order does NOT appear in GET /api/orders."""
        before = client.get("/api/orders").json()
        before_count = len(before)

        response = client.post("/api/restocking/orders", json={
            "budget": 100,
            "items": [
                {"item_sku": "VLV-506", "item_name": "Pressure Relief Valve", "quantity": 1, "unit_cost": 68.50}
            ]
        })
        assert response.status_code == 200
        new_order_number = response.json()["order_number"]

        after = client.get("/api/orders").json()
        assert len(after) == before_count
        assert not any(o["order_number"] == new_order_number for o in after)

    def test_create_restocking_order_rejects_non_positive_budget(self, client):
        """Test that a zero or negative budget is rejected."""
        response = client.post("/api/restocking/orders", json={
            "budget": 0,
            "items": [
                {"item_sku": "CTL-330", "item_name": "Logic Controller Board", "quantity": 1, "unit_cost": 14.50}
            ]
        })
        assert response.status_code == 400

    def test_create_restocking_order_rejects_empty_items(self, client):
        """Test that an order with no items is rejected."""
        response = client.post("/api/restocking/orders", json={"budget": 100, "items": []})
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_restocking_order_rejects_ineligible_sku(self, client):
        """Test that a SKU with zero forecast gap (MTR-304) is rejected."""
        response = client.post("/api/restocking/orders", json={
            "budget": 1000,
            "items": [
                {"item_sku": "MTR-304", "item_name": "Electric Motor 5HP", "quantity": 1, "unit_cost": 385.00}
            ]
        })
        assert response.status_code == 400
        assert "not eligible" in response.json()["detail"].lower()

    def test_create_restocking_order_rejects_quantity_exceeding_gap(self, client):
        """Test that a quantity above the SKU's forecast gap is rejected."""
        response = client.post("/api/restocking/orders", json={
            "budget": 10000,
            "items": [
                {"item_sku": "CTL-330", "item_name": "Logic Controller Board", "quantity": 999, "unit_cost": 14.50}
            ]
        })
        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"].lower()

    def test_dashboard_total_orders_value_excludes_restocking(self, client):
        """Test that placing a restocking order doesn't change dashboard revenue totals."""
        before = client.get("/api/dashboard/summary").json()

        response = client.post("/api/restocking/orders", json={
            "budget": 5000,
            "items": [
                {"item_sku": "GSK-203", "item_name": "High-Temperature Gasket", "quantity": 50, "unit_cost": 8.75}
            ]
        })
        assert response.status_code == 200

        after = client.get("/api/dashboard/summary").json()
        assert after["total_orders_value"] == before["total_orders_value"]
        assert after["pending_orders"] == before["pending_orders"]

    def test_reports_exclude_restocking_orders(self, client):
        """Test that quarterly/monthly report totals don't change after a restocking order."""
        before_quarterly = client.get("/api/reports/quarterly").json()
        before_monthly = client.get("/api/reports/monthly-trends").json()

        response = client.post("/api/restocking/orders", json={
            "budget": 500,
            "items": [
                {"item_sku": "BRG-102", "item_name": "Steel Bearing Assembly", "quantity": 2, "unit_cost": 22.50}
            ]
        })
        assert response.status_code == 200

        after_quarterly = client.get("/api/reports/quarterly").json()
        after_monthly = client.get("/api/reports/monthly-trends").json()
        assert after_quarterly == before_quarterly
        assert after_monthly == before_monthly
