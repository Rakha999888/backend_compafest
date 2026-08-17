from typing import Dict, List, Optional
import json
from pathlib import Path


class OrderRepository:
    
    def __init__(self, data_source: str = "demo"):
        self.data_source = data_source
        self.demo_data_path = Path(__file__).parent.parent / "data"
    
    def get_orders_with_categories(self, order_ids: List[str]) -> List[Dict]:
        
        if self.data_source == "demo":
            return self._get_orders_from_demo(order_ids)
        else:
            return self._get_orders_from_db(order_ids)
    
    def _get_orders_from_demo(self, order_ids: List[str]) -> List[Dict]:
        orders = []
        
        demo_files = ["demo_small.json", "demo_medium.json", "demo_large.json"]
        
        all_transactions = []
        for filename in demo_files:
            file_path = self.demo_data_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    transactions = json.load(f)
                    all_transactions.extend(transactions)
        
        order_data = {}
        for transaction in all_transactions:
            oid = transaction.get("order_id")
            if oid in order_ids:
                if oid not in order_data:
                    order_data[oid] = {
                        "order_id": oid,
                        "categories": set()
                    }
                category = transaction.get("category")
                if category:
                    order_data[oid]["categories"].add(category)
        
        for oid in order_ids:
            if oid in order_data:
                orders.append({
                    "order_id": order_data[oid]["order_id"],
                    "categories": list(order_data[oid]["categories"])
                })
        
        return orders
    
    def _get_orders_from_db(self, order_ids: List[str]) -> List[Dict]:
       
        return []


def get_order_repository() -> OrderRepository:
    return OrderRepository(data_source="demo")