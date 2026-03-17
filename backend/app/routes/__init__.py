from app.routes.graph import router as graph_router
from app.routes.pattern import router as pattern_router
from app.routes.scan import router as scan_router
from app.routes.template import router as template_router

__all__ = ["scan_router", "template_router", "pattern_router", "graph_router"]
