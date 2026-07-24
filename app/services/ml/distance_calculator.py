from typing import Dict, List

AISLE_DISTANCE = 10
POSITION_DISTANCE = 5


class DistanceCalculator:

    @staticmethod
    def manhattan(pos1: Dict, pos2: Dict) -> float:
        aisle_diff = abs(pos1["aisle"] - pos2["aisle"])
        p1 = ord(pos1["position"].upper()) - ord("A") if isinstance(pos1["position"], str) else pos1["position"]
        p2 = ord(pos2["position"].upper()) - ord("A") if isinstance(pos2["position"], str) else pos2["position"]
        pos_diff = abs(p1 - p2)
        return aisle_diff * AISLE_DISTANCE + pos_diff * POSITION_DISTANCE

    @staticmethod
    def route_distance(route_positions: List[Dict]) -> float:
        total = 0.0
        for i in range(len(route_positions) - 1):
            total += DistanceCalculator.manhattan(route_positions[i], route_positions[i + 1])
        return total

    @staticmethod
    def route_breakdown(route_labels: List[str], route_positions: List[Dict]) -> List[Dict]:
        segments = []
        for i in range(len(route_positions) - 1):
            dist = DistanceCalculator.manhattan(route_positions[i], route_positions[i + 1])
            segments.append({
                "from": route_labels[i],
                "to": route_labels[i + 1],
                "distance": dist,
            })
        return segments
