"""Application-wide configuration constants."""

import os
import platform
import uuid
from pathlib import Path

# --- Identity ---
APP_ID = "transfer-booth-v1"
# Generate a persistent device ID (stored in a local file)
_ID_FILE = Path(__file__).parent / ".device_id"
if _ID_FILE.exists():
    DEVICE_ID = _ID_FILE.read_text().strip()
else:
    DEVICE_ID = str(uuid.uuid4())
    _ID_FILE.write_text(DEVICE_ID)

DEVICE_NAME = platform.node()  # default to hostname, user can override
PLATFORM = platform.system().lower()  # "windows" | "darwin" | "linux"

# --- Networking ---
API_HOST = "0.0.0.0"
API_PORT = 8765
DISCOVERY_PORT = 41234  # UDP
DISCOVERY_INTERVAL = 3  # seconds
PEER_TIMEOUT = 10  # seconds before a peer is considered offline

TRANSFER_PORT_MIN = 50000
TRANSFER_PORT_MAX = 65000

# --- Transfer ---
CHUNK_SIZE = 131072  # 128 KB
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# --- Storage ---
DEFAULT_SAVE_DIR = str(
    Path.home() / "Downloads" / "TransferBooth"
)
os.makedirs(DEFAULT_SAVE_DIR, exist_ok=True)
