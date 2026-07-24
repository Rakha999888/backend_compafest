from dataclasses import dataclass
from typing import List, Dict

@dataclass
class WarehouseSlot:
    aisle: int
    position: str
    label: str

class WarehouseLayout:
    def __init__(self, num_aisles: int = 6, positions_per_aisle: int = 8):
        self.num_aisles = num_aisles
        self.positions_per_aisle = positions_per_aisle
        self.slots = self._generate_slots()
        
    def _generate_slots(self) -> List[WarehouseSlot]:
        slots = []
        for aisle in range(1, self.num_aisles + 1):
            for pos_idx in range(self.positions_per_aisle):
                position_letter = chr(ord("A") + pos_idx)
                slots.append(WarehouseSlot(
                    aisle=aisle,
                    position=position_letter,
                    label=f"Aisle {aisle}, Shelf {position_letter}",
                ))
        return slots
    
    def get_slot(self, index: int) -> WarehouseSlot:
        return self.slots[index % len(self.slots)]

    def get_slot_dict(self, index: int) -> Dict:
        s = self.get_slot(index)
        return {"aisle": s.aisle, "position": s.position, "label": s.label}

    def total_slots(self) -> int:
        return len(self.slots)

    def to_dict_list(self) -> List[Dict]:
        return [
            {"aisle": s.aisle, "position": s.position, "label": s.label}
            for s in self.slots
        ]
        
    @classmethod
    def from_product_count(cls, num_products: int) -> "WarehouseLayout":
        if num_products <= 20:
            return cls(num_aisles=4, positions_per_aisle=6)
        elif num_products <= 50:
            return cls(num_aisles=6, positions_per_aisle=8)
        else:
            return cls(num_aisles=10, positions_per_aisle=10)