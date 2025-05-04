timeout = 120  # Increase worker timeout to 120 seconds
workers = 3    # Use 3 worker processes
threads = 2    # Use 2 threads per worker
worker_class = 'gthread'  # Use threaded worker mode
max_requests = 1000  # Restart workers after 1000 requests
max_requests_jitter = 50  # Add jitter to prevent all workers restarting at once