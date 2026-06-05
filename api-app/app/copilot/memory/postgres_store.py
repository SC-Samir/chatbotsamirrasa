"""
PostgreSQL memory store for persistent fact storage.

This module provides durable storage for memory facts and events
using PostgreSQL as the backend.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    source: str = "nlu"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    tags: List[str] = field(default_factory=list)


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
                        version INTEGER NOT NULL DEFAULT 1,
                        PRIMARY KEY (user_id, scope, key)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_fact_tags (
                        user_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        key TEXT NOT NULL,
                        tag TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (user_id, scope, key, tag),
                        FOREIGN KEY (user_id, scope, key) REFERENCES memory_facts(user_id, scope, key) ON DELETE CASCADE
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
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_fact_tags_tag ON memory_fact_tags(tag)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_memory_fact_tags_user_tag ON memory_fact_tags(user_id, tag)"
                )
            conn.commit()
            
            # Add new columns if they don't exist (for existing databases)
            self._add_missing_columns()
    
    def _add_missing_columns(self) -> None:
        """Add missing columns for backward compatibility."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Check if version column exists
                cur.execute(
                    """
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'memory_facts' AND column_name = 'version'
                    """
                )
                if cur.fetchone() is None:
                    cur.execute("ALTER TABLE memory_facts ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
                
                # Check if memory_fact_tags table exists
                cur.execute(
                    """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name = 'memory_fact_tags'
                    """
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """
                        CREATE TABLE memory_fact_tags (
                            user_id TEXT NOT NULL,
                            scope TEXT NOT NULL,
                            key TEXT NOT NULL,
                            tag TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            PRIMARY KEY (user_id, scope, key, tag),
                            FOREIGN KEY (user_id, scope, key) REFERENCES memory_facts(user_id, scope, key) ON DELETE CASCADE
                        )
                        """
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_memory_fact_tags_tag ON memory_fact_tags(tag)"
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_memory_fact_tags_user_tag ON memory_fact_tags(user_id, tag)"
                    )
            conn.commit()

    def get_facts(self, user_id: str, scope: str = "user") -> Dict[str, FactRow]:
        rows: Dict[str, FactRow] = {}
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT key, value_json, confidence, pinned, source, created_at, updated_at, version 
                    FROM memory_facts WHERE user_id = %s AND scope = %s""",
                    (user_id, scope),
                )
                for row in cur.fetchall():
                    key, value_json, confidence, pinned, source, created_at, updated_at, version = row
                    # Get tags for this fact
                    cur.execute(
                        """SELECT tag FROM memory_fact_tags 
                        WHERE user_id = %s AND scope = %s AND key = %s""",
                        (user_id, scope, key),
                    )
                    tags = [t[0] for t in cur.fetchall()]
                    
                    rows[key] = FactRow(
                        key=key,
                        value=value_json,
                        confidence=float(confidence),
                        pinned=bool(pinned),
                        source=source or "nlu",
                        created_at=created_at,
                        updated_at=updated_at,
                        version=int(version) if version is not None else 1,
                        tags=tags,
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

    def get_all_facts(self, user_id: str, scope: str = "user") -> List[FactRow]:
        """Get all facts as a list."""
        facts_dict = self.get_facts(user_id, scope)
        return list(facts_dict.values())

    def search_facts(
        self,
        user_id: str,
        query: str,
        limit: int = 50,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        pinned_only: bool = False,
    ) -> List[FactRow]:
        """Search for facts matching the query."""
        facts: List[FactRow] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Build the base query
                where_clauses = ["user_id = %s", "scope = %s"]
                params: List[Any] = [user_id, "user"]
                
                if query:
                    where_clauses.append(
                        "(key ILIKE %s OR value_json::text ILIKE %s)"
                    )
                    query_param = f"%{query}%"
                    params.extend([query_param, query_param])
                
                if tags:
                    where_clauses.append("key IN (SELECT key FROM memory_fact_tags WHERE tag = ANY(%s) AND user_id = %s AND scope = %s)")
                    params.extend([tags, user_id, "user"])
                
                if min_confidence > 0:
                    where_clauses.append("confidence >= %s")
                    params.append(min_confidence)
                
                if pinned_only:
                    where_clauses.append("pinned = TRUE")
                
                where_clause = " AND ".join(where_clauses) if len(where_clauses) > 2 else " AND ".join(where_clauses)
                
                cur.execute(
                    f"""SELECT key, value_json, confidence, pinned, source, created_at, updated_at, version 
                    FROM memory_facts 
                    WHERE {where_clause}
                    ORDER BY confidence DESC, updated_at DESC
                    LIMIT %s OFFSET %s""",
                    params + [limit, offset],
                )
                
                for row in cur.fetchall():
                    key, value_json, confidence, pinned, source, created_at, updated_at, version = row
                    # Get tags for this fact
                    cur.execute(
                        """SELECT tag FROM memory_fact_tags 
                        WHERE user_id = %s AND scope = %s AND key = %s""",
                        (user_id, "user", key),
                    )
                    fact_tags = [t[0] for t in cur.fetchall()]
                    
                    facts.append(FactRow(
                        key=key,
                        value=value_json,
                        confidence=float(confidence),
                        pinned=bool(pinned),
                        source=source or "nlu",
                        created_at=created_at,
                        updated_at=updated_at,
                        version=int(version) if version is not None else 1,
                        tags=fact_tags,
                    ))
        
        return facts

    def add_tag(self, user_id: str, key: str, tag: str, scope: str = "user") -> bool:
        """Add a tag to a fact."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Check if fact exists
                cur.execute(
                    "SELECT 1 FROM memory_facts WHERE user_id = %s AND scope = %s AND key = %s",
                    (user_id, scope, key),
                )
                if cur.fetchone() is None:
                    return False
                
                # Check if tag already exists
                cur.execute(
                    "SELECT 1 FROM memory_fact_tags WHERE user_id = %s AND scope = %s AND key = %s AND tag = %s",
                    (user_id, scope, key, tag),
                )
                if cur.fetchone() is not None:
                    return False  # Tag already exists
                
                # Add the tag
                cur.execute(
                    "INSERT INTO memory_fact_tags(user_id, scope, key, tag) VALUES(%s, %s, %s, %s)",
                    (user_id, scope, key, tag),
                )
            conn.commit()
            return True

    def remove_tag(self, user_id: str, key: str, tag: str, scope: str = "user") -> bool:
        """Remove a tag from a fact."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM memory_fact_tags WHERE user_id = %s AND scope = %s AND key = %s AND tag = %s",
                    (user_id, scope, key, tag),
                )
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted

    def get_facts_by_tag(self, user_id: str, tag: str, scope: str = "user") -> List[FactRow]:
        """Get all facts with a specific tag."""
        facts: List[FactRow] = []
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT f.key, f.value_json, f.confidence, f.pinned, f.source, f.created_at, f.updated_at, f.version 
                    FROM memory_facts f
                    JOIN memory_fact_tags t ON f.user_id = t.user_id AND f.scope = t.scope AND f.key = t.key
                    WHERE f.user_id = %s AND f.scope = %s AND t.tag = %s""",
                    (user_id, scope, tag),
                )
                
                for row in cur.fetchall():
                    key, value_json, confidence, pinned, source, created_at, updated_at, version = row
                    # Get all tags for this fact
                    cur.execute(
                        """SELECT tag FROM memory_fact_tags 
                        WHERE user_id = %s AND scope = %s AND key = %s""",
                        (user_id, scope, key),
                    )
                    fact_tags = [t[0] for t in cur.fetchall()]
                    
                    facts.append(FactRow(
                        key=key,
                        value=value_json,
                        confidence=float(confidence),
                        pinned=bool(pinned),
                        source=source or "nlu",
                        created_at=created_at,
                        updated_at=updated_at,
                        version=int(version) if version is not None else 1,
                        tags=fact_tags,
                    ))
        
        return facts

    def increment_version(self, user_id: str, key: str, scope: str = "user") -> Optional[int]:
        """Increment the version of a fact."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE memory_facts 
                    SET version = version + 1, updated_at = NOW() 
                    WHERE user_id = %s AND scope = %s AND key = %s 
                    RETURNING version""",
                    (user_id, scope, key),
                )
                result = cur.fetchone()
                conn.commit()
                if result:
                    return result[0]
                return None

    def get_fact_metadata(self, user_id: str, key: str, scope: str = "user") -> Optional[FactRow]:
        """Get metadata for a specific fact."""
        facts = self.get_facts(user_id, scope)
        return facts.get(key)

    def get_analytics(self, user_id: str) -> Any:
        """Get memory usage analytics for a user."""
        from app.copilot.memory.service import MemoryAnalytics
        
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Total facts
                cur.execute(
                    "SELECT COUNT(*) FROM memory_facts WHERE user_id = %s",
                    (user_id,),
                )
                total_facts = cur.fetchone()[0]
                
                # Pinned facts
                cur.execute(
                    "SELECT COUNT(*) FROM memory_facts WHERE user_id = %s AND pinned = TRUE",
                    (user_id,),
                )
                pinned_facts = cur.fetchone()[0]
                
                # Average confidence
                cur.execute(
                    "SELECT AVG(confidence) FROM memory_facts WHERE user_id = %s",
                    (user_id,),
                )
                avg_confidence = cur.fetchone()[0] or 0.0
                
                # By source
                cur.execute(
                    "SELECT source, COUNT(*) FROM memory_facts WHERE user_id = %s GROUP BY source",
                    (user_id,),
                )
                by_source = {row[0]: row[1] for row in cur.fetchall()}
                
                # By tag
                cur.execute(
                    """SELECT tag, COUNT(*) FROM memory_fact_tags 
                    WHERE user_id = %s GROUP BY tag""",
                    (user_id,),
                )
                by_tag = {row[0]: row[1] for row in cur.fetchall()}
                
                # Storage size (approximate)
                cur.execute(
                    "SELECT SUM(OCTET_LENGTH(value_json::text)) FROM memory_facts WHERE user_id = %s",
                    (user_id,),
                )
                storage_size = cur.fetchone()[0] or 0
                
                # Total sessions (from Redis - we'll return 0 here as we don't have access to Redis)
                # This will be updated in the MemoryService
                total_sessions = 0
        
        return MemoryAnalytics(
            total_facts=total_facts,
            pinned_facts=pinned_facts,
            total_sessions=total_sessions,
            average_confidence=float(avg_confidence),
            by_source=by_source,
            by_tag=by_tag,
            storage_size_bytes=storage_size,
        )

    def get_all_analytics(self) -> Dict[str, Any]:
        """Get memory analytics for all users."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Get all user IDs
                cur.execute("SELECT DISTINCT user_id FROM memory_facts")
                user_ids = [row[0] for row in cur.fetchall()]
        
        return {user_id: self.get_analytics(user_id) for user_id in user_ids}
