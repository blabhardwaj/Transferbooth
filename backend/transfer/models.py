"""Pydantic models for file transfer."""

from enum import Enum
from pydantic import BaseModel


class TransferState(str, Enum):
    """All possible states for a file transfer."""
    PENDING = "pending"
    AWAITING_ACCEPTANCE = "awaiting_acceptance"
    REJECTED = "rejected"
    CONNECTING = "connecting"
    TRANSFERRING = "transferring"
    PAUSED = "paused"
    PAUSED_BY_PEER = "paused_by_peer"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransferDirection(str, Enum):
    SENDING = "sending"
    RECEIVING = "receiving"


class TransferInfo(BaseModel):
    """Full state of a single file transfer, exposed to the frontend."""
    transfer_id: str
    file_name: str
    file_size: int
    transferred_bytes: int = 0
    state: TransferState = TransferState.PENDING
    direction: TransferDirection
    peer_device_id: str
    peer_device_name: str
    speed_bps: float = 0.0
    progress_percent: float = 0.0
    eta_seconds: float = 0.0
    error_message: str | None = None


class TransferRequest(BaseModel):
    """API body for initiating a transfer."""
    peer_id: str
    file_paths: list[str]


# --- Wire protocol message types ---

class MessageType:
    HANDSHAKE_PUBKEY = 0x01
    METADATA = 0x02
    ACCEPT = 0x03
    REJECT = 0x04
    RESUME_OFFSET = 0x05
    DATA_CHUNK = 0x06
    PAUSE = 0x07
    RESUME = 0x08
    CANCEL = 0x09
    TRANSFER_COMPLETE = 0x0A


class FileMetadata(BaseModel):
    """Metadata sent before file data."""
    transfer_id: str
    file_name: str
    file_size: int
    sender_device_id: str
    sender_device_name: str
    identity_public_key: str = ""
    identity_signature: str = ""
