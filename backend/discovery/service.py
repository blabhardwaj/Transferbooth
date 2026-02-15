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

logger = logging.getLogger(__name__)


class DiscoveryProtocol(asyncio.DatagramProtocol):
    """asyncio UDP protocol for receiving discovery beacons."""

    def __init__(self, service: "DiscoveryService"):
        self.service = service

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            payload = json.loads(data.decode("utf-8"))
            beacon = DiscoveryBeacon(**payload)

            # Ignore our own beacons
            if beacon.device_id == DEVICE_ID:
                return
            if beacon.app_id != APP_ID:
                return

            peer = Peer(
                device_id=beacon.device_id,
                device_name=beacon.device_name,
                ip_address=addr[0],
                api_port=beacon.api_port,
                platform=beacon.platform,
                last_seen=time.time(),
            )
            self.service.update_peer(peer)

        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Ignoring invalid discovery packet from {addr}: {e}")

    def error_received(self, exc: Exception) -> None:
        logger.warning(f"Discovery UDP error: {exc}")


class DiscoveryService:
    """Manages LAN device discovery via UDP broadcast."""

    def __init__(self) -> None:
        self._peers: dict[str, Peer] = {}
        self._lock = asyncio.Lock()
        self._broadcast_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None
        self._transport: asyncio.DatagramTransport | None = None
        self._on_peer_change: list = []  # callbacks: async def fn(event, peer)
        self._device_name = DEVICE_NAME

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

        # Create the UDP listener
        transport, _ = await loop.create_datagram_endpoint(
            lambda: DiscoveryProtocol(self),
            local_addr=("0.0.0.0", DISCOVERY_PORT),
            family=socket.AF_INET,
            allow_broadcast=True,
        )
        self._transport = transport

        # Enable broadcast on the socket
        sock = transport.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

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
        beacon = DiscoveryBeacon(
            app_id=APP_ID,
            device_id=DEVICE_ID,
            device_name=self._device_name,
            api_port=API_PORT,
            platform=PLATFORM,
        )

        while True:
            try:
                # Update device name in case it changed
                beacon.device_name = self._device_name
                data = json.dumps(beacon.model_dump()).encode("utf-8")

                if self._transport:
                    self._transport.sendto(data, ("<broadcast>", DISCOVERY_PORT))

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
