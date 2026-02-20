"""
Identity Service for generating ephemeral and long-term device identities.
"""

import os
import uuid
import random
import logging
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from config import CONFIG_DIR

logger = logging.getLogger(__name__)

ADJECTIVES = [
    "Neon", "Cosmic", "Turbo", "Silent", "Electric", "Quantum",
    "Hidden", "Mystic", "Clever", "Swift", "Brave", "Pixel",
    "Sneaky", "Bold", "Lucky", "Happy", "Fierce", "Calm"
]

ANIMALS = [
    "Fox", "Panda", "Gopher", "Bear", "Snail", "Owl",
    "Wolf", "Tiger", "Hawk", "Dolphin", "Penguin", "Falcon",
    "Eagle", "Lion", "Shark", "Whale", "Octopus", "Duck"
]


class IdentityService:
    """Manages the current node's ephemeral identity and long-term signing key."""

    def __init__(self):
        # Ephemeral session ID for the current app run
        self.public_id = str(uuid.uuid4())
        
        # Ephemeral alias
        self.alias = f"{random.choice(ADJECTIVES)} {random.choice(ANIMALS)}"
        
        # Long-term Identity Key (Ed25519)
        self._key_path = CONFIG_DIR / "identity.key"
        self.identity_key = self._load_or_generate_key()
        
        logger.info(f"Initialized IdentityService with alias: {self.alias}")

    def _load_or_generate_key(self) -> ed25519.Ed25519PrivateKey:
        """Loads the existing identity key or creates a new one."""
        if self._key_path.exists():
            try:
                key_bytes = self._key_path.read_bytes()
                return serialization.load_pem_private_key(
                    key_bytes,
                    password=None
                )
            except Exception as e:
                logger.warning(f"Failed to load existing identity key: {e}. Generating new one.")

        # Generate new key
        private_key = ed25519.Ed25519PrivateKey.generate()
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        self._key_path.write_bytes(pem)
        return private_key

    def get_public_bytes(self) -> bytes:
        """Returns the public key as 32-byte raw bytes."""
        return self.identity_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    def sign(self, data: bytes) -> bytes:
        """Sign data using the long-term identity key."""
        return self.identity_key.sign(data)
