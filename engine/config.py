"""Runtime settings, read from the environment (and .env if python-dotenv finds one)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass
class Settings:
    llm: str = field(default_factory=lambda: os.getenv("GC_LLM", "openai"))  # openai | anthropic | offline
    model: str = field(default_factory=lambda: os.getenv("GC_MODEL", "claude-opus-5-5"))
    openai_model: str = field(default_factory=lambda: os.getenv("GC_OPENAI_MODEL", "gpt-5.4"))
    effort: str = field(default_factory=lambda: os.getenv("GC_EFFORT", "medium"))
    votes: int = field(default_factory=lambda: int(os.getenv("GC_VOTES", "3")))
    cache: str = field(default_factory=lambda: os.getenv("GC_CACHE", "off"))  # off | on | replay
    cache_dir: Path = field(default_factory=lambda: ROOT / os.getenv("GC_CACHE_DIR", "demo/cache"))
    doc_ttl_min: int = field(default_factory=lambda: int(os.getenv("GC_DOC_TTL_MIN", "60")))
    db_path: Path = field(default_factory=lambda: ROOT / os.getenv("GC_DB_PATH", "gateway_check.sqlite3"))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("GC_MAX_TOKENS", "8000")))

    @property
    def has_api_key(self) -> bool:
        return self.has_key_for(self.llm)

    def has_key_for(self, kind: str) -> bool:
        if kind == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
        if kind == "anthropic":
            return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))
        return True


settings = Settings()
