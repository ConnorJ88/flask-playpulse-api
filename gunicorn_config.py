# gunicorn_config.py - Save this file in your project root

# Worker settings
workers = 1                    # Reduce to a single worker to avoid memory issues
worker_class = 'sync'          # Use sync worker type
threads = 2                    # Use 2 threads per worker
worker_connections = 100       # Maximum number of connections per worker

# Timeout settings - critical for preventing worker timeouts
timeout = 300                  # Increase timeout to 5 minutes for long-running tasks
graceful_timeout = 30          # Time to finish processing after receiving TERM signal
keepalive = 5                  # Keep connections alive for 5 seconds

# Server settings
bind = '0.0.0.0:10000'         # Bind to all interfaces on port 10000
max_requests = 100             # Restart worker after handling 100 requests
max_requests_jitter = 10       # Add randomness to max_requests
limit_request_line = 4096      # Limit request line size
limit_request_fields = 100     # Limit request headers

# Logging
accesslog = '-'                # Log to stdout
errorlog = '-'                 # Log errors to stdout
loglevel = 'info'              # Set log level
access_log_format = '%({X-Forwarded-For}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Memory optimization
preload_app = False            # Don't preload the app (reduces memory usage)

# Lifecycle hooks - include these to handle memory cleanup
def on_starting(server):
    """Clean up before the server starts."""
    import gc
    gc.collect()
    
def pre_fork(server, worker):
    """Clean up before forking a worker."""
    import gc
    gc.collect()
    
def post_fork(server, worker):
    """Initialize worker with optimized settings."""
    import os
    # Disable matplotlib font cache
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

def worker_abort(worker):
    """Clean up when a worker is aborted."""
    import gc
    gc.collect()