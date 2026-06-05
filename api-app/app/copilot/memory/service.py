"""
Memory service for session and long-term fact storage.

This module provides a hybrid memory service using Redis for short-term
session storage and PostgreSQL for long-term fact persistence.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import redis

from app.config import settings
from app.copilot.memory.postgres_store import PostgresMemoryStore
from app.core.logging import StructuredLogger

logger = StructuredLogger("memory_service")


@dataclass(frozen=True)
class MemorySnapshot:
    session: Dict[str, Any]
    facts: Dict[str, Any]


@dataclass
class FactMetadata:
    """Metadata for a memory fact."""
    key: str
    value: Any
    confidence: float
    pinned: bool
    source: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    version: int = 1


@dataclass
class MemoryExport:
    """Memory export data structure."""
    version: str = "1.0"
    exported_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: str = ""
    facts: List[Dict[str, Any]] = field(default_factory=list)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "exported_at": self.exported_at,
            "user_id": self.user_id,
            "facts": self.facts,
            "sessions": self.sessions,
            "metadata": self.metadata,
        }


@dataclass
class MemorySearchResult:
    """Result of a memory search."""
    facts: List[FactMetadata] = field(default_factory=list)
    total: int = 0
    query: str = ""
    limit: int = 50
    offset: int = 0


@dataclass
class MemoryAnalytics:
    """Memory usage analytics."""
    total_facts: int = 0
    pinned_facts: int = 0
    total_sessions: int = 0
    average_confidence: float = 0.0
    by_source: Dict[str, int] = field(default_factory=dict)
    by_tag: Dict[str, int] = field(default_factory=dict)
    storage_size_bytes: int = 0


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

    def search_facts(
        self,
        user_id: str,
        query: str,
        limit: int = 50,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        pinned_only: bool = False,
    ) -> MemorySearchResult:
        """
        Search for facts in memory.
        
        Args:
            user_id: User ID to search for
            query: Search query (matches keys and values)
            limit: Maximum number of results
            offset: Pagination offset
            tags: Filter by tags
            min_confidence: Minimum confidence threshold
            pinned_only: Only return pinned facts
        
        Returns:
            MemorySearchResult with matching facts
        """
        facts = self.pg_store.search_facts(
            user_id=user_id,
            query=query,
            limit=limit,
            offset=offset,
            tags=tags,
            min_confidence=min_confidence,
            pinned_only=pinned_only,
        )
        
        return MemorySearchResult(
            facts=facts,
            total=len(facts),
            query=query,
            limit=limit,
            offset=offset,
        )

    def export_memory(self, user_id: str, session_id: Optional[str] = None) -> MemoryExport:
        """
        Export memory data for a user.
        
        Args:
            user_id: User ID to export
            session_id: Optional session ID to include session data
        
        Returns:
            MemoryExport with all memory data
        """
        facts = self.pg_store.get_all_facts(user_id)
        
        export_facts = []
        for fact in facts:
            export_facts.append({
                "key": fact.key,
                "value": fact.value,
                "confidence": fact.confidence,
                "pinned": fact.pinned,
                "source": fact.source,
                "created_at": fact.created_at.isoformat() if fact.created_at else None,
                "updated_at": fact.updated_at.isoformat() if fact.updated_at else None,
            })
        
        sessions = []
        if session_id:
            session_data = self.get_session(session_id)
            if session_data:
                sessions.append({
                    "session_id": session_id,
                    "data": session_data,
                })
        
        return MemoryExport(
            user_id=user_id,
            facts=export_facts,
            sessions=sessions,
            metadata={
                "total_facts": len(export_facts),
                "total_sessions": len(sessions),
            },
        )

    def import_memory(self, export_data: MemoryExport, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Import memory data.
        
        Args:
            export_data: MemoryExport data to import
            user_id: Target user ID (defaults to export user_id)
        
        Returns:
            Summary of imported data
        """
        target_user_id = user_id or export_data.user_id
        
        imported_facts = 0
        imported_sessions = 0
        errors = []
        
        for fact_data in export_data.facts:
            try:
                self.pg_store.upsert_fact(
                    user_id=target_user_id,
                    scope="user",
                    key=fact_data["key"],
                    value=fact_data["value"],
                    confidence=float(fact_data.get("confidence", 1.0)),
                    source=fact_data.get("source", "import"),
                )
                imported_facts += 1
            except Exception as e:
                errors.append(f"Failed to import fact {fact_data.get('key')}: {str(e)}")
        
        for session_data in export_data.sessions:
            try:
                session_id = session_data.get("session_id")
                if session_id:
                    self.put_session(session_id, session_data.get("data", {}))
                    imported_sessions += 1
            except Exception as e:
                errors.append(f"Failed to import session: {str(e)}")
        
        return {
            "imported_facts": imported_facts,
            "imported_sessions": imported_sessions,
            "errors": errors,
            "success": len(errors) == 0,
        }

    def export_to_json(self, user_id: str, session_id: Optional[str] = None) -> str:
        """
        Export memory to JSON string.
        
        Args:
            user_id: User ID to export
            session_id: Optional session ID to include
        
        Returns:
            JSON string with memory data
        """
        export = self.export_memory(user_id, session_id)
        return json.dumps(export.to_dict() if hasattr(export, 'to_dict') else {
            "version": export.version,
            "exported_at": export.exported_at,
            "user_id": export.user_id,
            "facts": export.facts,
            "sessions": export.sessions,
            "metadata": export.metadata,
        }, indent=2)

    def export_to_csv(self, user_id: str) -> str:
        """
        Export facts to CSV format.
        
        Args:
            user_id: User ID to export
        
        Returns:
            CSV string with facts data
        """
        facts = self.pg_store.get_all_facts(user_id)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["key", "value", "confidence", "pinned", "source", "created_at", "updated_at"])
        
        # Write facts
        for fact in facts:
            writer.writerow([
                fact.key,
                json.dumps(fact.value) if isinstance(fact.value, (dict, list)) else fact.value,
                fact.confidence,
                fact.pinned,
                fact.source,
                fact.created_at.isoformat() if fact.created_at else "",
                fact.updated_at.isoformat() if fact.updated_at else "",
            ])
        
        return output.getvalue()

    def export_to_gzip_json(self, user_id: str, session_id: Optional[str] = None) -> bytes:
        """
        Export memory to gzip-compressed JSON.
        
        Args:
            user_id: User ID to export
            session_id: Optional session ID to include
        
        Returns:
            Gzip-compressed JSON bytes
        """
        json_data = self.export_to_json(user_id, session_id)
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
            f.write(json_data.encode('utf-8'))
        return buffer.getvalue()

    def add_tag(self, user_id: str, key: str, tag: str) -> bool:
        """
        Add a tag to a fact.
        
        Args:
            user_id: User ID
            key: Fact key
            tag: Tag to add
        
        Returns:
            True if tag was added successfully
        """
        return self.pg_store.add_tag(user_id, key, tag)

    def remove_tag(self, user_id: str, key: str, tag: str) -> bool:
        """
        Remove a tag from a fact.
        
        Args:
            user_id: User ID
            key: Fact key
            tag: Tag to remove
        
        Returns:
            True if tag was removed successfully
        """
        return self.pg_store.remove_tag(user_id, key, tag)

    def get_facts_by_tag(self, user_id: str, tag: str) -> List[FactMetadata]:
        """
        Get all facts with a specific tag.
        
        Args:
            user_id: User ID
            tag: Tag to filter by
        
        Returns:
            List of facts with the tag
        """
        return self.pg_store.get_facts_by_tag(user_id, tag)

    def version_fact(self, user_id: str, key: str) -> Optional[int]:
        """
        Increment the version of a fact.
        
        Args:
            user_id: User ID
            key: Fact key
        
        Returns:
            New version number or None if fact doesn't exist
        """
        return self.pg_store.increment_version(user_id, key)

    def get_fact_metadata(self, user_id: str, key: str) -> Optional[FactMetadata]:
        """
        Get metadata for a specific fact.
        
        Args:
            user_id: User ID
            key: Fact key
        
        Returns:
            FactMetadata or None if fact doesn't exist
        """
        return self.pg_store.get_fact_metadata(user_id, key)

    def get_analytics(self, user_id: str) -> MemoryAnalytics:
        """
        Get memory usage analytics for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            MemoryAnalytics with usage statistics
        """
        analytics = self.pg_store.get_analytics(user_id)
        
        # Update session count from Redis
        session_keys = self.redis_client.keys(f"ws:v2:session:{user_id}:*")
        analytics.total_sessions = len(session_keys)
        
        return analytics

    def get_all_analytics(self) -> Dict[str, MemoryAnalytics]:
        """
        Get memory analytics for all users.
        
        Returns:
            Dictionary mapping user IDs to their analytics
        """
        return self.pg_store.get_all_analytics()

    def cleanup_old_sessions(self, max_age_seconds: int = 86400) -> int:
        """
        Clean up old session data from Redis.
        
        Args:
            max_age_seconds: Maximum age in seconds for sessions to keep
        
        Returns:
            Number of sessions cleaned up
        """
        cleaned = 0
        keys = self.redis_client.keys("ws:v2:session:*")
        for key in keys:
            ttl = self.redis_client.ttl(key)
            if ttl == -2:  # Key doesn't exist (shouldn't happen but just in case)
                continue
            if ttl == -1:  # No TTL set
                # Check when it was created
                # For simplicity, we'll just set a TTL and continue
                self.redis_client.expire(key, max_age_seconds)
                continue
            # If TTL is less than or equal to 0, it's expired or about to expire
            # We can skip these as Redis will clean them up
        
        # Also clean up confirmation tokens
        confirm_keys = self.redis_client.keys("ws:v2:confirm:*")
        for key in confirm_keys:
            ttl = self.redis_client.ttl(key)
            if ttl == -1:
                self.redis_client.expire(key, 120)  # 2 minutes
        
        return cleaned


def build_memory_service() -> Optional[MemoryService]:
    """
    Build memory service if PostgreSQL is configured.
    
    Returns:
        MemoryService instance or None if PostgreSQL is not configured
    """
    pg_dsn = settings.memory_postgres_dsn or settings.database_url
    if not pg_dsn:
        logger.warning("Memory service not initialized - MEMORY_POSTGRES_DSN or DATABASE_URL not configured")
        return None
    return MemoryService(
        redis_url=settings.redis_url,
        pg_dsn=pg_dsn,
        session_ttl=settings.memory_session_ttl_seconds,
    )
