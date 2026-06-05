"""
Unit tests for Cache Manager.
"""
from __future__ import annotations

import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.infrastructure.cache import (
    CacheManager,
    CacheConfig,
    CacheEntry,
    CacheStats,
    CacheStrategy,
    get_cache_manager,
    reset_cache_manager,
)


class TestCacheEntry(unittest.TestCase):
    """Tests for CacheEntry dataclass."""
    
    def test_default_ttl(self):
        """Test that default TTL is used."""
        entry = CacheEntry(key="test", value="value")
        
        self.assertEqual(entry.ttl, 300)
        self.assertIsNotNone(entry.expires_at)
        self.assertEqual(entry.hit_count, 0)
        self.assertEqual(entry.size, len("value"))
    
    def test_custom_ttl(self):
        """Test custom TTL."""
        entry = CacheEntry(key="test", value="value", ttl=60)
        
        self.assertEqual(entry.ttl, 60)
    
    def test_is_expired(self):
        """Test expiration check."""
        # Entry that expires in 1 second
        entry = CacheEntry(key="test", value="value", ttl=1)
        
        self.assertFalse(entry.is_expired())
        
        # Wait for expiration
        time.sleep(1.1)
        
        self.assertTrue(entry.is_expired())
    
    def test_is_not_expired_with_zero_ttl(self):
        """Test that entries with TTL=0 never expire."""
        entry = CacheEntry(key="test", value="value", ttl=0)
        
        self.assertFalse(entry.is_expired())
    
    def test_touch(self):
        """Test touching an entry."""
        entry = CacheEntry(key="test", value="value")
        original_accessed = entry.accessed_at
        original_hit_count = entry.hit_count
        
        time.sleep(0.01)  # Small delay
        entry.touch()
        
        self.assertGreater(entry.accessed_at, original_accessed)
        self.assertEqual(entry.hit_count, original_hit_count + 1)
    
    def test_to_dict(self):
        """Test to_dict method."""
        entry = CacheEntry(
            key="test",
            value="value",
            ttl=60,
            tags=["tag1", "tag2"],
        )
        
        result = entry.to_dict()
        
        self.assertEqual(result["key"], "test")
        self.assertEqual(result["value"], "value")
        self.assertEqual(result["ttl"], 60)
        self.assertEqual(result["tags"], ["tag1", "tag2"])
        self.assertEqual(result["hit_count"], 0)
        self.assertIn("created_at", result)
        self.assertIn("accessed_at", result)


class TestCacheStats(unittest.TestCase):
    """Tests for CacheStats dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        stats = CacheStats()
        
        self.assertEqual(stats.total_entries, 0)
        self.assertEqual(stats.total_size, 0)
        self.assertEqual(stats.hit_count, 0)
        self.assertEqual(stats.miss_count, 0)
        self.assertEqual(stats.hit_rate, 0.0)
        self.assertEqual(stats.eviction_count, 0)
        self.assertEqual(stats.expiration_count, 0)
    
    def test_to_dict(self):
        """Test to_dict method."""
        stats = CacheStats(
            total_entries=10,
            total_size=1024,
            hit_count=8,
            miss_count=2,
            hit_rate=0.8,
            eviction_count=1,
            expiration_count=2,
            average_ttl=30.5,
        )
        
        result = stats.to_dict()
        
        self.assertEqual(result["total_entries"], 10)
        self.assertEqual(result["total_size"], 1024)
        self.assertEqual(result["hit_count"], 8)
        self.assertEqual(result["miss_count"], 2)
        self.assertEqual(result["hit_rate"], 0.8)


class TestCacheConfig(unittest.TestCase):
    """Tests for CacheConfig dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        config = CacheConfig()
        
        self.assertEqual(config.default_ttl, 300)
        self.assertEqual(config.max_size, 10000)
        self.assertEqual(config.max_memory, 1024 * 1024 * 100)
        self.assertEqual(config.strategy, CacheStrategy.HYBRID)
        self.assertEqual(config.cleanup_interval, 60)
    
    def test_custom_values(self):
        """Test custom values."""
        config = CacheConfig(
            default_ttl=60,
            max_size=100,
            max_memory=1024 * 1024,
            strategy=CacheStrategy.TIME_BASED,
            cleanup_interval=30,
        )
        
        self.assertEqual(config.default_ttl, 60)
        self.assertEqual(config.max_size, 100)
        self.assertEqual(config.max_memory, 1024 * 1024)
        self.assertEqual(config.strategy, CacheStrategy.TIME_BASED)
        self.assertEqual(config.cleanup_interval, 30)


