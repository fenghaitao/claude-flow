"""
Performance and load testing for Claude-Flow system.

Comprehensive testing suite for measuring system performance,
throughput, latency, memory usage, and scalability limits.
"""

import asyncio
import time
import psutil
import pytest
from concurrent.futures import ThreadPoolExecutor
import statistics
from typing import List, Dict, Any, Callable
from unittest.mock import AsyncMock, patch
import gc

from claude_flow.core.system import ClaudeFlowSystem
from claude_flow.agents.orchestrator import AgentOrchestrator
from claude_flow.events.bus import EventBus
from claude_flow.memory.manager import MemoryManager
from claude_flow.claude.client import ClaudeClient


class PerformanceMetrics:
    """Collect and analyze performance metrics."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all metrics."""
        self.response_times = []
        self.throughput_data = []
        self.memory_usage = []
        self.cpu_usage = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = None
        self.end_time = None
    
    def start_measurement(self):
        """Start performance measurement."""
        self.start_time = time.time()
        self.memory_usage.append(psutil.virtual_memory().percent)
        self.cpu_usage.append(psutil.cpu_percent())
    
    def end_measurement(self):
        """End performance measurement."""
        self.end_time = time.time()
        self.memory_usage.append(psutil.virtual_memory().percent)
        self.cpu_usage.append(psutil.cpu_percent())
    
    def record_response_time(self, response_time: float):
        """Record response time for a request."""
        self.response_times.append(response_time)
    
    def record_success(self):
        """Record successful operation."""
        self.success_count += 1
    
    def record_error(self):
        """Record failed operation."""
        self.error_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        total_operations = self.success_count + self.error_count
        
        summary = {
            "total_time_seconds": total_time,
            "total_operations": total_operations,
            "successful_operations": self.success_count,
            "failed_operations": self.error_count,
            "success_rate": self.success_count / max(1, total_operations),
            "throughput_ops_per_second": total_operations / max(0.001, total_time),
        }
        
        if self.response_times:
            summary.update({
                "avg_response_time": statistics.mean(self.response_times),
                "median_response_time": statistics.median(self.response_times),
                "min_response_time": min(self.response_times),
                "max_response_time": max(self.response_times),
                "p95_response_time": self._percentile(self.response_times, 95),
                "p99_response_time": self._percentile(self.response_times, 99)
            })
        
        if self.memory_usage:
            summary.update({
                "avg_memory_usage_percent": statistics.mean(self.memory_usage),
                "max_memory_usage_percent": max(self.memory_usage),
                "memory_delta_percent": self.memory_usage[-1] - self.memory_usage[0]
            })
        
        if self.cpu_usage:
            summary.update({
                "avg_cpu_usage_percent": statistics.mean(self.cpu_usage),
                "max_cpu_usage_percent": max(self.cpu_usage)
            })
        
        return summary
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.fixture
def performance_metrics():
    """Create performance metrics collector."""
    return PerformanceMetrics()


