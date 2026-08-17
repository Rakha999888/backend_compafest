from typing import List, Dict, Any

REQUIRED_COLUMNS = {"order_id", "product"}
OPTIONAL_COLUMNS = {"category", "quantity", "location", "timestamp"}
MAX_ROWS = 100_000
MAX_UNIQUE_PRODUCTS = 5_000

class ValidationService:
    
    @staticmethod
    def validate_transactions(data: List[Dict[str, Any]]) -> List[str]:
        errors = []

        if not isinstance(data, list):
            return ["Data must be a list of transactions"]

        if len(data) == 0:
            errors.append("Transaction data is empty")
            return errors

        if len(data) > MAX_ROWS:
            errors.append(f"Too many rows: {len(data)} exceeds maximum {MAX_ROWS}")

        for i, row in enumerate(data):
            if not isinstance(row, dict):
                errors.append(f"Row {i} is not a valid object")
                continue
            if not row.get("order_id"):
                errors.append(f"Row {i}: missing 'order_id'")
            if not row.get("product"):
                errors.append(f"Row {i}: missing 'product'")

        unique_products = set()
        for row in data:
            if isinstance(row, dict) and row.get("product"):
                unique_products.add(row["product"])

        if len(unique_products) > MAX_UNIQUE_PRODUCTS:
            errors.append(f"Too many unique products: {len(unique_products)} exceeds maximum {MAX_UNIQUE_PRODUCTS}")

        return errors
    
    @staticmethod
    def validate_csv_columns(columns: List[str]) ->List[str]:
        errors = []
        col_set = set(c.strip().lower() for c in columns)
        for required in REQUIRED_COLUMNS:
            if required not in col_set:
                errors.append(f"Missing required column: '{required}'")
        return errors