class TestCacheManager(unittest.TestCase):
    """Tests for CacheManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = CacheConfig(
            default_ttl=1,
            max_size=10,
            max_memory=1024 * 1024,
            cleanup_interval=0.1,
        )
        self.cache_manager = CacheManager(self.config)
        self.cache_manager.start()
    
    def tearDown(self):
        """Clean up after tests."""
        self.cache_manager.stop()
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        self.cache_manager.set("key1", "value1")
        
        value, hit = self.cache_manager.get("key1")
        
        self.assertTrue(hit)
        self.assertEqual(value, "value1")
    
    def test_get_nonexistent(self):
        """Test getting a non-existent key."""
        value, hit = self.cache_manager.get("nonexistent")
        
        self.assertFalse(hit)
        self.assertIsNone(value)
    
    def test_get_expired(self):
        """Test getting an expired key."""
        self.cache_manager.set("key1", "value1", ttl=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        value, hit = self.cache_manager.get("key1")
        
        self.assertFalse(hit)
        self.assertIsNone(value)
    
    def test_delete(self):
        """Test deleting a key."""
        self.cache_manager.set("key1", "value1")
        
        result = self.cache_manager.delete("key1")
        
        self.assertTrue(result)
        
        value, hit = self.cache_manager.get("key1")
        self.assertFalse(hit)
    
    def test_delete_nonexistent(self):
        """Test deleting a non-existent key."""
        result = self.cache_manager.delete("nonexistent")
        
        self.assertFalse(result)
    
    def test_clear(self):
        """Test clearing the cache."""
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        
        self.cache_manager.clear()
        
        self.assertEqual(len(self.cache_manager.get_keys()), 0)
    
    def test_clear_by_prefix(self):
        """Test clearing by prefix."""
        self.cache_manager.set("user:1:data", "value1")
        self.cache_manager.set("user:2:data", "value2")
        self.cache_manager.set("app:1:data", "value3")
        
        count = self.cache_manager.clear_by_prefix("user:")
        
        self.assertEqual(count, 2)
        
        keys = self.cache_manager.get_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0], "app:1:data")
    
    def test_exists(self):
        """Test exists check."""
        self.cache_manager.set("key1", "value1")
        
        self.assertTrue(self.cache_manager.exists("key1"))
        self.assertFalse(self.cache_manager.exists("nonexistent"))
    
    def test_get_or_set(self):
        """Test get_or_set method."""
        # First call should set and return default
        value1 = self.cache_manager.get_or_set("key1", "default_value")
        self.assertEqual(value1, "default_value")
        
        # Second call should return cached value
        value2 = self.cache_manager.get_or_set("key1", "different_value")
        self.assertEqual(value2, "default_value")
    
    def test_tags(self):
        """Test tag-based operations."""
        self.cache_manager.set("key1", "value1", tags=["user", "admin"])
        self.cache_manager.set("key2", "value2", tags=["user"])
        self.cache_manager.set("key3", "value3", tags=["admin"])
        
        # Get keys by tag
        user_keys = self.cache_manager.get_keys_by_tag("user")
        self.assertEqual(len(user_keys), 2)
        self.assertIn("key1", user_keys)
        self.assertIn("key2", user_keys)
        
        # Invalidate by tag
        count = self.cache_manager.invalidate_by_tag("user")
        self.assertEqual(count, 2)
        
        # Verify invalidation
        self.assertFalse(self.cache_manager.exists("key1"))
        self.assertFalse(self.cache_manager.exists("key2"))
        self.assertTrue(self.cache_manager.exists("key3"))
    
    def test_invalidate_by_tags(self):
        """Test invalidating by multiple tags."""
        self.cache_manager.set("key1", "value1", tags=["user", "admin"])
        self.cache_manager.set("key2", "value2", tags=["user"])
        self.cache_manager.set("key3", "value3", tags=["admin"])
        
        count = self.cache_manager.invalidate_by_tags(["user", "admin"])
        
        self.assertEqual(count, 3)
        self.assertEqual(len(self.cache_manager.get_keys()), 0)
    
    def test_warm_cache(self):
        """Test warming the cache."""
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        
        count = self.cache_manager.warm_cache(data, tags=["warmed"])
        
        self.assertEqual(count, 3)
        
        for key, value in data.items():
            cached_value, hit = self.cache_manager.get(key)
            self.assertTrue(hit)
            self.assertEqual(cached_value, value)
    
    def test_get_stats(self):
        """Test getting cache statistics."""
        self.cache_manager.set("key1", "value1", ttl=60)
        self.cache_manager.set("key2", "value2", ttl=60)
        
        # Generate some hits and misses
        self.cache_manager.get("key1")  # hit
        self.cache_manager.get("key2")  # hit
        self.cache_manager.get("nonexistent")  # miss
        
        stats = self.cache_manager.get_stats()
        
        self.assertEqual(stats.total_entries, 2)
        self.assertEqual(stats.hit_count, 2)
        self.assertEqual(stats.miss_count, 1)
        self.assertGreater(stats.hit_rate, 0)
    
    def test_get_config(self):
        """Test getting cache configuration."""
        config = self.cache_manager.get_config()
        
        self.assertEqual(config.default_ttl, self.config.default_ttl)
        self.assertEqual(config.max_size, self.config.max_size)
        self.assertEqual(config.strategy, self.config.strategy)
    
    def test_lru_eviction(self):
        """Test LRU eviction when size limit is reached."""
        config = CacheConfig(
            default_ttl=300,
            max_size=3,
            strategy=CacheStrategy.SIZE_BASED,
        )
        cache_manager = CacheManager(config)
        cache_manager.start()
        
        # Add 3 entries
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        cache_manager.set("key3", "value3")
        
        # Access key1 to make it most recently used
        cache_manager.get("key1")
        
        # Add a 4th entry, should evict key2 (least recently used)
        cache_manager.set("key4", "value4")
        
        # key2 should be evicted
        self.assertFalse(cache_manager.exists("key2"))
        self.assertTrue(cache_manager.exists("key1"))
        self.assertTrue(cache_manager.exists("key3"))
        self.assertTrue(cache_manager.exists("key4"))
        
        cache_manager.stop()
    
    def test_cached_decorator(self):
        """Test the cached decorator."""
        call_count = 0
        
        @self.cache_manager.cached(ttl=10)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call should execute function
        result1 = expensive_function(1, 2)
        self.assertEqual(result1, 3)
        self.assertEqual(call_count, 1)
        
        # Second call with same arguments should use cache
        result2 = expensive_function(1, 2)
        self.assertEqual(result2, 3)
        self.assertEqual(call_count, 1)  # Still 1, function not called again
        
        # Different arguments should call function
        result3 = expensive_function(3, 4)
        self.assertEqual(result3, 7)
        self.assertEqual(call_count, 2)


class TestSingletonFunctions(unittest.TestCase):
    """Tests for singleton functions."""
    
    def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns the same instance."""
        reset_cache_manager()
        
        manager1 = get_cache_manager()
        manager2 = get_cache_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_reset_cache_manager(self):
        """Test resetting the cache manager."""
        manager1 = get_cache_manager()
        reset_cache_manager()
        manager2 = get_cache_manager()
        
        self.assertIsNot(manager1, manager2)


class TestCacheStrategy(unittest.TestCase):
    """Tests for CacheStrategy enum."""
    
    def test_enum_values(self):
        """Test that enum values are correct."""
        self.assertEqual(CacheStrategy.TIME_BASED.value, "time_based")
        self.assertEqual(CacheStrategy.SIZE_BASED.value, "size_based")
        self.assertEqual(CacheStrategy.MANUAL.value, "manual")
        self.assertEqual(CacheStrategy.HYBRID.value, "hybrid")


if __name__ == "__main__":
    unittest.main()
