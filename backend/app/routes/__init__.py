from fastapi import APIRouter
from app.routes import ml

api_router = APIRouter()

# Put other resource routes here

api_router.include_router(ml.router, prefix="/ml")
