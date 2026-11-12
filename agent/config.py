"""Settings from environment variables. The API key is never printed."""

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class Settings:
    api_key: str
    model: str

    def __repr__(self) -> str:  # keep the key out of tracebacks and logs
        return f"Settings(model={self.model!r}, api_key=***)"


def load_dotenv(path: Path) -> None:
    """Minimal .env reader for local runs. Real environment variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip())


def load_settings() -> Settings:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("CODEMENTOR_MODEL", "").strip()
    missing = [name for name, value in [("OPENROUTER_API_KEY", api_key), ("CODEMENTOR_MODEL", model)] if not value]
    if missing:
        raise ConfigError(f"missing environment variables: {', '.join(missing)}")
    return Settings(api_key=api_key, model=model)
