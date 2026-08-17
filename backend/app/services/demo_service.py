from typing import List, Dict

class DemoService:
    def get_datasets(self) -> List[Dict[str, str]]:
        return [
            {"id": "small", "name": "Demo Small"},
            {"id": "medium", "name": "Demo Medium"},
            {"id": "large", "name": "Demo Large"}
        ]

demo_service = DemoService()