class TestCorePerformance:
    """Test core system component performance."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_event_bus_throughput(self, event_bus, performance_metrics):
        """Test event bus throughput under load."""
        performance_metrics.start_measurement()
        
        # Create handler to process events
        processed_events = []
        
        async def event_handler(event):
            processed_events.append(event)
            performance_metrics.record_success()
        
        # Subscribe to events
        from claude_flow.events.models import EventType
        await event_bus.subscribe(EventType.TASK_CREATED, event_handler)
        
        # Generate high volume of events
        num_events = 1000
        events = []
        
        for i in range(num_events):
            event = {
                "type": EventType.TASK_CREATED,
                "data": {"task_id": f"load_test_{i}", "payload": "x" * 100},  # 100 byte payload
                "source": "load_test"
            }
            events.append(event)
        
        # Publish all events
        start_time = time.time()
        
        for event in events:
            await event_bus.publish(event)
        
        # Wait for all events to be processed
        timeout = 10.0  # 10 second timeout
        elapsed = 0
        while len(processed_events) < num_events and elapsed < timeout:
            await asyncio.sleep(0.1)
            elapsed = time.time() - start_time
        
        performance_metrics.end_measurement()
        
        # Analyze results
        summary = performance_metrics.get_summary()
        
        assert len(processed_events) >= num_events * 0.95  # At least 95% processed
        assert summary["throughput_ops_per_second"] > 100   # At least 100 events/sec
        assert summary["success_rate"] > 0.95               # At least 95% success rate
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_manager_performance(self, memory_manager, performance_metrics):
        """Test memory manager performance under load."""
        performance_metrics.start_measurement()
        
        # Store large number of entries
        num_entries = 500
        entry_size = 1024  # 1KB per entry
        
        for i in range(num_entries):
            start_time = time.time()
            
            try:
                data = {"payload": "x" * entry_size, "index": i, "timestamp": time.time()}
                await memory_manager.store(
                    key=f"perf_test_{i}",
                    data=data,
                    tags=["performance", "test", f"batch_{i // 100}"]
                )
                
                response_time = time.time() - start_time
                performance_metrics.record_response_time(response_time)
                performance_metrics.record_success()
                
            except Exception as e:
                performance_metrics.record_error()
        
        # Test retrieval performance
        retrieval_times = []
        
        for i in range(0, num_entries, 10):  # Sample every 10th entry
            start_time = time.time()
            
            try:
                result = await memory_manager.retrieve(f"perf_test_{i}")
                retrieval_time = time.time() - start_time
                retrieval_times.append(retrieval_time)
                
                assert result is not None
                assert result["index"] == i
                
            except Exception as e:
                performance_metrics.record_error()
        
        # Test search performance
        search_start = time.time()
        search_results = await memory_manager.search("performance test", limit=50)
        search_time = time.time() - search_start
        
        performance_metrics.end_measurement()
        
        # Analyze results
        summary = performance_metrics.get_summary()
        
        assert summary["success_rate"] > 0.95
        assert statistics.mean(retrieval_times) < 0.1  # Under 100ms average retrieval
        assert search_time < 1.0                       # Under 1 second search
        assert len(search_results) > 0
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_claude_client_rate_limiting_performance(self, claude_config, performance_metrics):
        """Test Claude client performance with rate limiting."""
        client = ClaudeClient(claude_config)
        await client.initialize()
        
        try:
            performance_metrics.start_measurement()
            
            # Mock Claude API to return quickly
            with patch.object(client, 'chat') as mock_chat:
                mock_chat.return_value = AsyncMock(
                    content="Test response",
                    usage={'total_tokens': 50},
                    response_time_ms=100
                )
                
                # Test sustained request rate
                num_requests = 100
                requests = []
                
                for i in range(num_requests):
                    start_time = time.time()
                    
                    try:
                        response = await client.chat(
                            messages=f"Test message {i}",
                            max_tokens=50
                        )
                        
                        response_time = time.time() - start_time
                        performance_metrics.record_response_time(response_time)
                        performance_metrics.record_success()
                        
                        assert response.content == "Test response"
                        
                    except Exception as e:
                        performance_metrics.record_error()
            
            performance_metrics.end_measurement()
            
            # Analyze results
            summary = performance_metrics.get_summary()
            
            assert summary["success_rate"] > 0.95
            assert summary["avg_response_time"] < 0.5  # Under 500ms average
            
        finally:
            await client.shutdown()


class TestLoadTesting:
    """Test system behavior under various load conditions."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_agent_orchestration(self, claude_flow_config, performance_metrics):
        """Test agent orchestration under concurrent load."""
        orchestrator = AgentOrchestrator(claude_flow_config)
        await orchestrator.initialize()
        
        try:
            performance_metrics.start_measurement()
            
            # Mock Claude client for consistent responses
            with patch.object(orchestrator.claude_client, 'chat') as mock_chat:
                mock_chat.return_value = AsyncMock(
                    content="Task completed successfully",
                    usage={'total_tokens': 100}
                )
                
                # Create concurrent project requests
                projects = []
                for i in range(20):  # 20 concurrent projects
                    project = {
                        "name": f"Load Test Project {i}",
                        "description": f"Concurrent load testing project {i}",
                        "requirements": [
                            "Design component architecture",
                            "Implement core functionality",
                            "Write unit tests",
                            "Create documentation"
                        ]
                    }
                    projects.append(project)
                
                # Execute all projects concurrently
                start_time = time.time()
                
                results = await asyncio.gather(*[
                    orchestrator.execute_project(project)
                    for project in projects
                ], return_exceptions=True)
                
                total_time = time.time() - start_time
                
                # Analyze results
                successful_results = [r for r in results if not isinstance(r, Exception)]
                failed_results = [r for r in results if isinstance(r, Exception)]
                
                performance_metrics.success_count = len(successful_results)
                performance_metrics.error_count = len(failed_results)
                
            performance_metrics.end_measurement()
            
            summary = performance_metrics.get_summary()
            
            # Verify performance criteria
            assert len(successful_results) >= 18        # At least 90% success
            assert total_time < 30.0                    # Complete within 30 seconds
            assert summary["success_rate"] > 0.90       # 90% success rate
            
        finally:
            await orchestrator.shutdown()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_pressure_scenario(self, claude_flow_config, performance_metrics):
        """Test system behavior under memory pressure."""
        system = ClaudeFlowSystem(claude_flow_config)
        await system.initialize()
        
        try:
            performance_metrics.start_measurement()
            
            # Create memory pressure by storing large objects
            large_objects = []
            memory_threshold = 80  # Stop if memory usage exceeds 80%
            
            for i in range(1000):
                # Check memory usage
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > memory_threshold:
                    break
                
                # Create large data object (1MB)
                large_data = {
                    "id": f"large_object_{i}",
                    "payload": "x" * (1024 * 1024),  # 1MB string
                    "metadata": {"created": time.time(), "size": "1MB"}
                }
                
                start_time = time.time()
                
                try:
                    await system.memory_manager.store(
                        key=f"large_obj_{i}",
                        data=large_data,
                        tags=["large_object", "memory_test"]
                    )
                    
                    response_time = time.time() - start_time
                    performance_metrics.record_response_time(response_time)
                    performance_metrics.record_success()
                    
                    large_objects.append(f"large_obj_{i}")
                    
                except Exception as e:
                    performance_metrics.record_error()
                    break
                
                # Occasional cleanup to test garbage collection
                if i % 100 == 0:
                    gc.collect()
            
            # Test system responsiveness under memory pressure
            responsiveness_test_start = time.time()
            
            simple_task = {
                "description": "Simple task during memory pressure",
                "type": "analysis"
            }
            
            with patch.object(system.claude_client, 'chat') as mock_chat:
                mock_chat.return_value = AsyncMock(
                    content="Analysis complete",
                    usage={'total_tokens': 50}
                )
                
                result = await system.orchestrator.process_simple_task(simple_task)
                responsiveness_time = time.time() - responsiveness_test_start
            
            performance_metrics.end_measurement()
            
            # Analyze results
            summary = performance_metrics.get_summary()
            
            assert summary["success_rate"] > 0.80        # 80% success under pressure
            assert responsiveness_time < 5.0             # System still responsive
            assert len(large_objects) > 10               # Managed to store some large objects
            
        finally:
            await system.shutdown()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, claude_flow_config, performance_metrics):
        """Test sustained throughput over extended period."""
        system = ClaudeFlowSystem(claude_flow_config)
        await system.initialize()
        
        try:
            performance_metrics.start_measurement()
            
            # Mock Claude responses
            with patch.object(system.claude_client, 'chat') as mock_chat:
                mock_chat.return_value = AsyncMock(
                    content="Task processed",
                    usage={'total_tokens': 75}
                )
                
                # Run sustained load for 60 seconds
                test_duration = 60.0  # 60 seconds
                start_time = time.time()
                task_counter = 0
                
                while (time.time() - start_time) < test_duration:
                    batch_start = time.time()
                    
                    # Process batch of tasks
                    batch_size = 10
                    batch_tasks = []
                    
                    for i in range(batch_size):
                        task = {
                            "id": f"sustained_task_{task_counter}_{i}",
                            "description": f"Sustained load task {task_counter}_{i}",
                            "type": "processing"
                        }
                        batch_tasks.append(
                            system.orchestrator.process_simple_task(task)
                        )
                    
                    # Execute batch
                    try:
                        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                        
                        # Record results
                        for result in batch_results:
                            if isinstance(result, Exception):
                                performance_metrics.record_error()
                            else:
                                performance_metrics.record_success()
                        
                        batch_time = time.time() - batch_start
                        performance_metrics.record_response_time(batch_time)
                        
                    except Exception as e:
                        performance_metrics.error_count += batch_size
                    
                    task_counter += 1
                    
                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.1)
            
            performance_metrics.end_measurement()
            
            # Analyze sustained performance
            summary = performance_metrics.get_summary()
            
            assert summary["total_time_seconds"] >= 55.0     # Ran for almost full duration
            assert summary["throughput_ops_per_second"] > 5  # Maintained decent throughput
            assert summary["success_rate"] > 0.85            # 85% success rate
            
        finally:
            await system.shutdown()


