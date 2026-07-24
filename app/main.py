from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.routes import api_router
from app.utils.exceptions import (
    DatasetNotFoundError,
    InvalidTransactionDataError,
    FileProcessingError,
    MLServiceError,
    map_ml_error_to_http_status,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="SIGAP Backend - Warehouse Slotting & Picking Recommendation via ML Service",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)


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