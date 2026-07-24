import httpx
import logging
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.schemas.ml import (
    MLResponse,
    MLInferenceRequest,
    MLFullPipelineRequest,
    MLErrorResponse,
)



logger = logging.getLogger(__name__)


class MLClientError(Exception):
    def __init__(self, error_code: str, message: str, details: Optional[Dict] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{error_code}] {message}")




class MLClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = (base_url or settings.ML_SERVICE_URL).rstrip("/")
        self.timeout = timeout or settings.ML_SERVICE_TIMEOUT

    async def infer(self, request: MLInferenceRequest) -> MLResponse:
        payload = request.model_dump(exclude_none=True)
        return await self._post("/infer", payload)

    async def full_pipeline(self, request: MLFullPipelineRequest) -> MLResponse:
        payload = request.model_dump(exclude_none=True)
        return await self._post("/full-pipeline", payload)

    async def _post(self, path: str, payload: Dict[str, Any]) -> MLResponse:
        url = f"{self.base_url}{path}"
        logger.info("ML request: %s %s", url, payload.get("mode", "unknown"))

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except httpx.ConnectError as exc:
            logger.error("ML service unreachable: %s", exc)
            raise MLClientError(
                error_code="ML_SERVICE_UNAVAILABLE",
                message="ML service is unreachable",
                details={"url": url, "reason": str(exc)},
            )
        except httpx.TimeoutException as exc:
            logger.error("ML service timeout: %s", exc)
            raise MLClientError(
                error_code="ML_SERVICE_TIMEOUT",
                message="ML service timed out",
                details={"url": url, "timeout": self.timeout},
            )

        if response.status_code >= 400:
            self._handle_error_response(response)

        data = response.json()
        return MLResponse(**data)

    def _handle_error_response(self, response: httpx.Response) -> None:
        try:
            error_data = response.json()
            error_resp = MLErrorResponse(**error_data)
            logger.warning(
                "ML error: %s - %s", error_resp.error, error_resp.message
            )
            raise MLClientError(
                error_code=error_resp.error,
                message=error_resp.message,
                details=error_resp.details,
            )
        except (ValueError, KeyError):
            raise MLClientError(
                error_code="ML_UNKNOWN_ERROR",
                message=f"ML service returned status {response.status_code}",
                details={"body": response.text[:500]},
            )



_ml_client: Optional[MLClient] = None





def get_ml_client() -> MLClient:
    global _ml_client
    if _ml_client is None:
        _ml_client = MLClient()
    return _ml_client