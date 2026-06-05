"""
Memory service for session and long-term fact storage.

This module provides a hybrid memory service using Redis for short-term
session storage and PostgreSQL for long-term fact persistence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

import redis

from app.config import settings
from app.copilot.memory.postgres_store import PostgresMemoryStore


@dataclass(frozen=True)
class MemorySnapshot:
    session: Dict[str, Any]
    facts: Dict[str, Any]


class MemoryService:
    def __init__(self, redis_url: str, pg_dsn: str, session_ttl: int):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.pg_store = PostgresMemoryStore(pg_dsn)
        self.session_ttl = session_ttl

    def _session_key(self, session_id: str) -> str:
        return f"ws:v2:session:{session_id}"

    def _confirm_key(self, session_id: str, token: str) -> str:
        return f"ws:v2:confirm:{session_id}:{token}"

    def get_session(self, session_id: str) -> Dict[str, Any]:
        raw = self.redis_client.get(self._session_key(session_id))
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def put_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        self.redis_client.setex(self._session_key(session_id), self.session_ttl, json.dumps(payload))

    def merge_entities(self, session_id: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        session = self.get_session(session_id)
        merged = session.get("entities", {})
        for key, value in entities.items():
            if value is not None:
                merged[key] = value
        session["entities"] = merged
        self.put_session(session_id, session)
        return merged

    def persist_facts(self, user_id: str, facts: Dict[str, Any], confidence: float, source: str = "nlu") -> None:
        for key, value in facts.items():
            self.pg_store.upsert_fact(user_id=user_id, scope="user", key=key, value=value, confidence=confidence, source=source)

    def get_facts(self, user_id: str) -> Dict[str, Any]:
        rows = self.pg_store.get_facts(user_id=user_id, scope="user")
        return {k: v.value for k, v in rows.items()}

    def snapshot(self, user_id: str, session_id: str) -> MemorySnapshot:
        return MemorySnapshot(session=self.get_session(session_id), facts=self.get_facts(user_id))

    def forget(self, user_id: str, key: str) -> bool:
        return self.pg_store.forget_fact(user_id=user_id, scope="user", key=key)

    def pin(self, user_id: str, key: str) -> bool:
        return self.pg_store.pin_fact(user_id=user_id, scope="user", key=key)

    def issue_confirmation_token(self, session_id: str, command: str, payload: Dict[str, Any], ttl_seconds: int = 120) -> str:
        import secrets

        token = secrets.token_hex(4)
        self.redis_client.setex(self._confirm_key(session_id, token), ttl_seconds, json.dumps({"command": command, "payload": payload}))
        return token

    def consume_confirmation_token(self, session_id: str, token: str) -> Dict[str, Any] | None:
        key = self._confirm_key(session_id, token)
        raw = self.redis_client.get(key)
        if not raw:
            return None
        self.redis_client.delete(key)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None


def build_memory_service() -> MemoryService:
    if not settings.memory_postgres_dsn:
        raise RuntimeError("MEMORY_POSTGRES_DSN or DATABASE_URL is required for ws.v2 memory")
    return MemoryService(
        redis_url=settings.redis_url,
        pg_dsn=settings.memory_postgres_dsn,
        session_ttl=settings.memory_session_ttl_seconds,
    )
