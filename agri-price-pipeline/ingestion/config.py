import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent


def find_env_file():
    for base in (PROJECT_ROOT, WORKSPACE_ROOT, Path.cwd()):
        candidate = base / ".env"
        if candidate.exists():
            return candidate
    return PROJECT_ROOT / ".env"


def load_env_file():
    env_file = find_env_file()
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_env(name, default=None):
    value = os.getenv(name)
    if value is not None:
        return value

    load_env_file()
    value = os.getenv(name, default)
    return value


def get_api_key():
    api_key = get_env("DATAGOVINDIA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing DATAGOVINDIA_API_KEY. Create a .env file in the project root or workspace root and set DATAGOVINDIA_API_KEY=..."
        )
    return api_key
