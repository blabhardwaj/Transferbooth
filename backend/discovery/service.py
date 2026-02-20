"""
UDP-based LAN discovery service.

Broadcasts a periodic beacon and listens for beacons from other
Transfer Booth instances on the same LAN.
"""

import asyncio
import json
import logging
import socket
import time

from config import (
    APP_ID,
    API_PORT,
    DEVICE_ID,
    DEVICE_NAME,
    DISCOVERY_INTERVAL,
    DISCOVERY_PORT,
    PEER_TIMEOUT,
    PLATFORM,
)
from discovery.models import DiscoveryBeacon, Peer
from discovery.identity import IdentityService
from discovery.trust import TrustStore

logger = logging.getLogger(__name__)


class DiscoveryProtocol(asyncio.DatagramProtocol):
    """asyncio UDP protocol for receiving discovery beacons."""

    def __init__(self, service: "DiscoveryService"):
        self.service = service

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            payload = json.loads(data.decode("utf-8"))
            beacon = DiscoveryBeacon(**payload)

            # Ignore our own beacons (check both static device_id and ephemeral public_id)
            if beacon.device_id == DEVICE_ID or beacon.public_id == self.service.identity.public_id:
                return
            if beacon.app_id != APP_ID:
                return

            trusted_peer = self.service.trust_store.verify_peer(beacon)
            if trusted_peer:
                resolved_name = trusted_peer.real_name
                peer_device_id = trusted_peer.device_id
                is_trusted = True
                logger.debug(f"`{beacon.alias}` resolved to trusted peer {resolved_name}")
            else:
                resolved_name = beacon.alias or beacon.device_name
                peer_device_id = beacon.public_id or beacon.device_id
                is_trusted = False

            peer = Peer(
                device_id=peer_device_id,
                device_name=resolved_name,
                ip_address=addr[0],
                api_port=beacon.api_port,
                transfer_port=beacon.transfer_port,
                platform=beacon.platform,
                last_seen=time.time(),
                is_trusted=is_trusted,
            )
            self.service.update_peer(peer)

        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Ignoring invalid discovery packet from {addr}: {e}")

    def error_received(self, exc: Exception) -> None:
        logger.warning(f"Discovery UDP error: {exc}")


class DiscoveryService:
    """Manages LAN device discovery via UDP broadcast."""

    def __init__(self, identity, trust_store) -> None:
        self._peers: dict[str, Peer] = {}
        self._lock = asyncio.Lock()
        self._broadcast_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._on_peer_change: list = []  # callbacks: async def fn(event, peer)
        self._device_name = DEVICE_NAME
        self._transfer_port = 0  # Set by main.py after transfer manager starts
        
        self.identity = identity
        self.trust_store = trust_store

    @property
    def transfer_port(self) -> int:
        return self._transfer_port

    @transfer_port.setter
    def transfer_port(self, port: int) -> None:
        self._transfer_port = port

    @property
    def device_name(self) -> str:
        return self._device_name

    @device_name.setter
    def device_name(self, name: str) -> None:
        self._device_name = name

    def on_peer_change(self, callback) -> None:
        """Register a callback for peer discovered/lost events."""
        self._on_peer_change.append(callback)

    async def start(self) -> None:
        """Start the discovery broadcaster and listener."""
        logger.info(f"Starting discovery on UDP port {DISCOVERY_PORT}")

        loop = asyncio.get_running_loop()

        # Create a raw socket with SO_REUSEADDR set BEFORE binding
        # so multiple instances can share the same UDP port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)
        sock.bind(("0.0.0.0", DISCOVERY_PORT))

        # Wrap in asyncio transport
        transport, _ = await loop.create_datagram_endpoint(
            lambda: DiscoveryProtocol(self),
            sock=sock,
        )
        self._transport = transport

        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Discovery service started")

    async def stop(self) -> None:
        """Stop the discovery service."""
        if self._broadcast_task:
            self._broadcast_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._transport:
            self._transport.close()
        logger.info("Discovery service stopped")

    async def get_peers(self) -> list[Peer]:
        """Return a list of currently known peers."""
        async with self._lock:
            return list(self._peers.values())

    def update_peer(self, peer: Peer) -> None:
        """Add or update a peer in the registry."""
        is_new = peer.device_id not in self._peers
        self._peers[peer.device_id] = peer

        if is_new:
            logger.info(f"Discovered peer: {peer.device_name} ({peer.ip_address})")
            for cb in self._on_peer_change:
                asyncio.ensure_future(cb("peer_discovered", peer))

    async def _broadcast_loop(self) -> None:
        """Periodically send a discovery beacon."""
        while True:
            try:
                # Update dynamic fields
                # We send the ephemeral `public_id` and `alias` to hide our real identity.
                # However, we still supply `device_id` as the real DEVICE_ID for backward compatibility 
                # momentarily. Wait, design says NO static tracking! We must mask `device_id`.
                
                beacon = DiscoveryBeacon(
                    app_id=APP_ID,
                    device_id=self.identity.public_id, # Deprecated in favor of public_id but needed for old clients
                    device_name=self.identity.alias,  # Mask real device name
                    api_port=API_PORT,
                    transfer_port=self._transfer_port,
                    platform=PLATFORM,
                    alias=self.identity.alias,
                    public_id=self.identity.public_id,
                    auth_tag="", # Computed next
                )
                
                # Sign the beacon content for friends
                signable_bytes = self.trust_store.get_signable_bytes(beacon)
                beacon.auth_tag = self.identity.sign(signable_bytes).hex()

                data = json.dumps(beacon.model_dump()).encode("utf-8")

                if self._transport:
                    # Collect broadcast addresses
                    bcast_ips = ["<broadcast>", "255.255.255.255", "127.255.255.255"]
                    try:
                        host_name = socket.gethostname()
                        _, _, ips = socket.gethostbyname_ex(host_name)
                        for ip in ips:
                            if not ip.startswith("127."):
                                # Simple heuristic for /24 subnets
                                parts = ip.split(".")
                                if len(parts) == 4:
                                    parts[3] = "255"
                                    bcast_ips.append(".".join(parts))
                    except Exception as e:
                        logger.debug(f"Error resolving local IPs: {e}")

                    # Send to all gathered addresses
                    for bcast_ip in set(bcast_ips):
                        try:
                            self._transport.sendto(data, (bcast_ip, DISCOVERY_PORT))
                        except Exception as inner_e:
                            # Some interfaces might not support broadcast, ignore
                            pass

            except Exception as e:
                logger.warning(f"Broadcast failed: {e}")

            await asyncio.sleep(DISCOVERY_INTERVAL)

    async def _cleanup_loop(self) -> None:
        """Remove stale peers that haven't been seen recently."""
        while True:
            await asyncio.sleep(PEER_TIMEOUT)
            now = time.time()
            stale = []

            async with self._lock:
                for device_id, peer in list(self._peers.items()):
                    if now - peer.last_seen > PEER_TIMEOUT:
                        stale.append(peer)
                        del self._peers[device_id]

            for peer in stale:
                logger.info(f"Peer lost: {peer.device_name} ({peer.ip_address})")
                for cb in self._on_peer_change:
                    asyncio.ensure_future(cb("peer_lost", peer))
