from pydantic import BaseModel

class Transaction(BaseModel):
    order_id: str
    product: str
    category: str
    quantity: int
    location: str
    timestamp: str
