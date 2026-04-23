"""Secure optional user authentication and support services."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import string
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    success: bool
    message: str
    username: Optional[str] = None
    session_token: Optional[str] = None


@dataclass
class SupportTicket:
    ticket_id: str
    owner: str
    subject: str
    status: str = "open"
    created_at: int = 0
    updated_at: int = 0
    messages: List[Dict[str, Any]] = field(default_factory=list)


class UserService:
    """Security-first optional user login + support ticket subsystem."""

    def __init__(self, storage_dir: Path, enabled: bool = False):
        self.enabled = bool(enabled)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.storage_dir / "user_security_db.json"
        self._lock = threading.RLock()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._db: Dict[str, Any] = self._default_db()
        self._load_db_with_healing()

    def enable(self) -> None:
        """Dynamically enable the user service."""
        with self._lock:
            self.enabled = True

    def disable(self) -> None:
        """Dynamically disable the user service, clearing sessions."""
        with self._lock:
            self.enabled = False
            self._active_sessions.clear()

    def _default_db(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "users": {},
            "support_tickets": {},
            "security": {
                "max_failed_attempts": 5,
                "base_lockout_seconds": 30,
                "max_lockout_seconds": 900,
            },
        }

    def _load_db_with_healing(self) -> None:
        """Muninn restores damaged storage from backup defaults when required."""
        with self._lock:
            try:
                if not self._db_path.exists():
                    self._persist_db_locked()
                    return

                raw = self._db_path.read_text(encoding="utf-8")
                loaded = json.loads(raw)
                if not isinstance(loaded, dict):
                    raise ValueError("Invalid DB root type")
                self._db = self._heal_db_shape(loaded)
                self._persist_db_locked()
            except Exception as exc:
                logger.warning("User DB corrupted, self-healing to defaults: %s", exc)
                try:
                    if self._db_path.exists():
                        recovery = self._db_path.with_suffix(
                            f".corrupt.{int(time.time())}.json"
                        )
                        self._db_path.replace(recovery)
                except Exception as move_exc:
                    logger.warning(
                        "Failed to preserve corrupt DB snapshot: %s", move_exc
                    )
                self._db = self._default_db()
                self._persist_db_locked()

    def _heal_db_shape(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        healed = self._default_db()
        healed["version"] = int(payload.get("version", 1))
        healed["users"] = (
            payload.get("users", {}) if isinstance(payload.get("users"), dict) else {}
        )
        healed["support_tickets"] = (
            payload.get("support_tickets", {})
            if isinstance(payload.get("support_tickets"), dict)
            else {}
        )
        security = (
            payload.get("security", {})
            if isinstance(payload.get("security"), dict)
            else {}
        )
        healed["security"].update(
            {
                "max_failed_attempts": int(security.get("max_failed_attempts", 5)),
                "base_lockout_seconds": int(security.get("base_lockout_seconds", 30)),
                "max_lockout_seconds": int(security.get("max_lockout_seconds", 900)),
            }
        )
        return healed

    def _persist_db_locked(self) -> None:
        temp_path = self._db_path.with_suffix(".tmp")
        serialized = json.dumps(self._db, indent=2, sort_keys=True)
        temp_path.write_text(serialized, encoding="utf-8")
        os.chmod(temp_path, 0o600)
        temp_path.replace(self._db_path)

    def _normalize_username(self, username: str) -> str:
        cleaned = "".join(
            ch
            for ch in username.strip().lower()
            if ch in string.ascii_lowercase + string.digits + "_-"
        )
        return cleaned[:32]

    def _password_hash(self, password: str, salt: bytes) -> str:
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return derived.hex()

    def _validate_password_policy(self, password: str) -> Tuple[bool, str]:
        if len(password) < 12:
            return False, "Password must be at least 12 characters long."
        if password.lower() == password or password.upper() == password:
            return False, "Password must mix both uppercase and lowercase letters."
        if not any(ch.isdigit() for ch in password):
            return False, "Password must include at least one number."
        if not any(ch in string.punctuation for ch in password):
            return (
                False,
                "Password must include at least one special symbol (e.g. !@#$).",
            )
        return True, "ok"

    def register_user(self, username: str, password: str) -> AuthResult:
        if not self.enabled:
            return AuthResult(False, "Login is disabled by configuration.")
        with self._lock:
            try:
                norm = self._normalize_username(username)
                if len(norm) < 3:
                    return AuthResult(False, "Username must be 3+ allowed characters.")
                if norm in self._db["users"]:
                    return AuthResult(False, "Username already exists.")

                valid, reason = self._validate_password_policy(password)
                if not valid:
                    return AuthResult(False, reason)

                salt = secrets.token_bytes(16)
                self._db["users"][norm] = {
                    "password_salt": salt.hex(),
                    "password_hash": self._password_hash(password, salt),
                    "created_at": int(time.time()),
                    "failed_attempts": 0,
                    "locked_until": 0,
                    "support_flags": [],
                }
                self._persist_db_locked()
                return AuthResult(True, "User registered.", username=norm)
            except Exception as exc:
                logger.warning("register_user failed: %s", exc)
                return AuthResult(False, "Registration failed due to internal error.")

    def login_user(self, username: str, password: str) -> AuthResult:
        if not self.enabled:
            return AuthResult(False, "Login is disabled by configuration.")
        with self._lock:
            try:
                norm = self._normalize_username(username)
                record = self._db["users"].get(norm)
                if not record:
                    return AuthResult(False, "Invalid username or password.")

                now = int(time.time())
                locked_until = int(record.get("locked_until", 0))
                if locked_until > now:
                    remaining = locked_until - now
                    return AuthResult(
                        False, f"Account locked. Try again in {remaining}s."
                    )

                salt = bytes.fromhex(str(record.get("password_salt", "")))
                candidate_hash = self._password_hash(password, salt)
                expected_hash = str(record.get("password_hash", ""))
                if not hmac.compare_digest(candidate_hash, expected_hash):
                    attempts = int(record.get("failed_attempts", 0)) + 1
                    record["failed_attempts"] = attempts
                    threshold = int(self._db["security"].get("max_failed_attempts", 5))
                    if attempts >= threshold:
                        base_lock = int(
                            self._db["security"].get("base_lockout_seconds", 30)
                        )
                        max_lock = int(
                            self._db["security"].get("max_lockout_seconds", 900)
                        )
                        lock_seconds = min(
                            base_lock * (2 ** max(0, attempts - threshold)), max_lock
                        )
                        record["locked_until"] = now + lock_seconds
                    self._persist_db_locked()
                    return AuthResult(False, "Invalid username or password.")

                record["failed_attempts"] = 0
                record["locked_until"] = 0
                token = secrets.token_urlsafe(32)
                self._active_sessions[token] = {
                    "username": norm,
                    "issued_at": now,
                    "expires_at": now + 86400,
                }
                self._persist_db_locked()
                return AuthResult(
                    True, "Login successful.", username=norm, session_token=token
                )
            except Exception as exc:
                logger.warning("login_user failed: %s", exc)
                return AuthResult(False, "Login failed due to internal error.")

    def logout(self, session_token: Optional[str]) -> bool:
        with self._lock:
            if not session_token:
                return False
            return self._active_sessions.pop(session_token, None) is not None

    def validate_session(self, session_token: Optional[str]) -> Optional[str]:
        with self._lock:
            if not session_token:
                return None
            session = self._active_sessions.get(session_token)
            if not session:
                return None
            if int(session.get("expires_at", 0)) <= int(time.time()):
                self._active_sessions.pop(session_token, None)
                return None
            return str(session.get("username"))

    def create_support_ticket(
        self, username: str, subject: str, message: str
    ) -> Tuple[bool, str]:
        if not self.enabled:
            return False, "Support system is disabled because login is disabled."
        with self._lock:
            try:
                norm = self._normalize_username(username)
                if norm not in self._db["users"]:
                    return False, "Unknown user."
                if not subject.strip() or not message.strip():
                    return False, "Subject and message are required."
                ticket_id = f"TKT-{int(time.time())}-{secrets.randbelow(10000):04d}"
                now = int(time.time())
                ticket = SupportTicket(
                    ticket_id=ticket_id,
                    owner=norm,
                    subject=subject.strip()[:120],
                    status="open",
                    created_at=now,
                    updated_at=now,
                    messages=[
                        {
                            "author": norm,
                            "message": message.strip()[:2000],
                            "timestamp": now,
                        }
                    ],
                )
                self._db["support_tickets"][ticket_id] = ticket.__dict__
                self._persist_db_locked()
                return True, ticket_id
            except Exception as exc:
                logger.warning("create_support_ticket failed: %s", exc)
                return False, "Ticket creation failed due to internal error."

    def list_support_tickets(self, username: str) -> List[Dict[str, Any]]:
        with self._lock:
            norm = self._normalize_username(username)
            tickets = []
            for ticket in self._db.get("support_tickets", {}).values():
                if isinstance(ticket, dict) and ticket.get("owner") == norm:
                    tickets.append(ticket)
            return sorted(
                tickets, key=lambda t: int(t.get("updated_at", 0)), reverse=True
            )

    def update_support_ticket(
        self, username: str, ticket_id: str, message: str, close: bool = False
    ) -> Tuple[bool, str]:
        with self._lock:
            try:
                norm = self._normalize_username(username)
                ticket = self._db.get("support_tickets", {}).get(ticket_id)
                if not isinstance(ticket, dict):
                    return False, "Ticket not found."
                if ticket.get("owner") != norm:
                    return False, "Access denied for ticket."
                now = int(time.time())
                if message.strip():
                    ticket.setdefault("messages", []).append(
                        {
                            "author": norm,
                            "message": message.strip()[:2000],
                            "timestamp": now,
                        }
                    )
                ticket["updated_at"] = now
                if close:
                    ticket["status"] = "closed"
                self._persist_db_locked()
                return True, "Ticket updated."
            except Exception as exc:
                logger.warning("update_support_ticket failed: %s", exc)
                return False, "Ticket update failed due to internal error."
