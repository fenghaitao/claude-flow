"""
Test script for SQLite backend implementation.

This script tests the basic functionality of the SQLite backend
to ensure it works correctly with the multi-tier memory system.
"""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from claude_flow.core.config_models import DatabaseConfig
from claude_flow.core.interfaces import MemoryKey, MemoryEntry
from claude_flow.memory.backends.sqlite_backend import SQLiteBackend
from claude_flow.memory.schema import MemorySchemaManager


async def test_sqlite_backend():
    """Test the SQLite backend functionality."""
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_memory.db"
        
        # Configure SQLite backend
        config = DatabaseConfig(
            database_name=str(db_path),
            host="localhost",
            port=5432,
            username="test",
            password="test"
        )
        
        schema_manager = MemorySchemaManager()
        backend = SQLiteBackend(config, schema_manager)
        
        try:
            # Initialize backend
            print("Initializing SQLite backend...")
            await backend.initialize()
            
            # Test data
            key1 = MemoryKey(namespace="test", identifier="item1")
            entry1 = MemoryEntry(
                data={"content": "Test content 1", "type": "text"},
                metadata={"source": "test", "priority": "high"},
                tags={"test", "memory", "content"}
            )
            
            key2 = MemoryKey(namespace="test", identifier="item2") 
            entry2 = MemoryEntry(
                data={"content": "Test content 2", "type": "json"},
                metadata={"source": "test", "priority": "low"},
                tags={"test", "memory", "data"},
                expires_at=datetime.now() + timedelta(hours=1)
            )
            
            # Test storage
            print("Testing storage...")
            success1 = await backend.store(key1, entry1)
            success2 = await backend.store(key2, entry2)
            print(f"Storage results: {success1}, {success2}")
            
            # Test retrieval
            print("Testing retrieval...")
            retrieved1 = await backend.retrieve(key1)
            retrieved2 = await backend.retrieve(key2)
            
            if retrieved1:
                print(f"Retrieved entry 1: {retrieved1.data}")
                print(f"Access count: {retrieved1.access_count}")
            else:
                print("Failed to retrieve entry 1")
            
            if retrieved2:
                print(f"Retrieved entry 2: {retrieved2.data}")
                print(f"Expires at: {retrieved2.expires_at}")
            else:
                print("Failed to retrieve entry 2")
            
            # Test search
            print("Testing search...")
            search_results = await backend.search(
                query="content",
                namespace="test",
                limit=10
            )
            print(f"Search found {len(search_results)} results")
            for key, entry, score in search_results:
                print(f"  {key.to_string()}: {entry.data} (score: {score:.2f})")
            
            # Test listing keys
            print("Testing key listing...")
            keys = await backend.list_keys(namespace="test")
            print(f"Found {len(keys)} keys:")
            for key in keys:
                print(f"  {key.to_string()}")
            
            # Test statistics
            print("Testing statistics...")
            stats = await backend.get_stats()
            print(f"Database stats: {stats}")
            
            # Test health check
            print("Testing health check...")
            health = await backend.health_check()
            print(f"Health status: {health}")
            
            # Test deletion
            print("Testing deletion...")
            deleted = await backend.delete(key1)
            print(f"Deletion result: {deleted}")
            
            # Verify deletion
            retrieved_after_delete = await backend.retrieve(key1)
            print(f"Entry after deletion: {retrieved_after_delete}")
            
            print("All tests completed successfully!")
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            raise
        
        finally:
            # Clean up
            await backend.cleanup()


if __name__ == "__main__":
    asyncio.run(test_sqlite_backend())