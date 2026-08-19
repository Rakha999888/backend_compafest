import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.core.ml_state import MLState
from app.routes import api_router
from app.services.ml_service import MLService
from app.utils.exceptions import (
    DatasetNotFoundError,
    InvalidTransactionDataError,
    FileProcessingError,
    MLServiceError,
    map_ml_error_to_http_status,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s:     %(name)s - %(message)s",
    force=True,
)
logger = logging.getLogger("ml.startup")


async def _train_in_background(app: FastAPI):
    """Training di background thread supaya event loop tidak terblokir."""
    app.state.ml_state.is_training = True
    try:
        await asyncio.to_thread(MLService().train, app.state.ml_state)
        logger.info(
            "training selesai: %d kategori, %d aturan",
            app.state.ml_state.train_meta.get("n_categories", 0),
            app.state.ml_state.train_meta.get("n_rules", 0),
        )
    except Exception as exc:
        logger.error("training gagal: %s", exc)
        app.state.ml_state.training_error = str(exc)
    finally:
        app.state.ml_state.is_training = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ml_state = MLState()
    logger.info("training dimulai di background...")
    task = asyncio.create_task(_train_in_background(app))
    yield
    # shutdown: pastikan training task selesai
    if not task.done():
        task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="SIGAP Backend - Warehouse Slotting & Picking Recommendation via ML Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

_app_instance = app


@app.exception_handler(DatasetNotFoundError)
async def dataset_not_found_handler(request: Request, exc: DatasetNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"success": False, "message": "Dataset not found"},
    )


@app.exception_handler(InvalidTransactionDataError)
async def invalid_transaction_handler(request: Request, exc: InvalidTransactionDataError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Invalid transaction data",
            "errors": exc.errors,
        },
    )


@app.exception_handler(FileProcessingError)
async def file_processing_handler(request: Request, exc: FileProcessingError):
    return JSONResponse(
        status_code=400,
        content={"success": False, "message": exc.message},
    )


@app.exception_handler(MLServiceError)
async def ml_service_error_handler(request: Request, exc: MLServiceError):
    status_code = map_ml_error_to_http_status(exc.error_code)
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "errors": exc.errors(),
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

app.include_router(api_router, prefix="/api")

from app.routes.health import router as health_router
app.include_router(health_router)

from app.routes.demo import router as demo_router
app.include_router(demo_router)

from app.routes.recommend import router as recommend_router
app.include_router(recommend_router)

from app.routes.upload import router as upload_router
app.include_router(upload_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "status": "running",
    }