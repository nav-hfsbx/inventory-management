from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

# Restocking orders are dated against a fixed "today" rather than the real
# clock: every other date in this demo (orders.json, FilterBar's month
# dropdown) lives inside a fictional Sept 2025 present, so datetime.now()
# would create an order dated 2026, break ORD-2025-xxxx numbering, and
# silently open a new bucket in /api/reports/monthly-trends.
SIMULATED_TODAY = datetime(2025, 9, 30, 12, 0, 0)
RESTOCKING_LEAD_TIME_DAYS = 10


def compute_lead_time_days(order: dict) -> int:
    """Derive delivery lead time from the same two dates every Order already has."""
    order_date = datetime.fromisoformat(order["order_date"])
    expected_delivery = datetime.fromisoformat(order["expected_delivery"])
    return (expected_delivery - order_date).days

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    if month.startswith('Q'):
        # Handle quarters
        if month in QUARTER_MAP:
            months = QUARTER_MAP[month]
            return [item for item in items if any(m in item.get('order_date', '') for m in months)]
    else:
        # Direct month match
        return [item for item in items if month in item.get('order_date', '')]

    return items

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None
    order_type: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: float
    warehouse: str
    category: str

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

class RestockingRecommendationItem(BaseModel):
    item_sku: str
    item_name: str
    warehouse: str
    category: str
    current_demand: int
    forecasted_demand: int
    recommended_quantity: int  # full forecast gap (need), independent of budget
    quantity: int  # quantity the greedy algorithm actually funded
    unit_cost: float
    line_total: float

class RestockingRecommendationResponse(BaseModel):
    budget: float
    total_estimated_cost: float
    remaining_budget: float
    items: List[RestockingRecommendationItem]

class RestockingOrderLineItem(BaseModel):
    item_sku: str
    quantity: int

class RestockingOrderRequest(BaseModel):
    budget: float
    items: List[RestockingOrderLineItem]

