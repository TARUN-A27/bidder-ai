from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas.scoring import ScoringRules


class ScoringConfigurationError(Exception):
    """Raised when scoring configuration is missing or invalid."""


class ScoringConfigLoader:
    def load(self, source_path: str | Path) -> ScoringRules:
        path = Path(source_path).expanduser()
        if not path.exists():
            raise ScoringConfigurationError(
                f"Scoring configuration does not exist: {path}"
            )
        if not path.is_file():
            raise ScoringConfigurationError(
                f"Scoring configuration path is not a file: {path}"
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ScoringConfigurationError(
                f"Malformed scoring JSON in {path.name}: "
                f"line {exc.lineno}, column {exc.colno}"
            ) from exc
        except OSError as exc:
            raise ScoringConfigurationError(
                f"Could not read scoring configuration: {path}"
            ) from exc
        if not isinstance(payload, dict):
            raise ScoringConfigurationError(
                f"Scoring configuration root must be an object: {path.name}"
            )
        try:
            return ScoringRules.model_validate(payload)
        except ValidationError as exc:
            raise ScoringConfigurationError(
                f"Invalid scoring configuration in {path.name}: {exc}"
            ) from exc
