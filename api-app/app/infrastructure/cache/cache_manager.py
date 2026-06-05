"""
Cache Manager for response and query caching.

This module provides a comprehensive caching solution with:
- In-memory caching
- Redis-based caching
- Multiple cache strategies (TTL, LRU, hybrid)
- Tag-based invalidation
- Cache statistics and monitoring
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar

from app.core.logging import StructuredLogger
from app.infrastructure.cache.cache_entry import CacheConfig, CacheEntry, CacheStats, CacheStrategy

logger = StructuredLogger("cache_manager")

T = TypeVar('T')


class CacheManager:
    """
    Manager for caching responses and query results.
    
    Supports:
    - In-memory caching (thread-safe)
    - Time-based expiration (TTL)
    - Size-based eviction (LRU)
    - Tag-based invalidation
    - Cache statistics
    - Background cleanup
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: Dict[str, CacheEntry] = OrderedDict()
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._stats = CacheStats()
        self._running = False
        self._cleanup_thread: Optional[threading.Thread] = None
        
        # For async support
        self._async_lock = asyncio.Lock()
    
    def start(self) -> None:
        """Start the cache manager and background cleanup."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
            logger.info("Cache manager started")
    
    def stop(self) -> None:
        """Stop the cache manager."""
        with self._lock:
            self._running = False
            if self._cleanup_thread:
                self._cleanup_thread.join(timeout=5)
                self._cleanup_thread = None
            logger.info("Cache manager stopped")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (defaults to config.default_ttl)
            tags: List of tags for this cache entry
        """
        with self._lock:
            effective_ttl = ttl if ttl is not None else self.config.default_ttl
            
            # Remove old entry with same key if it exists
            old_entry = self._cache.get(key)
            if old_entry:
                self._remove_entry_from_tag_index(old_entry)
            
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=effective_ttl,
                tags=tags or [],
            )
            
            self._cache[key] = entry
            self._add_entry_to_tag_index(entry)
            
            # Update stats
            self._stats.total_entries = len(self._cache)
            self._stats.total_size += entry.size
            
            logger.debug("Cache set", key=key, ttl=effective_ttl, tags=tags)
    
    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
        
        Returns:
            Tuple of (value, hit) where hit is True if cache hit, False if miss
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats.miss_count += 1
                return None, False
            
            if entry.is_expired():
                self._remove_entry(key)
                self._stats.miss_count += 1
                return None, False
            
            entry.touch()
            self._stats.hit_count += 1
            
            # Move to end for LRU
            self._cache.move_to_end(key)
            
            return entry.value, True
    
    def get_or_set(self, key: str, default_value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> Any:
        """
        Get a value from cache, or set and return default if not found.
        
        Args:
            key: Cache key
            default_value: Default value to set and return if cache miss
            ttl: Time to live in seconds
            tags: List of tags
        
        Returns:
            The cached value or default_value
        """
        value, hit = self.get(key)
        if hit:
            return value
        
        self.set(key, default_value, ttl, tags)
        return default_value
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache entry by key.
        
        Args:
            key: Cache key
        
        Returns:
            True if entry was deleted, False if not found
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache.pop(key)
            self._remove_entry_from_tag_index(entry)
            self._stats.total_entries = len(self._cache)
            self._stats.total_size -= entry.size
            self._stats.eviction_count += 1
            
            logger.debug("Cache delete", key=key)
            return True
    
    def invalidate_by_tag(self, tag: str) -> int:
        """
        Invalidate all cache entries with a specific tag.
        
        Args:
            tag: Tag to invalidate
        
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_delete = list(self._tag_index.get(tag, set()))
            count = 0
            
            for key in keys_to_delete:
                if key in self._cache:
                    entry = self._cache.pop(key)
                    self._remove_entry_from_tag_index(entry)
                    self._stats.total_entries = len(self._cache)
                    self._stats.total_size -= entry.size
                    self._stats.eviction_count += 1
                    count += 1
            
            # Clean up empty tag
            if tag in self._tag_index and not self._tag_index[tag]:
                del self._tag_index[tag]
            
            logger.debug("Cache invalidated by tag", tag=tag, count=count)
            return count
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        Invalidate all cache entries with any of the specified tags.
        
        Args:
            tags: List of tags to invalidate
        
        Returns:
            Number of entries invalidated
        """
        total_invalidated = 0
        for tag in tags:
            total_invalidated += self.invalidate_by_tag(tag)
        return total_invalidated
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._tag_index.clear()
            self._stats = CacheStats()
            logger.info("Cache cleared")
    
    def clear_by_prefix(self, prefix: str) -> int:
        """
        Clear all cache entries with keys starting with the given prefix.
        
        Args:
            prefix: Key prefix to clear
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            count = 0
            
            for key in keys_to_delete:
                entry = self._cache.pop(key)
                self._remove_entry_from_tag_index(entry)
                self._stats.total_entries = len(self._cache)
                self._stats.total_size -= entry.size
                count += 1
            
            logger.debug("Cache cleared by prefix", prefix=prefix, count=count)
            return count
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        with self._lock:
            return key in self._cache and not self._cache[key].is_expired()
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            # Calculate hit rate
            total_requests = self._stats.hit_count + self._stats.miss_count
            hit_rate = self._stats.hit_count / total_requests if total_requests > 0 else 0.0
            
            # Calculate average TTL
            if self._stats.total_entries > 0:
                total_ttl = sum(
                    (entry.expires_at - datetime.utcnow()).total_seconds() 
                    if entry.expires_at else 0
                    for entry in self._cache.values()
                )
                avg_ttl = total_ttl / self._stats.total_entries
            else:
                avg_ttl = 0.0
            
            return CacheStats(
                total_entries=self._stats.total_entries,
                total_size=self._stats.total_size,
                hit_count=self._stats.hit_count,
                miss_count=self._stats.miss_count,
                hit_rate=hit_rate,
                eviction_count=self._stats.eviction_count,
                expiration_count=self._stats.expiration_count,
                average_ttl=avg_ttl,
            )
    
    def get_keys(self) -> List[str]:
        """Get all cache keys."""
        with self._lock:
            return list(self._cache.keys())
    
    def get_keys_by_tag(self, tag: str) -> List[str]:
        """Get all cache keys with a specific tag."""
        with self._lock:
            return list(self._tag_index.get(tag, set()))
    
    def warm_cache(self, data: Dict[str, Any], ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> int:
        """
        Warm the cache with predefined data.
        
        Args:
            data: Dictionary of key-value pairs to cache
            ttl: Time to live in seconds
            tags: List of tags to apply to all entries
        
        Returns:
            Number of entries cached
        """
        count = 0
        for key, value in data.items():
            entry_tags = tags or []
            self.set(key, value, ttl, entry_tags)
            count += 1
        
        logger.info("Cache warmed", count=count)
        return count
    
    def get_config(self) -> CacheConfig:
        """Get cache configuration."""
        return self.config
    
    def _remove_entry(self, key: str) -> bool:
        """Internal method to remove an entry."""
        if key not in self._cache:
            return False
        
        entry = self._cache.pop(key)
        self._remove_entry_from_tag_index(entry)
        self._stats.total_entries = len(self._cache)
        self._stats.total_size -= entry.size
        self._stats.expiration_count += 1
        return True
    
    def _add_entry_to_tag_index(self, entry: CacheEntry) -> None:
        """Add an entry to the tag index."""
        for tag in entry.tags:
            self._tag_index[tag].add(entry.key)
    
    def _remove_entry_from_tag_index(self, entry: CacheEntry) -> None:
        """Remove an entry from the tag index."""
        for tag in entry.tags:
            self._tag_index[tag].discard(entry.key)
            if not self._tag_index[tag]:
                del self._tag_index[tag]
    
    def _evict_lru(self, count: int = 1) -> int:
        """Evict the least recently used entries."""
        with self._lock:
            evicted = 0
            while evicted < count and len(self._cache) > 0:
                # Get the first item (LRU in OrderedDict)
                key, entry = self._cache.popitem(last=False)
                self._remove_entry_from_tag_index(entry)
                self._stats.total_entries = len(self._cache)
                self._stats.total_size -= entry.size
                self._stats.eviction_count += 1
                evicted += 1
                logger.debug("LRU eviction", key=key)
            
            return evicted
    
    def _cleanup_expired(self) -> int:
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
            
            return len(expired_keys)
    
    def _cleanup_by_size(self) -> int:
        """Remove entries to stay within size limit."""
        with self._lock:
            if len(self._cache) <= self.config.max_size:
                return 0
            
            to_evict = len(self._cache) - self.config.max_size
            return self._evict_lru(to_evict)
    
    def _cleanup_by_memory(self) -> int:
        """Remove entries to stay within memory limit."""
        with self._lock:
            if self._stats.total_size <= self.config.max_memory:
                return 0
            
            # Evict LRU until under limit
            while self._stats.total_size > self.config.max_memory and len(self._cache) > 0:
                self._evict_lru(1)
            
            return self._stats.eviction_count
    
    def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self._running:
            try:
                # Sleep for cleanup interval
                time.sleep(self.config.cleanup_interval)
                
                # Perform cleanup
                expired_count = self._cleanup_expired()
                
                if self.config.strategy in [CacheStrategy.SIZE_BASED, CacheStrategy.HYBRID]:
                    size_evicted = self._cleanup_by_size()
                
                if self.config.strategy == CacheStrategy.HYBRID:
                    memory_evicted = self._cleanup_by_memory()
                
                if expired_count > 0 or size_evicted > 0:
                    logger.debug(
                        "Cache cleanup",
                        expired=expired_count,
                        size_evicted=size_evicted,
                        total_entries=len(self._cache),
                    )
            except Exception as e:
                logger.error("Cache cleanup error", error=str(e))
    
    # Async versions of methods
    async def async_set(self, key: str, value: Any, ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> None:
        """Async version of set."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.set, key, value, ttl, tags)
    
    async def async_get(self, key: str) -> Tuple[Optional[Any], bool]:
        """Async version of get."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get, key)
    
    async def async_delete(self, key: str) -> bool:
        """Async version of delete."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.delete, key)
    
    async def async_invalidate_by_tag(self, tag: str) -> int:
        """Async version of invalidate_by_tag."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.invalidate_by_tag, tag)
    
    async def async_clear(self) -> None:
        """Async version of clear."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.clear)
    
    def cached(self, ttl: Optional[int] = None, tags: Optional[List[str]] = None, key_func: Optional[Callable[..., str]] = None):
        """
        Decorator to cache function results.
        
        Args:
            ttl: Time to live in seconds
            tags: List of tags for cache entries
            key_func: Function to generate cache key from function arguments
        
        Returns:
            Decorator function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._generate_cache_key(func, args, kwargs)
                
                # Try to get from cache
                cached_value, hit = self.get(cache_key)
                if hit:
                    return cached_value
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl, tags)
                return result
            
            # Preserve function metadata
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            wrapper.__module__ = func.__module__
            return wrapper
        
        return decorator
    
    def _generate_cache_key(self, func: Callable, args: tuple, kwargs: Dict[str, Any]) -> str:
        """Generate a cache key for a function call."""
        # Create a stable hash of the function name and arguments
        key_parts = [func.__module__, func.__name__]
        
        for arg in args:
            key_parts.append(str(arg))
        
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}={value}")
        
        key_string = "|".join(key_parts)
        return f"func:{hashlib.md5(key_string.encode()).hexdigest()}"


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(config: Optional[CacheConfig] = None) -> CacheManager:
    """Get or create the singleton cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(config)
        _cache_manager.start()
    return _cache_manager


def reset_cache_manager() -> None:
    """Reset the singleton cache manager (useful for testing)."""
    global _cache_manager
    if _cache_manager:
        _cache_manager.stop()
        _cache_manager = None
