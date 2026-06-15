"""
Performance monitoring utilities for HFOrchestra.

This module provides performance monitoring, rate limiting, and optimization
capabilities for the system.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
import statistics


class PerformanceMonitor:
    """Monitors system performance and provides metrics."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_time = datetime.now()
        self.operation_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
    
    def record_operation(self, operation_name: str, duration: float, success: bool = True):
        """Record an operation's performance metrics."""
        self.operation_times[operation_name].append(duration)
        
        if success:
            self.success_counts[operation_name] += 1
        else:
            self.error_counts[operation_name] += 1
        
        # Keep only last 1000 operations to prevent memory bloat
        if len(self.operation_times[operation_name]) > 1000:
            self.operation_times[operation_name] = self.operation_times[operation_name][-1000:]
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        times = self.operation_times.get(operation_name, [])
        if not times:
            return {"error": "No data available"}
        
        return {
            "count": len(times),
            "success_count": self.success_counts.get(operation_name, 0),
            "error_count": self.error_counts.get(operation_name, 0),
            "success_rate": self.success_counts.get(operation_name, 0) / len(times),
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "median_time": statistics.median(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall system performance statistics."""
        all_times = []
        for times in self.operation_times.values():
            all_times.extend(times)
        
        if not all_times:
            return {"error": "No performance data available"}
        
        total_operations = sum(len(times) for times in self.operation_times.values())
        total_success = sum(self.success_counts.values())
        total_errors = sum(self.error_counts.values())
        
        return {
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_operations": total_operations,
            "total_success": total_success,
            "total_errors": total_errors,
            "overall_success_rate": total_success / total_operations if total_operations > 0 else 0,
            "avg_operation_time": statistics.mean(all_times),
            "operations_per_second": total_operations / ((datetime.now() - self.start_time).total_seconds() or 1),
            "operation_types": list(self.operation_times.keys())
        }
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.operation_times.clear()
        self.error_counts.clear()
        self.success_counts.clear()
        self.start_time = datetime.now()


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on performance and errors."""
    
    def __init__(self, initial_rate: int = 10, min_rate: int = 1, max_rate: int = 100):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.request_times = deque(maxlen=100)
        self.error_window = deque(maxlen=50)
        self.success_window = deque(maxlen=50)
        self.last_adjustment = datetime.now()
        self.adjustment_interval = timedelta(seconds=30)
    
    async def acquire(self):
        """Acquire permission to make a request."""
        now = datetime.now()
        
        # Check if we need to wait
        if len(self.request_times) >= self.current_rate:
            oldest_request = self.request_times[0]
            time_since_oldest = (now - oldest_request).total_seconds()
            
            if time_since_oldest < 1.0:  # Within 1 second window
                wait_time = 1.0 - time_since_oldest
                await asyncio.sleep(wait_time)
        
        self.request_times.append(now)
    
    def record_result(self, success: bool, response_time: float):
        """Record the result of a request for adaptive adjustment."""
        if success:
            self.success_window.append((response_time, datetime.now()))
        else:
            self.error_window.append((response_time, datetime.now()))
        
        # Adjust rate if enough time has passed
        if datetime.now() - self.last_adjustment > self.adjustment_interval:
            self._adjust_rate()
    
    def _adjust_rate(self):
        """Adjust the rate based on recent performance."""
        now = datetime.now()
        recent_errors = [e for e in self.error_window if (now - e[1]).total_seconds() < 60]
        recent_successes = [s for s in self.success_window if (now - s[1]).total_seconds() < 60]
        
        error_rate = len(recent_errors) / max(len(recent_errors) + len(recent_successes), 1)
        
        if error_rate > 0.1:  # More than 10% errors
            # Reduce rate
            self.current_rate = max(self.min_rate, int(self.current_rate * 0.8))
        elif error_rate < 0.05 and len(recent_successes) > 10:  # Less than 5% errors and good volume
            # Increase rate
            self.current_rate = min(self.max_rate, int(self.current_rate * 1.1))
        
        self.last_adjustment = now
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        return {
            "current_rate": self.current_rate,
            "min_rate": self.min_rate,
            "max_rate": self.max_rate,
            "recent_requests": len(self.request_times),
            "recent_errors": len(self.error_window),
            "recent_successes": len(self.success_window)
        }


class PerformanceDecorator:
    """Decorator for automatically monitoring function performance."""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: Optional[str] = None):
        self.monitor = monitor
        self.operation_name = operation_name
    
    def __call__(self, func: Callable):
        operation_name = self.operation_name or func.__name__
        
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                self.monitor.record_operation(operation_name, duration, True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                self.monitor.record_operation(operation_name, duration, False)
                raise
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                self.monitor.record_operation(operation_name, duration, True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                self.monitor.record_operation(operation_name, duration, False)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper 