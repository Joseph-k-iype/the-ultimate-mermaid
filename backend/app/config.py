from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CLONE_DIR: str = "/tmp/patternviz"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Enterprise proxy (optional)
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    NO_PROXY: str = "localhost,127.0.0.1"
    USE_SYSTEM_SSL: bool = True

    # FalkorDB knowledge graph (optional)
    FALKORDB_HOST: str = "localhost"
    FALKORDB_PORT: int = 6379
    FALKORDB_GRAPH: str = "patternviz"
    FALKORDB_ENABLED: bool = True

    model_config = {"env_prefix": "PATTERNVIZ_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