class RestockingOrderOut(Order):
    lead_time_days: int

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    # Restocking orders have their own section (Submitted Orders) on the
    # frontend and their own endpoint below — exclude them here so they
    # aren't shown twice.
    customer_orders = [o for o in orders if o.get("order_type") != "Restocking"]
    filtered_orders = apply_filters(customer_orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

# Restocking endpoints

@app.get("/api/restocking/recommendations", response_model=RestockingRecommendationResponse)
def get_restocking_recommendations(
    budget: Optional[float] = None,
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Greedy-by-urgency restocking recommendations within a budget."""
    if budget is None or budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be a positive number")

    pool = apply_filters(demand_forecasts, warehouse=warehouse, category=category)

    candidates = []
    for forecast in pool:
        gap = max(forecast["forecasted_demand"] - forecast["current_demand"], 0)
        if gap > 0:
            candidates.append({**forecast, "recommended_quantity": gap})

    # Urgency = larger forecast gap first; tie-break by id for deterministic ordering
    candidates.sort(key=lambda c: (-c["recommended_quantity"], int(c["id"])))

    remaining = budget
    items = []
    for candidate in candidates:
        unit_cost = candidate["unit_cost"]
        affordable = int(remaining // unit_cost)
        quantity = min(candidate["recommended_quantity"], affordable)
        if quantity <= 0:
            continue
        line_total = round(quantity * unit_cost, 2)
        remaining -= line_total
        items.append(RestockingRecommendationItem(
            item_sku=candidate["item_sku"],
            item_name=candidate["item_name"],
            warehouse=candidate["warehouse"],
            category=candidate["category"],
            current_demand=candidate["current_demand"],
            forecasted_demand=candidate["forecasted_demand"],
            recommended_quantity=candidate["recommended_quantity"],
            quantity=quantity,
            unit_cost=unit_cost,
            line_total=line_total
        ))

    return RestockingRecommendationResponse(
        budget=budget,
        total_estimated_cost=round(budget - remaining, 2),
        remaining_budget=round(remaining, 2),
        items=items
    )

@app.post("/api/restocking/orders", response_model=RestockingOrderOut)
def create_restocking_order(request: RestockingOrderRequest):
    """Submit a restocking order built from edited recommendation line items."""
    if request.budget <= 0:
        raise HTTPException(status_code=400, detail="Budget must be a positive number")

    valid_items = [item for item in request.items if item.quantity > 0]
    if not valid_items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item with a positive quantity")

    # Defense in depth: the greedy algorithm (not the user) decides which SKUs
    # are eligible and their max quantity, and demand_forecasts is also the
    # only source of truth for name/cost/warehouse/category - re-derive
    # everything server-side from it rather than trusting the client payload.
    # Quantities are summed per SKU first so two line items for the same SKU
    # can't each pass the per-line gap check while their total exceeds it.
    forecast_by_sku = {forecast["item_sku"]: forecast for forecast in demand_forecasts}
    requested_by_sku = {}
    for item in valid_items:
        requested_by_sku[item.item_sku] = requested_by_sku.get(item.item_sku, 0) + item.quantity

    for sku, requested_qty in requested_by_sku.items():
        forecast = forecast_by_sku.get(sku)
        gap = max(forecast["forecasted_demand"] - forecast["current_demand"], 0) if forecast else 0
        if gap <= 0:
            raise HTTPException(status_code=400, detail=f"{sku} is not eligible for restocking")
        if requested_qty > gap:
            raise HTTPException(
                status_code=400,
                detail=f"Quantity for {sku} exceeds the recommended maximum of {gap}"
            )

    order_date = SIMULATED_TODAY
    expected_delivery = order_date + timedelta(days=RESTOCKING_LEAD_TIME_DAYS)

    order_items = [
        {
            "sku": sku,
            "name": forecast_by_sku[sku]["item_name"],
            "quantity": quantity,
            "unit_price": forecast_by_sku[sku]["unit_cost"]
        }
        for sku, quantity in requested_by_sku.items()
    ]
    total_value = round(
        sum(quantity * forecast_by_sku[sku]["unit_cost"] for sku, quantity in requested_by_sku.items()),
        2
    )

    warehouses = {forecast_by_sku[sku]["warehouse"] for sku in requested_by_sku}
    categories = {forecast_by_sku[sku]["category"] for sku in requested_by_sku}

    # len(orders)+1 would collide with real data: orders.json's ids aren't a
    # clean 1..N sequence (e.g. 201-210 appear twice), so derive from the max.
    next_id = max((int(o["id"]) for o in orders), default=0) + 1

    new_order = {
        "id": str(next_id),
        "order_number": f"ORD-2025-{next_id:04d}",
        "customer": "Internal Restocking",
        "items": order_items,
        "status": "Submitted",
        "order_date": order_date.isoformat(),
        "expected_delivery": expected_delivery.isoformat(),
        "total_value": total_value,
        "actual_delivery": None,
        "warehouse": next(iter(warehouses)) if len(warehouses) == 1 else None,
        "category": next(iter(categories)) if len(categories) == 1 else None,
        "order_type": "Restocking"
    }
    orders.append(new_order)

    return RestockingOrderOut(**new_order, lead_time_days=compute_lead_time_days(new_order))

@app.get("/api/restocking/orders", response_model=List[RestockingOrderOut])
def get_restocking_orders():
    """All submitted restocking orders, unfiltered by the global FilterBar."""
    restocking = [o for o in orders if o.get("order_type") == "Restocking"]
    return [RestockingOrderOut(**o, lead_time_days=compute_lead_time_days(o)) for o in restocking]

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders (excluding restocking orders - those are procurement
    # spend, not customer-order revenue/fulfillment)
    customer_orders = [o for o in orders if o.get("order_type") != "Restocking"]
    filtered_orders = apply_filters(customer_orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders. Honours the same global
    # FilterBar params as /api/dashboard/summary so the Reports view stays
    # consistent with every other page.
    customer_orders = [o for o in orders if o.get("order_type") != "Restocking"]
    filtered_orders = apply_filters(customer_orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    quarters = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0,
                'fulfillment_rate': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends"""
    customer_orders = [o for o in orders if o.get("order_type") != "Restocking"]
    filtered_orders = apply_filters(customer_orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    months = {}

    for order in filtered_orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
