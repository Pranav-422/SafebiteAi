import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = 60
preload_app = True          # run init_db() once before forking workers
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
