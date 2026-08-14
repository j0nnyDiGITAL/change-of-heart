"""
Cryptographic Container Manager for Persona 5 Royal (P5R) Save Files
Handles AES-256-CBC encryption/decryption, zlib compression, and CRC validation.
"""

import base64
import secrets
import struct
import zlib
from typing import Tuple, Optional

from .crc import calc_crc

# Fallback crypto imports
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    HAS_PYCRYPTODOME = True
except ImportError:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        HAS_PYCRYPTODOME = False
        HAS_CRYPTOGRAPHY = True
    except ImportError:
        HAS_PYCRYPTODOME = False
        HAS_CRYPTOGRAPHY = False

# Hardcoded Atlus PC AES-256-CBC key
P5R_CRYPT_KEY_B64 = b"3lOZS0kYSoOOtkC4c7IDfvNXnxIprUPTlUGVC3yBJF0="
P5R_CRYPT_KEY = base64.b64decode(P5R_CRYPT_KEY_B64)  # Exactly 32 bytes (256 bits)


def align_offset(offset: int, alignment: int = 16) -> int:
    """Align offset to nearest multiple of alignment."""
    return (offset + (alignment - 1)) & ~(alignment - 1)


def aes_decrypt(ciphertext: bytes, iv: bytes, key: bytes = P5R_CRYPT_KEY) -> bytes:
    """Decrypt buffer using AES-256-CBC."""
    if HAS_PYCRYPTODOME:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(ciphertext)
    elif HAS_CRYPTOGRAPHY:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
    else:
        raise RuntimeError("Missing AES library. Install pycryptodome (`pip install pycryptodome`) or cryptography.")


def aes_encrypt(plaintext: bytes, iv: bytes, key: bytes = P5R_CRYPT_KEY) -> bytes:
    """Encrypt buffer using AES-256-CBC with 16-byte PKCS#7 / zero padding."""
    pad_len = 16 - (len(plaintext) % 16)
    if pad_len != 16:
        plaintext += b"\x00" * pad_len

    if HAS_PYCRYPTODOME:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.encrypt(plaintext)
    elif HAS_CRYPTOGRAPHY:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()
    else:
        raise RuntimeError("Missing AES library. Install pycryptodome (`pip install pycryptodome`) or cryptography.")


