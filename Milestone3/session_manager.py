"""
Session Manager - Twilio Call Session State
Manages multi-turn conversation state using CallSid as session key.
In production, replace in-memory dict with Redis.
"""

from datetime import datetime, timedelta
from typing import Any, Optional

# In-memory session store (use Redis in production)
_sessions: dict[str, dict] = {}

SESSION_TTL_MINUTES = 30  # sessions expire after 30 min of inactivity


# ─────────────────────────────────────────────
#  SESSION CRUD
# ─────────────────────────────────────────────

def get_session(call_sid: str) -> dict:
    """Get session for a call, creating if not exists."""
    _cleanup_expired()
    if call_sid not in _sessions:
        _sessions[call_sid] = {
            "call_sid": call_sid,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "flow": None,          # Current conversation flow
            "stage": "welcome",    # Current stage within flow
            "intent": None,        # Detected intent
            "collected": {},       # Collected data (name, ward, etc.)
            "retry_count": 0,      # Consecutive failed recognitions
            "language": "en-IN",   # Detected/preferred language
            "turns": 0,            # Total conversation turns
        }
    else:
        _sessions[call_sid]["last_activity"] = datetime.now()
    return _sessions[call_sid]


def update_session(call_sid: str, updates: dict) -> dict:
    """Update specific fields in a session."""
    session = get_session(call_sid)
    session.update(updates)
    session["last_activity"] = datetime.now()
    session["turns"] = session.get("turns", 0) + 1
    return session


def set_collected(call_sid: str, key: str, value: Any) -> None:
    """Store a collected piece of data (e.g., patient_name, ward_choice)."""
    session = get_session(call_sid)
    session["collected"][key] = value
    session["last_activity"] = datetime.now()


def get_collected(call_sid: str, key: str, default=None) -> Any:
    """Retrieve a collected value."""
    session = get_session(call_sid)
    return session["collected"].get(key, default)


def increment_retry(call_sid: str) -> int:
    """Increment retry counter and return new count."""
    session = get_session(call_sid)
    session["retry_count"] = session.get("retry_count", 0) + 1
    return session["retry_count"]


def reset_retry(call_sid: str) -> None:
    """Reset retry counter after a successful recognition."""
    session = get_session(call_sid)
    session["retry_count"] = 0


def end_session(call_sid: str) -> None:
    """Remove a session when call ends."""
    _sessions.pop(call_sid, None)


def get_all_sessions() -> dict:
    """For admin/debug: return all active sessions."""
    _cleanup_expired()
    return {
        sid: {
            "flow": s["flow"],
            "stage": s["stage"],
            "turns": s["turns"],
            "created_at": s["created_at"].isoformat(),
        }
        for sid, s in _sessions.items()
    }


# ─────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────

def _cleanup_expired() -> None:
    """Remove sessions that have been inactive past TTL."""
    cutoff = datetime.now() - timedelta(minutes=SESSION_TTL_MINUTES)
    expired = [sid for sid, s in _sessions.items() if s["last_activity"] < cutoff]
    for sid in expired:
        del _sessions[sid]
