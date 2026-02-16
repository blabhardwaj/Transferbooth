"""
Security module: ECDH key exchange + AES-256-GCM encryption.

All keys are ephemeral (per-session) and never persisted.
"""

import os
import logging

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

logger = logging.getLogger(__name__)

# AES-256-GCM nonce size (12 bytes recommended)
NONCE_SIZE = 12
# AES-256 key size
KEY_SIZE = 32


def generate_keypair() -> tuple[X25519PrivateKey, bytes]:
    """
    Generate an ephemeral X25519 keypair.

    Returns:
        (private_key, public_key_bytes) where public_key_bytes
        is 32 bytes suitable for transmission.
    """
    private_key = X25519PrivateKey.generate()
    public_bytes = private_key.public_key().public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw,
    )
    return private_key, public_bytes


def derive_shared_key(
    private_key: X25519PrivateKey,
    peer_public_bytes: bytes,
) -> bytes:
    """
    Derive a 32-byte AES-256 session key from ECDH shared secret.

    Uses HKDF-SHA256 to derive the final key.
    """
    peer_public_key = X25519PublicKey.from_public_bytes(peer_public_bytes)
    shared_secret = private_key.exchange(peer_public_key)

    derived_key = HKDF(
        algorithm=SHA256(),
        length=KEY_SIZE,
        salt=None,
        info=b"transfer-booth-v1-session-key",
    ).derive(shared_secret)

    return derived_key


def encrypt_chunk(key: bytes, plaintext: bytes) -> bytes:
    """
    Encrypt a data chunk using AES-256-GCM.

    Returns: nonce (12 bytes) || ciphertext || tag (16 bytes)
    """
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_chunk(key: bytes, data: bytes) -> bytes:
    """
    Decrypt a data chunk encrypted with AES-256-GCM.

    Expects: nonce (12 bytes) || ciphertext || tag (16 bytes)
    """
    nonce = data[:NONCE_SIZE]
    ciphertext = data[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
