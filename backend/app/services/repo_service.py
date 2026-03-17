import logging
import os
import shutil
import ssl
import certifi
from pathlib import Path

from git import Repo

from app.analyzers.registry import default_registry
from app.config import settings

logger = logging.getLogger(__name__)


def _build_git_env() -> dict[str, str]:
    """Build environment variables for git operations.

    Applies enterprise proxy and system SSL settings when configured.
    """
    env = dict(os.environ)

    # Proxy configuration
    if settings.HTTPS_PROXY:
        env["HTTPS_PROXY"] = settings.HTTPS_PROXY
        env["https_proxy"] = settings.HTTPS_PROXY
        logger.info("Git using HTTPS proxy: %s", settings.HTTPS_PROXY)
    if settings.HTTP_PROXY:
        env["HTTP_PROXY"] = settings.HTTP_PROXY
        env["http_proxy"] = settings.HTTP_PROXY
    if settings.NO_PROXY:
        env["NO_PROXY"] = settings.NO_PROXY
        env["no_proxy"] = settings.NO_PROXY

    # SSL certificate configuration
    if settings.USE_SYSTEM_SSL:
        # Try system SSL paths, fall back to certifi bundle
        system_ca_paths = [
            "/etc/ssl/certs/ca-certificates.crt",        # Debian/Ubuntu
            "/etc/pki/tls/certs/ca-bundle.crt",          # RHEL/CentOS
            "/etc/ssl/cert.pem",                          # macOS
            "/usr/local/etc/openssl/cert.pem",            # macOS Homebrew
            "/etc/ssl/ca-bundle.pem",                     # openSUSE
        ]

        ca_bundle = None
        for ca_path in system_ca_paths:
            if os.path.isfile(ca_path):
                ca_bundle = ca_path
                break

        if ca_bundle is None:
            # Fall back to certifi bundle (ships with Python)
            ca_bundle = certifi.where()

        env["GIT_SSL_CAINFO"] = ca_bundle
        # Also set for Python's ssl module (used by some git transports)
        env["SSL_CERT_FILE"] = ca_bundle
        env["REQUESTS_CA_BUNDLE"] = ca_bundle
        logger.info("Git using SSL CA bundle: %s", ca_bundle)

    return env


class RepoService:
    """Handles cloning repositories and scanning files."""

    _SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache"}

    def clone_repo(self, url: str, branch: str, clone_dir: str | None = None) -> Path:
        base = Path(clone_dir or settings.CLONE_DIR)
        repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
        dest = base / f"{repo_name}_{branch}"
        if dest.exists():
            shutil.rmtree(dest)

        git_env = _build_git_env()
        Repo.clone_from(url, str(dest), branch=branch, depth=1, env=git_env)
        return dest

    def scan_files(self, repo_path: Path) -> list[tuple[str, str]]:
        results: list[tuple[str, str]] = []
        for file_path in sorted(repo_path.rglob("*")):
            if not file_path.is_file():
                continue
            if any(part in self._SKIP_DIRS for part in file_path.parts):
                continue
            rel_path = str(file_path.relative_to(repo_path))
            if default_registry.get_analyzer(rel_path) is None:
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            results.append((rel_path, content))
        return results

    def cleanup(self, repo_path: Path) -> None:
        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