class SaveContainer:
    """
    Represents the binary container layer of a P5R PC save file.
    Magic: 'DATA' (4 bytes)
    File CRC: u32
    Timestamp: u32
    Flags: u32 (Bit 31 set if AES encrypted)
    IV: 16 bytes
    Header/Data block sizes, flags, and inner CRC
    """

    def __init__(self):
        self.file_magic = b"DATA"
        self.file_crc = 0
        self.file_timestamp = 0
        self.file_flags = 0x80000000  # Default: AES encrypted flag set
        self.file_iv = b"\x00" * 16

        self.header_size = 0x1D0
        self.header_size_comp = 0
        self.data_size = 0x30720
        self.data_size_comp = 0
        self.save_flags = 0x02110600

        self.data_crc = 0

        self.header_bytes = b""
        self.data_bytes = b""

    def unpack_raw(self, buffer: bytes) -> bool:
        """Unpack, decrypt, and decompress raw save bytes."""
        if len(buffer) < 0x34:
            raise ValueError("Save file buffer too small (< 0x34 bytes)")

        self.file_magic, self.file_crc, self.file_timestamp, self.file_flags = struct.unpack("<4s3I", buffer[:0x10])
        self.file_iv = buffer[0x10:0x20]

        if self.file_magic != b"DATA":
            raise ValueError(f"Invalid save magic header: {self.file_magic} (expected b'DATA')")

        # Validate outer file CRC
        computed_file_crc = calc_crc(buffer[0x8:])
        if computed_file_crc != self.file_crc:
            print(f"[Warning] File CRC mismatch: Header 0x{self.file_crc:08X} vs Calculated 0x{computed_file_crc:08X}")

        buffer_dec = buffer
        if self.file_flags & (1 << 31):
            encrypted_payload = buffer[0x20:]
            decrypted_payload = aes_decrypt(encrypted_payload, self.file_iv)
            buffer_dec = buffer[:0x20] + decrypted_payload

        (
            self.header_size,
            self.header_size_comp,
            self.data_size,
            self.data_size_comp,
            self.save_flags,
            self.data_crc,
        ) = struct.unpack("<HHIIII", buffer_dec[0x20:0x34])

        # Header extraction
        if self.save_flags & 1:
            raw_header = buffer_dec[0x40:self.header_size_comp]
            self.header_bytes = zlib.decompress(raw_header)
            data_offset = self.header_size_comp
        else:
            self.header_bytes = buffer_dec[0x40:self.header_size]
            data_offset = self.header_size

        data_offset = align_offset(data_offset, 16)

        # Data block extraction
        if self.save_flags & 2:
            raw_data = buffer_dec[data_offset:data_offset + self.data_size_comp]
            self.data_bytes = zlib.decompress(raw_data)
        else:
            self.data_bytes = buffer_dec[data_offset:data_offset + self.data_size]

        # Inner Data CRC Check
        computed_data_crc = calc_crc(self.data_bytes)
        if computed_data_crc != self.data_crc:
            print(f"[Warning] Inner Data CRC mismatch: Header 0x{self.data_crc:08X} vs Calculated 0x{computed_data_crc:08X}")

        return True

    def pack_raw(self, compress: bool = True, encrypt: bool = True) -> bytes:
        """Pack, compress, encrypt, and resign save file bytes."""
        if not self.data_bytes:
            raise ValueError("Cannot pack save container with empty data_bytes")

        # 1. Compute Inner Data CRC
        self.data_crc = calc_crc(self.data_bytes)

        # 2. Header processing & zlib compression
        header_payload = self.header_bytes
        self.header_size = 0x40 + len(header_payload)
        self.header_size_comp = 0
        hs = self.header_size

        save_flags = self.save_flags
        if compress:
            compressed_header = zlib.compress(header_payload, 9)
            save_flags |= 1
            self.header_size_comp = 0x40 + len(compressed_header)
            hs = self.header_size_comp
            header_payload = compressed_header
        else:
            save_flags &= ~1

        # 3. Data processing & zlib compression
        data_payload = self.data_bytes
        self.data_size = len(data_payload)
        self.data_size_comp = 0
        ds = self.data_size

        if compress:
            compressed_data = zlib.compress(data_payload, 9)
            save_flags |= 2
            self.data_size_comp = len(compressed_data)
            ds = self.data_size_comp
            data_payload = compressed_data
        else:
            save_flags &= ~2

        # 4. Construct unencrypted payload buffer
        meta_block = struct.pack(
            "<HHIIII 12x",
            self.header_size,
            self.header_size_comp,
            self.data_size,
            self.data_size_comp,
            save_flags,
            self.data_crc,
        )

        header_aligned_len = align_offset(hs, 16) - 0x40
        data_aligned_len = align_offset(ds, 16)

        unencrypted_body = meta_block + header_payload.ljust(header_aligned_len, b"\x00") + data_payload.ljust(data_aligned_len, b"\x00")

        # 5. Encryption & IV generation
        flags = self.file_flags
        iv = b"\x00" * 16
        if encrypt:
            flags |= 1 << 31
            iv = secrets.token_bytes(16)
            encrypted_body = aes_encrypt(unencrypted_body, iv)
        else:
            flags &= ~(1 << 31)
            encrypted_body = unencrypted_body

        timestamp = self.file_timestamp if self.file_timestamp > 0 else 1700000000
        header_block = struct.pack("<II16s", timestamp, flags, iv)

        # 6. Compute Outer File CRC
        full_payload_for_crc = header_block + encrypted_body
        self.file_crc = calc_crc(full_payload_for_crc)

        return struct.pack("<4sI", self.file_magic, self.file_crc) + full_payload_for_crc
