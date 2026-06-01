from honeypot.db import init_db
from honeypot.ssh_server import start_server
from honeypot.worker import start as start_worker
import logging

logging.getLogger("paramiko").setLevel(logging.CRITICAL) # suppress paramiko logs
logging.getLogger("paramiko.transport").setLevel(logging.CRITICAL)

if __name__ == "__main__":
    init_db()
    start_worker()
    start_server(host="0.0.0.0", port=2222)