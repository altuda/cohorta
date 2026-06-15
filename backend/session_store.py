"""In-memory session store with TTL-based cleanup."""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

SESSION_TTL = 30 * 60  # 30 minutes


@dataclass
class SessionData:
    session_id: str
    created_at: float
    df: pd.DataFrame
    file_name: str
    columns: list[str]
    auto_roles: dict[str, str]
    # Cached render output
    cached_png: bytes | None = None           # low-DPI on-screen preview
    cached_png_hires: bytes | None = None      # 300-DPI PNG, built lazily on download
    cached_pdf: bytes | None = None            # vector PDF, built lazily on download
    cached_csv: bytes | None = None
    cached_warnings: list[str] = field(default_factory=list)
    render_config_hash: str | None = None
    # Last render request, kept so the hi-res PNG / PDF can be regenerated on
    # demand without re-running the whole interactive loop.
    render_req: Any = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}

    def create(self, df: pd.DataFrame, file_name: str, auto_roles: dict[str, str]) -> SessionData:
        self._evict_expired()
        sid = uuid.uuid4().hex[:16]
        session = SessionData(
            session_id=sid,
            created_at=time.time(),
            df=df,
            file_name=file_name,
            columns=df.columns.tolist(),
            auto_roles=auto_roles,
        )
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> SessionData | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if time.time() - session.created_at > SESSION_TTL:
            del self._sessions[session_id]
            return None
        return session

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.created_at > SESSION_TTL
        ]
        for sid in expired:
            del self._sessions[sid]


store = SessionStore()
