# Gunicorn configuration for SENETRACK (ReportFormv2).
# Run: gunicorn root.wsgi:application -c gunicorn.conf.py
# Or: gunicorn root.wsgi:application -w 4 -b 0.0.0.0:8000

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads = 1
max_requests = 1000
max_requests_jitter = 50
timeout = 60
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Process naming
proc_name = "senetrack"
