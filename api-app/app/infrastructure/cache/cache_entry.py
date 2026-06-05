"""
Cache entry and statistics data structures.

This module defines the data structures used for cache management.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from enum import Enum


class CacheStrategy(str, Enum):
    """Cache invalidation/strategy types."""
    TIME_BASED = "time_based"  # Expire after TTL
    SIZE_BASED = "size_based"  # Evict when size limit reached (LRU)
    MANUAL = "manual"  # Manual invalidation only
    HYBRID = "hybrid"  # Time-based + size-based


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    value: Any
    ttl: int = 300  # Time to live in seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    hit_count: int = 0
    size: int = 0  # Size in bytes
    
    def __post_init__(self):
        """Calculate expires_at from ttl."""
        if self.expires_at is None and self.ttl > 0:
            self.expires_at = datetime.utcnow() + self.ttl
        if self.size == 0 and self.value is not None:
            self.size = len(str(self.value).encode('utf-8'))
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """Update the access time and increment hit count."""
        self.accessed_at = datetime.utcnow()
        self.hit_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "ttl": self.ttl,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "tags": self.tags,
            "hit_count": self.hit_count,
            "size": self.size,
        }


@dataclass
class CacheStats:
    """Cache statistics."""
    total_entries: int = 0
    total_size: int = 0  # Total size in bytes
    hit_count: int = 0
    miss_count: int = 0
    hit_rate: float = 0.0
    eviction_count: int = 0
    expiration_count: int = 0
    average_ttl: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_entries": self.total_entries,
            "total_size": self.total_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": self.hit_rate,
            "eviction_count": self.eviction_count,
            "expiration_count": self.expiration_count,
            "average_ttl": self.average_ttl,
        }


@dataclass
class CacheConfig:
    """Cache configuration."""
    default_ttl: int = 300  # 5 minutes
    max_size: int = 10000  # Maximum number of entries
    max_memory: int = 1024 * 1024 * 100  # 100MB
    strategy: CacheStrategy = CacheStrategy.HYBRID
    cleanup_interval: int = 60  # Cleanup interval in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "default_ttl": self.default_ttl,
            "max_size": self.max_size,
            "max_memory": self.max_memory,
            "strategy": self.strategy.value,
            "cleanup_interval": self.cleanup_interval,
        }
