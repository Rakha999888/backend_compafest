from dataclasses import dataclass, field
from typing import List, Optional, Dict
import pandas  as  pd
import io
import csv

@dataclass
class Basket:
    order_id: str
    products: List[str]


@dataclass
class TransactionRecord:
    order_id: str
    product: str
    category: Optional[str]
    quantity: int
    location: Optional[str]
    timestamp: Optional[str]


@dataclass
class PreprocessResult:
    baskets: List[Basket]
    records: List[TransactionRecord]
    unique_products: List[str]
    product_locations: Dict[str, str]
    total_transactions: int
    total_items: int


class DataPreprocessor:
    def preprocess_csv(self, raw_csv: str) -> PreprocessResult:
        reader = csv.DictReader(io.StringIO(raw_csv))
        records = []
        for row in reader:
            records.append(TransactionRecord(
                order_id=row.get("order_id", "").strip(),
                product=row.get("product", "").strip(),
                category=row.get("category", "").strip() or None,
                quantity=int(row.get("quantity", 1)),
                location=row.get("location", "").strip() or None,
                timestamp=row.get("timestamp", "").strip() or None,
            ))
        return self._build_result(records)
    
    def preprocess_json(self, data: List[Dict]) -> PreprocessResult:
        records = []
        for item in data:
            records.append(TransactionRecord(
                order_id=str(item.get("order_id", "")).strip(),
                product=str(item.get("product", "")).strip(),
                category=str(item.get("category", "")).strip() or None,
                quantity=int(item.get("quantity", 1)),
                location=str(item.get("location", "")).strip() or None,
                timestamp=str(item.get("timestamp", "")).strip() or None,
            ))
        return self._build_result(records)

    def preprocess_dataframe(self, df: pd.DataFrame) -> PreprocessResult:
        records = []
        for _, row in df.iterrows():
            records.append(TransactionRecord(
                order_id=str(row.get("order_id", "")).strip(),
                product=str(row.get("product", "")).strip(),
                category=str(row.get("category", "")).strip() or None,
                quantity=int(row.get("quantity", 1)),
                location=str(row.get("location", "")).strip() or None,
                timestamp=str(row.get("timestamp", "")).strip() or None,
            ))
        return self._build_result(records)
    
    def _build_result(self, records: List[TransactionRecord]) -> PreprocessResult:
        records = [r  for r in records if r.order_id and r.product]
        
        order_map: Dict[str, List[str]] = {}
        product_locations: Dict[str, str] = {}
        
        for r in records:
            order_map.setdefault(r.order_id, []).append(r.product)
            if r.location and r.product not in product_locations:
                product_locations[r.product] = r.location
                
        baskets = [Basket(order_id=oid, products=products) for oid, products in order_map.items()]
        
        unique_products = sorted(set(r.product for r in records))
        total_items = sum(r.quantity for r in records)

        return PreprocessResult(
            baskets=baskets,
            records=records,
            unique_products=unique_products,
            product_locations=product_locations,
            total_transactions=len(baskets),
            total_items=total_items,
        )