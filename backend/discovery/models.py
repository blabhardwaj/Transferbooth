"""Pydantic models for peer discovery."""

from pydantic import BaseModel


class Peer(BaseModel):
    """Represents a discovered device on the LAN."""
    device_id: str
    device_name: str
    ip_address: str
    api_port: int
    transfer_port: int  # TCP port for file transfer receiver
    platform: str  # "windows" | "darwin" | "linux"
    last_seen: float  # Unix timestamp
    is_trusted: bool = False


class DiscoveryBeacon(BaseModel):
    """The JSON payload broadcast over UDP."""
    app_id: str
    device_id: str
    device_name: str  # Kept for backward compatibility, but might be ephemeral alias
    api_port: int
    transfer_port: int
    platform: str
    alias: str = ""
    public_id: str = ""
    auth_tag: str = ""
