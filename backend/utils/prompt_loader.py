"""
Healthcare AI Router — Prompt Loader
=====================================
Loads prompt templates from the `backend/prompts/` directory.

Design decisions:
  - Prompts are stored as plain `.txt` files to allow non-developer
    stakeholders to edit them without touching Python code.
  - Files are read lazily and cached in-process after first access.
  - The loader raises a descriptive error at startup if any expected
    prompt file is missing, enabling fail-fast behaviour.

Usage:
    from backend.utils.prompt_loader import PromptLoader
    loader = PromptLoader()
    system_prompt = loader.get("router")
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from threading import Lock

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Canonical list of prompt names the system expects to find.
REQUIRED_PROMPTS: tuple[str, ...] = (
    "router",
    "consultation",
    "reimbursement",
    "followup",
    "faq",
)


class PromptLoader:
    """
    File-based prompt repository with in-memory caching.

    Thread-safe: uses a lock around the cache to handle concurrent
    first-access reads safely under async/threaded servers.
    """

    def __init__(self, prompts_dir: str | None = None) -> None:
        if prompts_dir is None:
            # Default: <repo_root>/backend/prompts/
            base = Path(__file__).parent.parent
            prompts_dir = str(base / "prompts")

        self._prompts_dir = Path(prompts_dir)
        self._cache: dict[str, str] = {}
        self._lock: Lock = Lock()

        self._validate_prompts_dir()

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def get(self, name: str) -> str:
        """
        Return the content of the prompt file named `name`.

        Args:
            name: Prompt name without extension, e.g. ``"router"``.

        Returns:
            The prompt text as a stripped string.

        Raises:
            FileNotFoundError: If the prompt file does not exist.
            IOError: If the file cannot be read.
        """
        with self._lock:
            if name not in self._cache:
                self._cache[name] = self._load(name)
        return self._cache[name]

    def reload(self, name: str) -> str:
        """
        Force-reload a prompt from disk (bypasses cache).

        Useful in development to pick up prompt edits without restarting.
        """
        with self._lock:
            content = self._load(name)
            self._cache[name] = content
        logger.info("Prompt reloaded from disk", extra={"prompt": name})
        return content

    def reload_all(self) -> None:
        """Reload every cached prompt from disk."""
        with self._lock:
            for name in list(self._cache.keys()):
                self._cache[name] = self._load(name)
        logger.info("All prompts reloaded from disk")

    def list_available(self) -> list[str]:
        """Return the names of all `.txt` files in the prompts directory."""
        return [
            p.stem
            for p in self._prompts_dir.glob("*.txt")
            if p.is_file()
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _load(self, name: str) -> str:
        path = self._prompts_dir / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: '{path}'. "
                f"Available prompts: {self.list_available()}"
            )
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(
                f"Prompt file '{path}' is empty. "
                "Every prompt must contain at least one non-whitespace character."
            )
        logger.debug("Prompt loaded from disk", extra={"prompt": name, "chars": len(content)})
        return content

    def _validate_prompts_dir(self) -> None:
        """Ensure the prompts directory exists and all required files are present."""
        if not self._prompts_dir.is_dir():
            raise NotADirectoryError(
                f"Prompts directory does not exist: '{self._prompts_dir}'. "
                "Create the directory and add the required .txt prompt files."
            )
        missing = [
            name
            for name in REQUIRED_PROMPTS
            if not (self._prompts_dir / f"{name}.txt").exists()
        ]
        if missing:
            raise FileNotFoundError(
                f"Missing required prompt files: {missing}. "
                f"Expected them in: '{self._prompts_dir}'"
            )
        logger.info(
            "Prompt repository validated",
            extra={
                "prompts_dir": str(self._prompts_dir),
                "available": self.list_available(),
            },
        )


@lru_cache(maxsize=1)
def get_prompt_loader() -> PromptLoader:
    """
    Return the cached application-wide PromptLoader singleton.

    FastAPI dependency injection example:
        def endpoint(loader: PromptLoader = Depends(get_prompt_loader)):
    """
    return PromptLoader()
