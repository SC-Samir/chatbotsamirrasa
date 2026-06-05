"""
PostgreSQL memory store for persistent fact storage.

This module provides durable storage for memory facts and events
using PostgreSQL as the backend.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

from app.core.logging import StructuredLogger

logger = StructuredLogger("memory_postgres")

try:
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None


@dataclass(frozen=True)
class FactRow:
    key: str
    value: Any
    confidence: float
    pinned: bool


class PostgresMemoryStore:
    def __init__(self, dsn: str):
        if psycopg is None:
            raise RuntimeError("psycopg is required for PostgreSQL memory store")
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self.dsn)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_facts (
                        user_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value_json JSONB NOT NULL,
                        confidence DOUBLE PRECISION NOT NULL,
                        pinned BOOLEAN NOT NULL DEFAULT FALSE,
                        source TEXT NOT NULL DEFAULT 'nlu',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (user_id, scope, key)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_events (
                        id BIGSERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        key TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_facts_user_scope ON memory_facts(user_id, scope)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_facts_updated_at ON memory_facts(updated_at)"
                )
            conn.commit()

    def get_facts(self, user_id: str, scope: str = "user") -> Dict[str, FactRow]:
        rows: Dict[str, FactRow] = {}
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT key, value_json, confidence, pinned FROM memory_facts WHERE user_id = %s AND scope = %s",
                    (user_id, scope),
                )
                for key, value_json, confidence, pinned in cur.fetchall():
                    rows[key] = FactRow(
                        key=key,
                        value=value_json,
                        confidence=float(confidence),
                        pinned=bool(pinned),
                    )
        return rows

    def upsert_fact(self, user_id: str, scope: str, key: str, value: Any, confidence: float, source: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value_json, confidence, pinned FROM memory_facts WHERE user_id = %s AND scope = %s AND key = %s",
                    (user_id, scope, key),
                )
                existing = cur.fetchone()
                if existing is not None:
                    old_value, old_confidence, old_pinned = existing
                    if bool(old_pinned) and old_value != value:
                        return
                    if float(old_confidence) > confidence and old_value != value:
                        return

                cur.execute(
                    """
                    INSERT INTO memory_facts(user_id, scope, key, value_json, confidence, source)
                    VALUES(%s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT(user_id, scope, key)
                    DO UPDATE SET
                        value_json = EXCLUDED.value_json,
                        confidence = EXCLUDED.confidence,
                        source = EXCLUDED.source,
                        updated_at = NOW()
                    """,
                    (user_id, scope, key, json.dumps(value), confidence, source),
                )
                cur.execute(
                    "INSERT INTO memory_events(user_id, scope, key, event_type, payload) VALUES(%s, %s, %s, %s, %s::jsonb)",
                    (user_id, scope, key, "upsert", json.dumps({"confidence": confidence, "source": source})),
                )
            conn.commit()

    def forget_fact(self, user_id: str, scope: str, key: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM memory_facts WHERE user_id = %s AND scope = %s AND key = %s",
                    (user_id, scope, key),
                )
                deleted = cur.rowcount > 0
                if deleted:
                    cur.execute(
                        "INSERT INTO memory_events(user_id, scope, key, event_type, payload) VALUES(%s, %s, %s, 'forget', %s::jsonb)",
                        (user_id, scope, key, "{}"),
                    )
            conn.commit()
            return deleted

    def pin_fact(self, user_id: str, scope: str, key: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE memory_facts SET pinned = TRUE, updated_at = NOW() WHERE user_id = %s AND scope = %s AND key = %s",
                    (user_id, scope, key),
                )
                updated = cur.rowcount > 0
                if updated:
                    cur.execute(
                        "INSERT INTO memory_events(user_id, scope, key, event_type, payload) VALUES(%s, %s, %s, 'pin', %s::jsonb)",
                        (user_id, scope, key, "{}"),
                    )
            conn.commit()
            return updated
