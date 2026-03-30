#!/usr/bin/env python3
"""
Helpers for resolving the active client in the multi-client WeWrite layout.

Official layout:
    clients/<client>/{style,history,playbook,writing-config}.yaml

Legacy fallback:
    {skill_root}/{style,history,playbook,writing-config}.yaml
"""

from dataclasses import dataclass
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
CLIENTS_DIR = SKILL_DIR / "clients"
LEGACY_FILES = ("style.yaml", "history.yaml", "playbook.md", "writing-config.yaml")
LEGACY_DIRS = ("corpus", "lessons")


@dataclass(frozen=True)
class ClientContext:
    name: str
    dir: Path
    source: str  # "client" or "legacy"

    @property
    def is_legacy(self) -> bool:
        return self.source == "legacy"

    def path(self, *parts: str) -> Path:
        return self.dir.joinpath(*parts)


def list_clients() -> list[str]:
    """Return client directory names, ignoring hidden folders."""
    if not CLIENTS_DIR.exists():
        return []
    return sorted(
        entry.name
        for entry in CLIENTS_DIR.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )


def has_legacy_layout() -> bool:
    """Detect whether the old root-level single-client layout still exists."""
    return any((SKILL_DIR / name).exists() for name in (*LEGACY_FILES, *LEGACY_DIRS))


def infer_client_from_path(path_str: str | None) -> str | None:
    """Infer a client name from paths like clients/<name>/... or output/<name>/...."""
    if not path_str:
        return None

    try:
        rel = Path(path_str).resolve().relative_to(SKILL_DIR)
    except Exception:
        return None

    parts = rel.parts
    if len(parts) >= 2 and parts[0] in {"clients", "output"}:
        return parts[1]
    return None


def resolve_client_context(client: str | None, *, purpose: str) -> ClientContext:
    """Resolve the active client, falling back to the legacy root layout if needed."""
    clients = list_clients()

    if client:
        client_dir = CLIENTS_DIR / client
        if client_dir.exists():
            return ClientContext(name=client, dir=client_dir, source="client")
        if client == "default" and not clients and has_legacy_layout():
            return ClientContext(name="default", dir=SKILL_DIR, source="legacy")
        raise ValueError(
            f"Client '{client}' not found for {purpose}. "
            f"Available clients: {', '.join(clients) or 'none'}."
        )

    if len(clients) == 1:
        only = clients[0]
        return ClientContext(name=only, dir=CLIENTS_DIR / only, source="client")

    if not clients and has_legacy_layout():
        return ClientContext(name="default", dir=SKILL_DIR, source="legacy")

    if not clients:
        raise ValueError(
            f"No clients found for {purpose}. Create one under {CLIENTS_DIR} first."
        )

    raise ValueError(
        f"Multiple clients found for {purpose}: {', '.join(clients)}. "
        "Pass --client to choose one."
    )
