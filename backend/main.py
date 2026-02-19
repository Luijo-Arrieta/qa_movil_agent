"""
FastAPI application para QA Mobile Agent Backend.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import tests, devices, results
from backend.api.routes import generate as generate_router
from backend.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events para la aplicación."""
    logger.info("🚀 Iniciando QA Mobile Agent Backend")
    yield
    logger.info("🛑 Cerrando QA Mobile Agent Backend")


# Crear aplicación FastAPI
app = FastAPI(
    title="QA Mobile Agent API",
    description="API para ejecutar y generar tests móviles con IA",
    version="0.1.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(tests.router, prefix="/api/v1/tests", tags=["tests"])
app.include_router(generate_router.router, prefix="/api/v1/tests", tags=["tests"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(results.router, prefix="/api/v1/results", tags=["results"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "QA Mobile Agent API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "qa-mobile-agent-api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
