import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from app.schemas.ml import (
    MLResponse,
    MLInferenceRequest,
    MLFullPipelineRequest,
    Coordinate,
    BatchResponse,
    PickingRoute,
    DistanceComparison,
    MLMetadata,
    MLTimings,
    MLInferenceSummary,
)
from app.services.ml_client import MLClientError

logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ML"
INFERENCE_OUTPUT = ML_DIR / "inference_output.json"
FULL_PIPELINE_OUTPUT = ML_DIR / "full_pipeline_output.json"


class MockMLClient:

    def __init__(self):
        self._slotting_map_cache: Optional[Dict] = None

    async def infer(self, request: MLInferenceRequest) -> MLResponse:
        self._validate_inference_request(request)
        data = self._load_json(INFERENCE_OUTPUT)
        response = self._parse_response(data)
        response = self._remap_order_ids(response, request.orders)
        return response

    async def full_pipeline(self, request: MLFullPipelineRequest) -> MLResponse:
        data = self._load_json(FULL_PIPELINE_OUTPUT)
        response = self._parse_response(data)
        if request.max_orders:
            response = self._limit_batches(response, request.max_orders)
        return response

    def _validate_inference_request(self, request: MLInferenceRequest) -> None:
        if not request.orders:
            raise MLClientError(
                error_code="EMPTY_ORDERS",
                message="Daftar orders kosong",
            )
        known_categories = self._get_known_categories()
        if known_categories:
            unknown = []
            for order in request.orders:
                for cat in order.categories:
                    if cat not in known_categories:
                        unknown.append(cat)
            if unknown:
                raise MLClientError(
                    error_code="UNKNOWN_CATEGORY",
                    message=f"Kategori tidak dikenali oleh model",
                    details={"unknown_categories": list(set(unknown))},
                )

    def _get_known_categories(self) -> set:
        data = self._load_json(FULL_PIPELINE_OUTPUT)
        return set(data.get("slotting_map", {}).keys())

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise MLClientError(
                error_code="ML_SERVICE_UNAVAILABLE",
                message=f"Mock data file not found: {path.name}",
                details={"path": str(path)},
            )
        with open(path, "r") as f:
            return json.load(f)

    def _parse_response(self, data: Dict[str, Any]) -> MLResponse:
        slotting_map = {}
        for category, coord in data.get("slotting_map", {}).items():
            slotting_map[category] = Coordinate(
                aisle=coord["aisle"],
                position=coord["position"],
            )

        batches = []
        for batch_data in data.get("batches", []):
            route_data = batch_data["picking_route"]
            sequence = [
                Coordinate(aisle=s["aisle"], position=s["position"])
                for s in route_data["sequence"]
            ]
            picking_route = PickingRoute(
                sequence=sequence,
                distance=route_data["distance"],
                heuristic=route_data["heuristic"],
            )
            batches.append(BatchResponse(
                batch_id=batch_data["batch_id"],
                order_ids=batch_data["order_ids"],
                picking_route=picking_route,
            ))

        dc = data.get("distance_comparison", {})
        distance_comparison = DistanceComparison(
            distance_random=dc.get("distance_random", 0.0),
            distance_abc=dc.get("distance_abc", 0.0),
            distance_system=dc.get("distance_system", 0.0),
            savings_vs_random_pct=dc.get("savings_vs_random_pct", 0.0),
            savings_vs_abc_pct=dc.get("savings_vs_abc_pct", 0.0),
        )

        metadata = None
        if "metadata" in data:
            md = data["metadata"]
            timings = None
            if "timings" in md:
                timings = MLTimings(**md["timings"])
            metadata = MLMetadata(
                n_orders=md.get("n_orders"),
                n_categories=md.get("n_categories"),
                n_batches=md.get("n_batches"),
                total_distance=md.get("total_distance"),
                timings=timings,
                disclaimer=md.get("disclaimer"),
            )

        summary = None
        if "summary" in data:
            sm = data["summary"]
            summary = MLInferenceSummary(
                n_orders=sm.get("n_orders"),
                n_batches=sm.get("n_batches"),
                total_distance=sm.get("total_distance"),
                best_fitness=sm.get("best_fitness"),
                inference_time_s=sm.get("inference_time_s"),
            )

        return MLResponse(
            slotting_map=slotting_map,
            batches=batches,
            distance_comparison=distance_comparison,
            metadata=metadata,
            summary=summary,
        )

    def _remap_order_ids(
        self, response: MLResponse, orders: list
    ) -> MLResponse:
        request_order_ids = [o.order_id for o in orders]
        all_order_ids_in_mock = []
        for batch in response.batches:
            all_order_ids_in_mock.extend(batch.order_ids)

        id_mapping = {}
        for i, mock_id in enumerate(all_order_ids_in_mock):
            if i < len(request_order_ids):
                id_mapping[mock_id] = request_order_ids[i]
            else:
                id_mapping[mock_id] = mock_id

        new_batches = []
        for batch in response.batches:
            new_order_ids = [
                id_mapping.get(oid, oid) for oid in batch.order_ids
            ]
            new_batches.append(BatchResponse(
                batch_id=batch.batch_id,
                order_ids=new_order_ids,
                picking_route=batch.picking_route,
            ))

        response.batches = new_batches
        return response

    def _limit_batches(self, response: MLResponse, max_orders: int) -> MLResponse:
        filtered = []
        total = 0
        for batch in response.batches:
            if total >= max_orders:
                break
            remaining = max_orders - total
            if len(batch.order_ids) > remaining:
                batch.order_ids = batch.order_ids[:remaining]
            filtered.append(batch)
            total += len(batch.order_ids)
        response.batches = filtered
        return response


_mock_ml_client: Optional[MockMLClient] = None


def get_mock_ml_client() -> MockMLClient:
    global _mock_ml_client
    if _mock_ml_client is None:
        _mock_ml_client = MockMLClient()
    return _mock_ml_client