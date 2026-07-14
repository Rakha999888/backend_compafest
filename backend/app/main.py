from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.routes import api_router
from app.utils.exceptions import DatasetNotFoundError

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Scalable FastAPI Backend Template",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Global handler for dataset not found (returns 404)
@app.exception_handler(DatasetNotFoundError)
async def dataset_not_found_handler(request: Request, exc: DatasetNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "Dataset not found"
        }
    )

# Global handler for validation errors (returns 422 for empty or invalid requests)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "errors": exc.errors()
        }
    )

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, configure specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core api router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include health router (adds GET /health endpoint)
from app.routes.health import router as health_router
app.include_router(health_router)

# Include demo router (adds GET /demo/list endpoint)
from app.routes.demo import router as demo_router
app.include_router(demo_router)

# Include recommendation router (adds POST /recommend endpoint)
from app.routes.recommend import router as recommend_router
app.include_router(recommend_router)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "status": "running"
    }
