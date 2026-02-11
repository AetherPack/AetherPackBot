"""
会话追踪器 - 跟踪和管理消息会话
Session tracker - tracks and manages message sessions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrackedSession:
    """
    被追踪的会话
    A tracked session.
    """

    session_id: str = ""
    platform: str = ""
    last_active: float = 0.0
    message_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionTracker:
    """
    会话追踪器 - 追踪所有活跃会话
    Session tracker - tracks all active sessions.
    """

    def __init__(self, timeout_seconds: int = 3600) -> None:
        self._sessions: dict[str, TrackedSession] = {}
        self._timeout = timeout_seconds

    def touch(self, session_id: str, platform: str = "") -> TrackedSession:
        """
        更新会话活跃时间
        Update session activity time.
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = TrackedSession(
                session_id=session_id,
                platform=platform,
                last_active=time.time(),
                message_count=1,
            )
        else:
            session = self._sessions[session_id]
            session.last_active = time.time()
            session.message_count += 1

        return self._sessions[session_id]

    def get(self, session_id: str) -> TrackedSession | None:
        """获取会话 / Get a session."""
        return self._sessions.get(session_id)

    def cleanup_expired(self) -> int:
        """
        清理过期会话
        Clean up expired sessions.
        """
        now = time.time()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session.last_active > self._timeout
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    @property
    def active_count(self) -> int:
        """活跃会话数 / Number of active sessions."""
        return len(self._sessions)
