"""Settings from the environment, with an optional .env file at the repo root.

The .env file is git-ignored. It holds KEY=value lines, for example:

    ANTHROPIC_API_KEY=...
    NDA_REVIEW_MODEL=claude-sonnet-5-5
    NDA_REVIEW_EFFORT=medium

A variable already set in the environment wins over the .env file. Nothing in this module ever
prints or logs a value; errors name the variable only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import playbook as pb  # noqa: E402

ENV_FILE = pb.ROOT / ".env"


class SettingError(RuntimeError):
    pass


def load_dotenv(path: Path | None = None) -> None:
    path = path or ENV_FILE
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def require(name: str) -> str:
    load_dotenv()
    value = os.environ.get(name, "").strip()
    if not value:
        raise SettingError(f"{name} is not set. Set it in your environment or in .env at the repo root "
                           f"(see README, Quick start).")
    return value


def optional(name: str) -> str:
    load_dotenv()
    return os.environ.get(name, "").strip()
