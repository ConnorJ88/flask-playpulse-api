# gunicorn_config.py
timeout = 120  # Extend worker timeout to 120 seconds
workers = 3    # Use 3 worker processes
threads = 2    # Use 2 threads per worker
worker_class = 'gthread'  # Use threaded worker mode
max_requests = 1000  # Restart workers after 1000 requests to prevent memory leaks
max_requests_jitter = 50  # Add jitter to prevent all workers restarting simultaneously