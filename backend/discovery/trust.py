"""Trust store for managing previously verified peers' public keys."""

import json
import logging
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from pydantic import BaseModel

from config import CONFIG_DIR
from discovery.models import DiscoveryBeacon

logger = logging.getLogger(__name__)


class TrustedPeer(BaseModel):
    """A peer that has been verified in a previous transfer."""
    device_id: str
    real_name: str
    public_key_hex: str


class TrustStore:
    """Persists and resolves trusted peers using Ed25519 signatures."""

    def __init__(self):
        self._store_path = CONFIG_DIR / "trusted_peers.json"
        self._peers: dict[str, TrustedPeer] = {}
        self._load()

    def _load(self) -> None:
        if not self._store_path.exists():
            return
        
        try:
            data = json.loads(self._store_path.read_text())
            for device_id, peer_data in data.items():
                self._peers[device_id] = TrustedPeer(**peer_data)
            logger.info(f"Loaded {len(self._peers)} trusted peers.")
        except Exception as e:
            logger.error(f"Failed to load trusted peers: {e}")

    def _save(self) -> None:
        try:
            data = {
                device_id: peer.model_dump()
                for device_id, peer in self._peers.items()
            }
            self._store_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save trusted peers: {e}")

    def add_trusted_peer(self, device_id: str, real_name: str, public_key_hex: str) -> None:
        """Add a newly verified peer after a successful transfer."""
        peer = TrustedPeer(
            device_id=device_id,
            real_name=real_name,
            public_key_hex=public_key_hex
        )
        self._peers[device_id] = peer
        logger.info(f"Added trusted peer: {real_name} ({device_id})")

    def get_peer_by_key(self, public_key_hex: str) -> Optional[TrustedPeer]:
        """Look up a known peer by their exact public key."""
        for peer in self._peers.values():
            if peer.public_key_hex == public_key_hex:
                return peer
        return None

    @staticmethod
    def get_signable_bytes(beacon: DiscoveryBeacon) -> bytes:
        """Generate the canonical byte string to sign for a beacon."""
        # We sign the ephemeral parts so they cannot be spoofed/replayed easily.
        payload = f"{beacon.app_id}:{beacon.public_id}:{beacon.alias}:{beacon.api_port}:{beacon.transfer_port}"
        return payload.encode("utf-8")

    def verify_peer(self, beacon: DiscoveryBeacon) -> Optional[TrustedPeer]:
        """
        Attempt to verify a beacon's auth_tag against all trusted peers.
        If a match is found, returns the TrustedPeer.
        """
        if not beacon.auth_tag:
            return None

        try:
            signature = bytes.fromhex(beacon.auth_tag)
        except ValueError:
            return None

        signable_bytes = self.get_signable_bytes(beacon)

        for peer in self._peers.values():
            try:
                pub_key_bytes = bytes.fromhex(peer.public_key_hex)
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)
                pub_key.verify(signature, signable_bytes)
                return peer  # Verification succeeded!
            except (ValueError, InvalidSignature):
                continue

        return None
