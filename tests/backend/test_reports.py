"""
Tests for reports API endpoints.
"""
import pytest


class TestReportsEndpoints:
    """Test suite for reports-related endpoints."""

    def test_get_quarterly_reports(self, client):
        """Test getting quarterly reports without filters."""
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first_quarter = data[0]
        assert "quarter" in first_quarter
        assert "total_orders" in first_quarter
        assert "total_revenue" in first_quarter
        assert "avg_order_value" in first_quarter
        assert "fulfillment_rate" in first_quarter

    def test_get_monthly_trends(self, client):
        """Test getting monthly trends without filters."""
        response = client.get("/api/reports/monthly-trends")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        first_month = data[0]
        assert "month" in first_month
        assert "order_count" in first_month
        assert "revenue" in first_month
        assert "delivered_count" in first_month

    def test_quarterly_fulfillment_rate_always_present(self, client):
        """Test that every quarter carries a fulfillment_rate the UI can render."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            assert isinstance(quarter["fulfillment_rate"], (int, float))
            assert 0 <= quarter["fulfillment_rate"] <= 100

    def test_quarterly_sorted_by_quarter(self, client):
        """Test that quarterly results come back in chronological order."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        quarters = [q["quarter"] for q in data]
        assert quarters == sorted(quarters)

    def test_monthly_trends_sorted_by_month(self, client):
        """Test that monthly results come back in chronological order."""
        response = client.get("/api/reports/monthly-trends")
        data = response.json()

        months = [m["month"] for m in data]
        assert months == sorted(months)

    # --- Filter tests: quarterly ---

    def test_quarterly_by_warehouse(self, client):
        """Test filtering quarterly reports by warehouse."""
        response = client.get("/api/reports/quarterly?warehouse=Tokyo")
        assert response.status_code == 200

        data = response.json()
        orders = client.get("/api/orders?warehouse=Tokyo").json()

        expected_orders = len(orders)
        actual_orders = sum(q["total_orders"] for q in data)
        assert actual_orders == expected_orders

    def test_quarterly_by_category(self, client):
        """Test filtering quarterly reports by category."""
        response = client.get("/api/reports/quarterly?category=Sensors")
        assert response.status_code == 200

        data = response.json()
        orders = client.get("/api/orders?category=Sensors").json()

        assert sum(q["total_orders"] for q in data) == len(orders)

    def test_quarterly_by_status(self, client):
        """Test filtering quarterly reports by status."""
        response = client.get("/api/reports/quarterly?status=Delivered")
        assert response.status_code == 200

        data = response.json()

        # Every counted order is Delivered, so fulfillment is necessarily 100%
        for quarter in data:
            assert quarter["fulfillment_rate"] == 100.0

    def test_quarterly_by_month(self, client):
        """Test filtering quarterly reports by a single month."""
        response = client.get("/api/reports/quarterly?month=2025-01")
        assert response.status_code == 200

        data = response.json()

        # January only falls in Q1, so at most that one quarter comes back
        assert len(data) <= 1
        for quarter in data:
            assert quarter["quarter"] == "Q1-2025"

    def test_quarterly_by_quarter_period(self, client):
        """Test filtering quarterly reports by a quarter period."""
        response = client.get("/api/reports/quarterly?month=Q2-2025")
        assert response.status_code == 200

        data = response.json()
        for quarter in data:
            assert quarter["quarter"] == "Q2-2025"

    def test_quarterly_multiple_filters(self, client):
        """Test filtering quarterly reports with multiple filters."""
        response = client.get(
            "/api/reports/quarterly?warehouse=London&category=Connectors&status=Delivered"
        )
        assert response.status_code == 200

        data = response.json()
        orders = client.get(
            "/api/orders?warehouse=London&category=Connectors&status=Delivered"
        ).json()

        assert sum(q["total_orders"] for q in data) == len(orders)

    # --- Filter tests: monthly trends ---

    def test_monthly_trends_by_warehouse(self, client):
        """Test filtering monthly trends by warehouse."""
        response = client.get("/api/reports/monthly-trends?warehouse=San Francisco")
        assert response.status_code == 200

        data = response.json()
        orders = client.get("/api/orders?warehouse=San Francisco").json()

        assert sum(m["order_count"] for m in data) == len(orders)

    def test_monthly_trends_by_category(self, client):
        """Test filtering monthly trends by category."""
        response = client.get("/api/reports/monthly-trends?category=Circuit Boards")
        assert response.status_code == 200

        data = response.json()
        orders = client.get("/api/orders?category=Circuit Boards").json()

        assert sum(m["order_count"] for m in data) == len(orders)

    def test_monthly_trends_by_status(self, client):
        """Test filtering monthly trends by status."""
        response = client.get("/api/reports/monthly-trends?status=Delivered")
        assert response.status_code == 200

        data = response.json()

        # Filtering to Delivered means every counted order is also delivered
        for month in data:
            assert month["delivered_count"] == month["order_count"]

    def test_monthly_trends_by_month(self, client):
        """Test filtering monthly trends by a single month."""
        response = client.get("/api/reports/monthly-trends?month=2025-03")
        assert response.status_code == 200

        data = response.json()
        assert len(data) <= 1
        for month in data:
            assert month["month"] == "2025-03"

    def test_monthly_trends_multiple_filters(self, client):
        """Test filtering monthly trends with multiple filters."""
        response = client.get(
            "/api/reports/monthly-trends?warehouse=Tokyo&category=Sensors"
        )
        assert response.status_code == 200

        data = response.json()
        orders = client.get("/api/orders?warehouse=Tokyo&category=Sensors").json()

        assert sum(m["order_count"] for m in data) == len(orders)

    # --- Consistency and edge cases ---

    def test_reports_revenue_matches_filtered_orders(self, client):
        """Test that reported revenue matches the filtered raw orders."""
        params = "warehouse=Tokyo&category=Sensors"

        orders = client.get(f"/api/orders?{params}").json()
        expected_revenue = sum(o["total_value"] for o in orders)

        monthly = client.get(f"/api/reports/monthly-trends?{params}").json()
        actual_revenue = sum(m["revenue"] for m in monthly)

        assert abs(actual_revenue - expected_revenue) < 0.01

    def test_quarterly_and_monthly_agree_under_same_filter(self, client):
        """Test that both report endpoints count the same orders for one filter."""
        params = "warehouse=London"

        quarterly = client.get(f"/api/reports/quarterly?{params}").json()
        monthly = client.get(f"/api/reports/monthly-trends?{params}").json()

        assert sum(q["total_orders"] for q in quarterly) == sum(
            m["order_count"] for m in monthly
        )

    def test_reports_filter_all_matches_unfiltered(self, client):
        """Test that the sentinel value 'all' behaves like no filter."""
        unfiltered = client.get("/api/reports/quarterly").json()
        all_filtered = client.get(
            "/api/reports/quarterly?warehouse=all&category=all&status=all&month=all"
        ).json()

        assert unfiltered == all_filtered

    def test_reports_nonexistent_filter_returns_empty(self, client):
        """Test that a filter matching nothing yields empty reports, not an error."""
        quarterly = client.get("/api/reports/quarterly?warehouse=Atlantis")
        monthly = client.get("/api/reports/monthly-trends?warehouse=Atlantis")

        assert quarterly.status_code == 200
        assert monthly.status_code == 200
        assert quarterly.json() == []
        assert monthly.json() == []

    def test_reports_avg_order_value_calculation(self, client):
        """Test that avg_order_value is revenue divided by order count."""
        response = client.get("/api/reports/quarterly")
        data = response.json()

        for quarter in data:
            if quarter["total_orders"] > 0:
                expected = quarter["total_revenue"] / quarter["total_orders"]
                assert abs(quarter["avg_order_value"] - expected) < 0.01
