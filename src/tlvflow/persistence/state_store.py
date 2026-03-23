"""JSON snapshot persistence for in-memory repositories.

This module stores a single snapshot file (state.json) that can be loaded on
startup to restore the application's in-memory repositories after a restart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


@dataclass(frozen=True)
class StateStore:
    """Persist and restore application state as an atomic JSON snapshot."""

    path: Path

    def load(self) -> dict[str, Any]:
        """Load a snapshot from disk.

        Returns an empty dict if the file does not exist.
        """
        if not self.path.exists():
            return {}

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(
                "Invalid state file format: expected a JSON object at top level"
            )

        return dict(raw)

    def save(self, snapshot: dict[str, Any]) -> None:
        """Persist a snapshot atomically (temp file + rename)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with NamedTemporaryFile(
            mode="w",
            delete=False,
            dir=self.path.parent,
            encoding="utf-8",
            newline="\n",
        ) as tmp:
            json.dump(snapshot, tmp, ensure_ascii=False)
            tmp_path = Path(tmp.name)

        tmp_path.replace(self.path)
