import os


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
COUNTER_KEY_PREFIX = "blueocean:counter"
