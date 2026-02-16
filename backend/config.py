"""Application-wide configuration constants."""

import os
import platform
import uuid
from pathlib import Path

# --- Identity ---
APP_ID = "transfer-booth-v1"

# Store device ID in a persistent user directory
CONFIG_DIR = Path.home() / ".transferbooth"
CONFIG_DIR.mkdir(exist_ok=True)

_ID_FILE = CONFIG_DIR / "device_id"
if _ID_FILE.exists():
    DEVICE_ID = _ID_FILE.read_text().strip()
else:
    DEVICE_ID = str(uuid.uuid4())
    _ID_FILE.write_text(DEVICE_ID)

DEVICE_NAME = platform.node()
PLATFORM = platform.system().lower()  # "windows" | "darwin" | "linux"

# --- Networking ---
API_HOST = "0.0.0.0"
API_PORT = 8765
DISCOVERY_PORT = 41234  # UDP
DISCOVERY_INTERVAL = 3  # seconds
PEER_TIMEOUT = 10  # seconds

TRANSFER_PORT_MIN = 50000
TRANSFER_PORT_MAX = 65000

# --- Transfer ---
CHUNK_SIZE = 131072  # 128 KB
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# --- Storage ---
DEFAULT_SAVE_DIR = str(Path.home() / "Downloads" / "TransferBooth")
os.makedirs(DEFAULT_SAVE_DIR, exist_ok=True)
