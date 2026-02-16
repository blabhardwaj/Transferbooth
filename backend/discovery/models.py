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


class DiscoveryBeacon(BaseModel):
    """The JSON payload broadcast over UDP."""
    app_id: str
    device_id: str
    device_name: str
    api_port: int
    transfer_port: int
    platform: str
