# gunicorn_config.py
timeout = 120  # Increase from default 30 seconds to 120 seconds
workers = 4    # Adjust based on available CPU cores
threads = 2    # Use threads for I/O bound operations
worker_class = 'gthread'  # Good for I/O bound applications