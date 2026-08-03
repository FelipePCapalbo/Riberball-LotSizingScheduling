import os
import socket

from dotenv import load_dotenv

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, 'backend', '.env'))

WORKER_BASE_URL = os.environ.get(
    'WORKER_BASE_URL', 'https://riberball-lotsizingscheduling.felipecapalbo.workers.dev'
).rstrip('/')
SHARED_SECRET = os.environ.get('SHARED_SECRET', '')
MACHINE_LABEL = os.environ.get('MACHINE_LABEL') or socket.gethostname()
TUNNEL_ENABLED = os.environ.get('TUNNEL_ENABLED', 'true').strip().lower() == 'true'
HEARTBEAT_INTERVAL_SECONDS = float(os.environ.get('HEARTBEAT_INTERVAL_SECONDS', '15'))
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', '8000'))