class TestScalabilityLimits:
    """Test system scalability and identify limits."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_agent_scaling_limits(self, claude_flow_config, performance_metrics):
        """Test limits of agent scaling."""
        orchestrator = AgentOrchestrator(claude_flow_config)
        await orchestrator.initialize()
        
        try:
            performance_metrics.start_measurement()
            
            # Gradually increase number of concurrent agents
            agent_counts = [5, 10, 20, 50, 100]
            scaling_results = []
            
            for agent_count in agent_counts:
                test_start = time.time()
                
                # Create tasks for agents
                tasks = []
                for i in range(agent_count):
                    task = {
                        "id": f"scaling_task_{agent_count}_{i}",
                        "description": f"Scaling test with {agent_count} agents - task {i}",
                        "type": "concurrent_processing"
                    }
                    tasks.append(task)
                
                # Mock responses
                with patch.object(orchestrator.claude_client, 'chat') as mock_chat:
                    mock_chat.return_value = AsyncMock(
                        content="Scaling test completed",
                        usage={'total_tokens': 60}
                    )
                    
                    # Execute all tasks concurrently
                    try:
                        results = await asyncio.wait_for(
                            asyncio.gather(*[
                                orchestrator.process_simple_task(task)
                                for task in tasks
                            ], return_exceptions=True),
                            timeout=30.0  # 30 second timeout
                        )
                        
                        successful_results = [r for r in results if not isinstance(r, Exception)]
                        test_time = time.time() - test_start
                        
                        scaling_result = {
                            "agent_count": agent_count,
                            "successful_tasks": len(successful_results),
                            "total_tasks": len(tasks),
                            "success_rate": len(successful_results) / len(tasks),
                            "completion_time": test_time,
                            "throughput": len(successful_results) / test_time
                        }
                        
                        scaling_results.append(scaling_result)
                        
                        # Update performance metrics
                        performance_metrics.success_count += len(successful_results)
                        performance_metrics.error_count += (len(tasks) - len(successful_results))
                        
                    except asyncio.TimeoutError:
                        # Record timeout as degraded performance
                        scaling_result = {
                            "agent_count": agent_count,
                            "successful_tasks": 0,
                            "total_tasks": len(tasks),
                            "success_rate": 0.0,
                            "completion_time": 30.0,
                            "throughput": 0.0,
                            "timeout": True
                        }
                        scaling_results.append(scaling_result)
                        performance_metrics.error_count += len(tasks)
                
                # Small delay between scaling tests
                await asyncio.sleep(1.0)
            
            performance_metrics.end_measurement()
            
            # Analyze scaling characteristics
            peak_throughput = max(r["throughput"] for r in scaling_results)
            optimal_agent_count = max(scaling_results, key=lambda x: x["throughput"])["agent_count"]
            
            # Verify scaling behavior
            assert len(scaling_results) == len(agent_counts)
            assert peak_throughput > 0
            assert optimal_agent_count > 0
            
            # At least small scale should work well
            small_scale_results = [r for r in scaling_results if r["agent_count"] <= 20]
            assert all(r["success_rate"] > 0.8 for r in small_scale_results)
            
        finally:
            await orchestrator.shutdown()
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_scalability_limits(self, memory_manager, performance_metrics):
        """Test memory system scalability limits."""
        performance_metrics.start_measurement()
        
        # Test with increasing data sizes
        data_sizes = [1024, 10240, 102400, 1048576]  # 1KB to 1MB
        size_results = []
        
        for data_size in data_sizes:
            size_start = time.time()
            
            # Store multiple entries of this size
            num_entries = min(100, 10485760 // data_size)  # Don't exceed 10MB total
            
            successful_stores = 0
            failed_stores = 0
            
            for i in range(num_entries):
                entry_start = time.time()
                
                try:
                    data = {
                        "payload": "x" * data_size,
                        "size": data_size,
                        "index": i
                    }
                    
                    await memory_manager.store(
                        key=f"size_test_{data_size}_{i}",
                        data=data,
                        tags=["size_test", f"size_{data_size}"]
                    )
                    
                    store_time = time.time() - entry_start
                    performance_metrics.record_response_time(store_time)
                    successful_stores += 1
                    
                except Exception as e:
                    failed_stores += 1
            
            size_time = time.time() - size_start
            
            size_result = {
                "data_size": data_size,
                "num_entries": num_entries,
                "successful_stores": successful_stores,
                "failed_stores": failed_stores,
                "success_rate": successful_stores / num_entries,
                "total_time": size_time,
                "avg_store_time": size_time / num_entries
            }
            
            size_results.append(size_result)
            
            performance_metrics.success_count += successful_stores
            performance_metrics.error_count += failed_stores
        
        performance_metrics.end_measurement()
        
        # Analyze memory scalability
        summary = performance_metrics.get_summary()
        
        # Verify memory can handle different data sizes
        assert all(r["success_rate"] > 0.8 for r in size_results)
        assert summary["success_rate"] > 0.8
        
        # Store time shouldn't increase drastically with size
        small_size_time = next(r["avg_store_time"] for r in size_results if r["data_size"] == 1024)
        large_size_time = next(r["avg_store_time"] for r in size_results if r["data_size"] == 1048576)
        
        # Large entries shouldn't take more than 100x longer (should be much less with good implementation)
        assert large_size_time < small_size_time * 100


@pytest.mark.benchmark
class TestBenchmarks:
    """Benchmark tests for establishing performance baselines."""
    
    @pytest.mark.performance
    def test_event_bus_benchmark(self, benchmark, event_bus):
        """Benchmark event bus publication performance."""
        from claude_flow.events.models import EventType
        
        async def publish_event():
            event = {
                "type": EventType.TASK_CREATED,
                "data": {"benchmark": "test"},
                "source": "benchmark"
            }
            await event_bus.publish(event)
        
        # Benchmark single event publication
        result = benchmark(asyncio.run, publish_event())
        
        # Verify benchmark results are reasonable
        assert result is None  # publish_event returns None
    
    @pytest.mark.performance
    def test_memory_store_benchmark(self, benchmark, memory_manager):
        """Benchmark memory storage performance."""
        
        async def store_entry():
            data = {"benchmark": "test", "payload": "x" * 1024}  # 1KB payload
            await memory_manager.store("benchmark_key", data, ["benchmark"])
        
        # Benchmark single storage operation
        result = benchmark(asyncio.run, store_entry())
        
        assert result is None  # store returns None
    
    @pytest.mark.performance
    def test_config_loading_benchmark(self, benchmark, temp_dir):
        """Benchmark configuration loading performance."""
        from claude_flow.config.manager import ConfigurationManager
        
        # Create test config file
        config_file = temp_dir / "benchmark_config.yaml"
        config_content = {
            "claude": {"api_key": "test"},
            "database": {"sqlite": {"path": "test.db"}},
            "memory": {"max_entries": 1000}
        }
        
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        
        def load_config():
            manager = ConfigurationManager()
            return manager.load_from_file(config_file)
        
        # Benchmark configuration loading
        result = benchmark(load_config)
        
        assert result is not None
        assert result.claude.api_key == "test"