import abc
from typing import Dict, Any
from app.services.dummy_service import dummy_service

class BaseRecommendationPipeline(abc.ABC):
    @abc.abstractmethod
    def run_pipeline(self, dataset_id: str) -> Dict[str, Any]:
        pass

class DummyRecommendationPipeline(BaseRecommendationPipeline):
    def load_dummy(self, dataset_id: str) -> Dict[str, Any]:
        # Fetch the transaction data from the dummy service
        transactions = dummy_service.get_dataset_data(dataset_id)
        
        # Calculate summary metrics from transactions
        total_items = sum(tx.get("quantity", 0) for tx in transactions)
        unique_orders = len(set(tx.get("order_id") for tx in transactions if tx.get("order_id")))
        warehouse_name = f"Warehouse Alpha ({dataset_id.capitalize()})"
        
        # Simulate slotting changes based on the products found
        slotting_before = []
        slotting_after = []
        seen_products = set()
        
        optimized_locations = [
            "Aisle 1, Shelf A",
            "Aisle 1, Shelf B",
            "Aisle 2, Shelf A",
            "Aisle 2, Shelf B"
        ]
        
        for tx in transactions:
            prod = tx.get("product")
            loc = tx.get("location")
            if prod and loc and prod not in seen_products:
                seen_products.add(prod)
                slotting_before.append({"product": prod, "location": loc})
                opt_loc = optimized_locations[len(slotting_after) % len(optimized_locations)]
                slotting_after.append({"product": prod, "location": opt_loc})
                if len(seen_products) >= 4:
                    break

        # Simulate picking route and distance metrics based on size
        if dataset_id == "small":
            picking_route = ["START", "A1", "A5", "A8", "B1", "EXIT"]
            dist_before = 320.0
            dist_after = 210.0
        elif dataset_id == "medium":
            picking_route = ["START", "A1", "A2", "A5", "A8", "B2", "B5", "C1", "EXIT"]
            dist_before = 1450.0
            dist_after = 920.0
        else:  # large
            picking_route = ["START", "A1", "A2", "A5", "A8", "B2", "B5", "C1", "C4", "D2", "EXIT"]
            dist_before = 3120.0
            dist_after = 1890.0

        dist_saved = dist_before - dist_after
        saving_percentage = round((dist_saved / dist_before) * 100, 2)

        return {
            "summary": {
                "warehouse": warehouse_name,
                "total_orders": unique_orders,
                "total_items": total_items
            },
            "slotting": {
                "before": slotting_before,
                "after": slotting_after
            },
            "picking_route": picking_route,
            "distance": {
                "before": dist_before,
                "after": dist_after,
                "saved": dist_saved,
                "saving_percentage": saving_percentage
            }
        }

    def run_pipeline(self, dataset_id: str) -> Dict[str, Any]:
        # Currently, run_pipeline wraps load_dummy
        return self.load_dummy(dataset_id)
