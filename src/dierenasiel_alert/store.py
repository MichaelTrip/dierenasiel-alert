from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Set


# Use ~/.local/share/dierenasiel-alert/seen.json by default
# This ensures the store works regardless of where the command is run from
DEFAULT_STORE = Path.home() / ".local/share/dierenasiel-alert/seen.json"


@dataclass(frozen=True)
class StoreKey:
    site: str
    availability: str
    animal_type: str = "katten"

    def key(self) -> str:
        return f"animal_type={self.animal_type}|site={self.site}|availability={self.availability}"


def load_seen(path: Path, key: StoreKey) -> Set[str]:
    path = path.expanduser()
    if not path.exists():
        return set()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return set()

    ids = data.get(key.key(), [])
    if isinstance(ids, list):
        return set(map(str, ids))
    return set()


def save_seen(path: Path, key: StoreKey, ids: Iterable[str]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except Exception:
            data = {}

    data[key.key()] = sorted(set(map(str, ids)))

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
