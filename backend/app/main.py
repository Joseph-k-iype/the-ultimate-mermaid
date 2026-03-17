import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.graph import graph_service
from app.routes import graph_router, pattern_router, scan_router, template_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure clone dir exists
    Path(settings.CLONE_DIR).mkdir(parents=True, exist_ok=True)

    # Connect to FalkorDB if enabled
    if settings.FALKORDB_ENABLED:
        graph_service.connect(
            host=settings.FALKORDB_HOST,
            port=settings.FALKORDB_PORT,
            graph_name=settings.FALKORDB_GRAPH,
        )
        if graph_service.is_available:
            graph_service.initialize_schema()

    yield
    # Shutdown: clean up clone dir
    clone_path = Path(settings.CLONE_DIR)
    if clone_path.exists():
        shutil.rmtree(clone_path, ignore_errors=True)


app = FastAPI(
    title="PatternViz",
    description="Code pattern visualization API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan_router, prefix="/api")
app.include_router(template_router, prefix="/api")
app.include_router(pattern_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
