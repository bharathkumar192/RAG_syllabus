import logging
import time
from functools import wraps
from flask import request, current_app
from datetime import datetime
import threading
from collections import deque, defaultdict
import psutil
import os

class APIMonitor:
    def __init__(self):
        self.request_times = deque(maxlen=1000)  # Store last 1000 request times
        self.error_counts = defaultdict(int)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'errors': 0
        })
        self.logger = logging.getLogger('api_monitor')

    def monitor_request(self):
        """Decorator for monitoring API requests."""
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                start_time = time.time()
                
                try:
                    response = f(*args, **kwargs)
                    self._record_request(time.time() - start_time, request.endpoint, success=True)
                    return response
                except Exception as e:
                    self._record_request(time.time() - start_time, request.endpoint, success=False)
                    self._record_error(str(e))
                    raise
                
            return wrapped
        return decorator

    def _record_request(self, duration, endpoint, success=True):
        """Record request timing and endpoint statistics."""
        self.request_times.append(duration)
        
        stats = self.endpoint_stats[endpoint]
        stats['count'] += 1
        stats['total_time'] += duration
        if not success:
            stats['errors'] += 1

        # Log slow requests
        if duration > 1.0:  # More than 1 second
            self.logger.warning(f"Slow request to {endpoint}: {duration:.2f}s")

    def _record_error(self, error_type):
        """Record error occurrence."""
        self.error_counts[error_type] += 1
        self.logger.error(f"API Error: {error_type}")

    def get_stats(self):
        """Get current monitoring statistics."""
        if not self.request_times:
            return None

        return {
            'request_stats': {
                'avg_response_time': sum(self.request_times) / len(self.request_times),
                'max_response_time': max(self.request_times),
                'total_requests': len(self.request_times)
            },
            'endpoint_stats': {
                endpoint: {
                    'avg_time': stats['total_time'] / stats['count'],
                    'total_calls': stats['count'],
                    'error_rate': (stats['errors'] / stats['count']) * 100
                }
                for endpoint, stats in self.endpoint_stats.items()
            },
            'error_counts': dict(self.error_counts)
        }

class SystemMonitor:
    def __init__(self):
        self.stats_history = deque(maxlen=60)  # Keep last 60 minutes of data
        self.logger = logging.getLogger('system_monitor')
        self._start_monitoring()

    def _start_monitoring(self):
        """Start background monitoring thread."""
        def monitor_loop():
            while True:
                try:
                    stats = self._collect_system_stats()
                    self.stats_history.append(stats)
                    time.sleep(60)  # Collect stats every minute
                except Exception as e:
                    self.logger.error(f"Error collecting system stats: {str(e)}")

        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

    def _collect_system_stats(self):
        """Collect system performance metrics."""
        return {
            'timestamp': datetime.utcnow(),
            'cpu_percent': psutil.cpu_percent(),
            'memory_usage': dict(psutil.virtual_memory()._asdict()),
            'disk_usage': psutil.disk_usage('/').percent,
            'open_files': len(psutil.Process().open_files()),
            'threads': len(psutil.Process().threads())
        }

    def get_current_stats(self):
        """Get the most recent system statistics."""
        if not self.stats_history:
            return None
        return self.stats_history[-1]

    def get_stats_history(self):
        """Get historical system statistics."""
        return list(self.stats_history)