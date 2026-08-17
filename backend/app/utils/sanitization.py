import re
from typing import Any, Dict, List

def sanitize_string(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[<>]", "", value)
    return value[:500]


def sanitize_transaction_row(row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, val in row.items():
        clean_key = sanitize_string(str(key))
        if isinstance(val, str):
            cleaned[clean_key] = sanitize_string(val)
        else:
            cleaned[clean_key] = val
    return cleaned


def sanitize_transactions(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [sanitize_transaction_row(row) for row in data if isinstance(row, dict)]