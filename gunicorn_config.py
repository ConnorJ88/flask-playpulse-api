bind = "0.0.0.0:$PORT"  # Use PORT environment variable
workers = 4             # Number of worker processes
threads = 2             # Threads per worker
worker_class = "gthread"  # Use threaded worker mode
timeout = 120           # Increase worker timeout to 120 seconds
max_requests = 1000     # Restart workers after 1000 requests
max_requests_jitter = 50  # Add jitter to prevent all workers restarting at once