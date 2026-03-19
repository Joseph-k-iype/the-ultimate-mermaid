import os
import tempfile

from pydantic_settings import BaseSettings


def _default_clone_dir() -> str:
    """Cross-platform default clone directory."""
    return os.path.join(tempfile.gettempdir(), "patternviz")


class Settings(BaseSettings):
    CLONE_DIR: str = _default_clone_dir()
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Enterprise proxy (optional)
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    NO_PROXY: str = "localhost,127.0.0.1"

    # SSL certificate configuration
    USE_SYSTEM_SSL: bool = True
    SSL_CA_FILE: str = ""       # Explicit path to a CA bundle file (PEM)
    SSL_CA_PATH: str = ""       # Explicit path to a directory of CA certs

    # FalkorDB knowledge graph (optional)
    FALKORDB_HOST: str = "localhost"
    FALKORDB_PORT: int = 6379
    FALKORDB_GRAPH: str = "patternviz"
    FALKORDB_ENABLED: bool = True

    # Multi-agent AI analysis (optional)
    ENABLE_AGENTS: bool = False

    model_config = {"env_prefix": "PATTERNVIZ_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
