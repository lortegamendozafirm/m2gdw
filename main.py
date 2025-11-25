from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api.v1 import routes
from app.core import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------
# Nuevo estilo: lifespan context manager
# --------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja startup y shutdown con el nuevo patrón de FastAPI"""
    # Startup logic
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Modo DEBUG: {settings.DEBUG}")

    yield  # 👈 Aquí se ejecuta la app

    # Shutdown logic
    logger.info(f"🛑 Cerrando {settings.APP_NAME}")

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Microservicio para escribir contenido Markdown en Google Docs usando una cuenta de servicio",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # 👈 Aquí se usa el nuevo manejador
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de la API v1
app.include_router(
    routes.router,
    prefix="/api/v1",
    tags=["documents"]
)

# Endpoint raíz
@app.get("/", tags=["root"])
async def root():
    """Endpoint raíz"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# Entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
