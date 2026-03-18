import logging
import os
import platform
import shutil
import ssl
import subprocess
import tempfile
from pathlib import Path

import certifi
from git import Repo

from app.analyzers.registry import default_registry
from app.config import settings

logger = logging.getLogger(__name__)


def _export_windows_certs() -> str | None:
    """Export certificates from the Windows certificate store to a temp PEM file.

    Uses PowerShell to extract all trusted root CA certificates and writes
    them to a temporary PEM file that Git and Python can consume.
    Returns the path to the PEM file, or None on failure.
    """
    try:
        ps_script = (
            "Get-ChildItem -Path Cert:\\LocalMachine\\Root | "
            "ForEach-Object { "
            "'-----BEGIN CERTIFICATE-----'; "
            "[Convert]::ToBase64String($_.RawData, 'InsertLineBreaks'); "
            "'-----END CERTIFICATE-----' "
            "}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        # Write to a temp file that persists for the process lifetime
        pem_path = os.path.join(tempfile.gettempdir(), "patternviz_cacerts.pem")
        with open(pem_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)

        logger.info("Exported %d bytes from Windows cert store to %s",
                     len(result.stdout), pem_path)
        return pem_path
    except Exception as exc:
        logger.debug("Windows cert export failed: %s", exc)
        return None


def _find_ca_bundle() -> str | None:
    """Find the best CA bundle for the current platform.

    Priority order:
    1. User-specified SSL_CA_FILE in settings
    2. System certificate paths (platform-aware)
    3. Python ssl module's default verify paths
    4. Windows certificate store export
    5. Python certifi bundle (last resort)
    """
    # 1. Explicit user override
    if settings.SSL_CA_FILE:
        ca = settings.SSL_CA_FILE
        if os.path.isfile(ca):
            logger.info("Using user-specified CA file: %s", ca)
            return ca
        logger.warning("SSL_CA_FILE not found: %s (falling back to auto-detect)", ca)

    # 2. Platform-specific well-known paths
    system = platform.system()

    if system == "Windows":
        windows_paths = [
            # Git for Windows ships its own bundle
            os.path.expandvars(r"%ProgramFiles%\Git\mingw64\etc\ssl\certs\ca-bundle.crt"),
            os.path.expandvars(r"%ProgramFiles%\Git\mingw64\ssl\certs\ca-bundle.crt"),
            os.path.expandvars(r"%LocalAppData%\Programs\Git\mingw64\etc\ssl\certs\ca-bundle.crt"),
            # Scoop-installed Git
            os.path.expandvars(r"%UserProfile%\scoop\apps\git\current\mingw64\etc\ssl\certs\ca-bundle.crt"),
            # Chocolatey-installed Git
            os.path.expandvars(r"%ChocolateyInstall%\lib\git\tools\mingw64\etc\ssl\certs\ca-bundle.crt"),
        ]
        for ca_path in windows_paths:
            if os.path.isfile(ca_path):
                return ca_path

    elif system == "Darwin":
        macos_paths = [
            "/etc/ssl/cert.pem",
            "/usr/local/etc/openssl/cert.pem",       # Homebrew Intel
            "/opt/homebrew/etc/openssl/cert.pem",     # Homebrew Apple Silicon
            "/usr/local/etc/openssl@3/cert.pem",
            "/opt/homebrew/etc/openssl@3/cert.pem",
        ]
        for ca_path in macos_paths:
            if os.path.isfile(ca_path):
                return ca_path

    else:
        # Linux variants
        linux_paths = [
            "/etc/ssl/certs/ca-certificates.crt",     # Debian/Ubuntu
            "/etc/pki/tls/certs/ca-bundle.crt",       # RHEL/CentOS/Fedora
            "/etc/ssl/ca-bundle.pem",                  # openSUSE
            "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem",  # RHEL 7+
            "/etc/ssl/cert.pem",                       # Alpine
        ]
        for ca_path in linux_paths:
            if os.path.isfile(ca_path):
                return ca_path

    # 3. Python ssl module's default paths
    try:
        default_paths = ssl.get_default_verify_paths()
        if default_paths.cafile and os.path.isfile(default_paths.cafile):
            return default_paths.cafile
        if default_paths.openssl_cafile and os.path.isfile(default_paths.openssl_cafile):
            return default_paths.openssl_cafile
    except Exception:
        pass

    # 4. Windows certificate store export
    if system == "Windows":
        exported = _export_windows_certs()
        if exported:
            return exported

    # 5. certifi bundle (always available as a fallback)
    return certifi.where()


def _find_ca_path() -> str | None:
    """Find a CA certificate directory if user specified one or the system has one."""
    if settings.SSL_CA_PATH:
        if os.path.isdir(settings.SSL_CA_PATH):
            return settings.SSL_CA_PATH
        logger.warning("SSL_CA_PATH not found: %s", settings.SSL_CA_PATH)

    # Common certificate directories
    ca_dirs = [
        "/etc/ssl/certs",                           # Debian/Ubuntu
        "/etc/pki/tls/certs",                       # RHEL/CentOS
    ]
    if platform.system() == "Windows":
        git_certs = os.path.expandvars(
            r"%ProgramFiles%\Git\mingw64\etc\ssl\certs"
        )
        ca_dirs.insert(0, git_certs)

    for d in ca_dirs:
        if os.path.isdir(d):
            return d

    return None


def _build_git_env() -> dict[str, str]:
    """Build environment variables for git operations.

    Applies enterprise proxy and SSL settings. Cross-platform:
    works on Windows, macOS, and Linux.
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
        ca_bundle = _find_ca_bundle()
        if ca_bundle:
            env["GIT_SSL_CAINFO"] = ca_bundle
            env["SSL_CERT_FILE"] = ca_bundle
            env["REQUESTS_CA_BUNDLE"] = ca_bundle
            logger.info("Git using SSL CA bundle: %s", ca_bundle)

        ca_path = _find_ca_path()
        if ca_path:
            env["GIT_SSL_CAPATH"] = ca_path
            env["SSL_CERT_DIR"] = ca_path

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

    # Filenames that should always be checked even without a recognized extension
    _EXTRA_FILENAMES = {"Dockerfile", "Jenkinsfile", "docker-compose.yml",
                        "docker-compose.yaml"}

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
