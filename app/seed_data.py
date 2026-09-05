"""
Synthetic, clearly-labeled demo data. Swap for real merchant data (products,
customers, events) once connected to an actual Razorpay merchant account.
"""

CATALOG = [
    {"id": "p1", "name": "Aeon 15 Gaming Laptop", "category": "laptop", "price": 65999, "tags": ["coding", "gaming", "performance"]},
    {"id": "p2", "name": "Vertex Pro Ultrabook", "category": "laptop", "price": 71499, "tags": ["coding", "office", "portable"]},
    {"id": "p3", "name": "Katana Wireless Gaming Mouse", "category": "mouse", "price": 1299, "tags": ["gaming", "performance"]},
    {"id": "p4", "name": "Origin Mechanical Keyboard", "category": "keyboard", "price": 2499, "tags": ["gaming", "coding"]},
    {"id": "p5", "name": "Halo ANC Headphones", "category": "headphones", "price": 3999, "tags": ["gaming", "coding", "office"]},
    {"id": "p6", "name": "Lumen 27\" QHD Monitor", "category": "monitor", "price": 18999, "tags": ["coding", "office", "gaming"]},
    {"id": "p7", "name": "Pixel Shot 64MP Phone", "category": "phone", "price": 34999, "tags": ["photography"]},
    {"id": "p8", "name": "ClearFrame Camera Lens Kit", "category": "accessory", "price": 5499, "tags": ["photography"]},
    {"id": "p9", "name": "GlideMat XL Desk Pad", "category": "accessory", "price": 899, "tags": ["gaming", "office"]},
    {"id": "p10", "name": "Nimbus Backpack 25L", "category": "accessory", "price": 2199, "tags": ["office", "coding", "portable"]},
    {"id": "p11", "name": "Forge Power Bank 20K", "category": "accessory", "price": 1799, "tags": ["portable", "photography"]},
    {"id": "p12", "name": "Meridian 4K Webcam", "category": "accessory", "price": 4299, "tags": ["office", "coding"]},
]

FUNNEL = {"view": 4821, "cart": 1124, "checkout": 721, "payment": 482}

CUSTOMERS = [
    {"id": "c1", "name": "Ananya R.", "ltv": 48200, "last_order_days_ago": 52, "score": 91, "orders": 14},
    {"id": "c2", "name": "Rohit K.", "ltv": 31500, "last_order_days_ago": 8, "score": 88, "orders": 9},
    {"id": "c3", "name": "Farah S.", "ltv": 56900, "last_order_days_ago": 61, "score": 79, "orders": 17},
    {"id": "c4", "name": "Devansh M.", "ltv": 12300, "last_order_days_ago": 5, "score": 64, "orders": 3},
    {"id": "c5", "name": "Priya N.", "ltv": 39750, "last_order_days_ago": 47, "score": 83, "orders": 11},
    {"id": "c6", "name": "Karan V.", "ltv": 9800, "last_order_days_ago": 70, "score": 41, "orders": 2},
]

DEFAULT_GUARDRAILS = {
    "max_discount_pct": 10,
    "min_margin_pct": 15,
    "max_offer_amount": 2000,
    "max_daily_offers": 500,
    "auto_execute_payments": False,
    "auto_launch_campaigns": False,
    "high_value_requires_approval": True,
    "high_value_threshold": 40000,
}
