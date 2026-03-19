"""Tests for semantic_cache.py"""
import sys
sys.path.insert(0, '/workspace/model-router/src')

from semantic_cache import SemanticCache

def test_cache_basic():
    """Test basic get/set"""
    cache = SemanticCache()
    cache.set("hello", "world")
    assert cache.get("hello") == "world"
    print("✅ test_cache_basic passed")

def test_cache_similarity():
    """Test similarity matching - exact match works"""
    cache = SemanticCache()
    cache.set("hello world", "response1")
    # Exact match should work
    result = cache.get("hello world")
    assert result == "response1"
    print("✅ test_cache_similarity passed")

def test_cache_clear():
    """Test clear"""
    cache = SemanticCache()
    cache.set("test", "value")
    cache.clear()
    assert cache.stats()["size"] == 0
    print("✅ test_cache_clear passed")

def test_cache_stats():
    """Test stats"""
    cache = SemanticCache()
    cache.set("a", "1")
    cache.set("b", "2")
    assert cache.stats()["size"] == 2
    print("✅ test_cache_stats passed")

if __name__ == "__main__":
    test_cache_basic()
    test_cache_similarity()
    test_cache_clear()
    test_cache_stats()
    print("\n✅ All tests passed!")
