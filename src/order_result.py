from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class OrderResult:
    order_id: int
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime
    order_type: str
