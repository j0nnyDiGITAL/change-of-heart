"""
Binary Struct Parser for Persona 5 Royal (P5R) Save Data Headers and Blocks
"""

import struct
from typing import Dict, Any, Optional, List, Tuple


def pack_fixed_string(text: str, length: int, encoding: str = "utf-8") -> bytes:
    """Encode string and pad with null bytes to fixed byte length."""
    encoded = text.encode(encoding, errors="ignore")[:length]
    return encoded.ljust(length, b"\x00")


class SaveHeader:
    """Represents uncompressed 0x190 header block."""

    def __init__(self):
        self.playtime: int = 0  # In seconds
        self.day: int = 0       # Calendar day index
        self.time: int = 0      # Time of day (0=Morning, 1=After School, 2=Evening, etc.)
        self.playthrough: int = 1
        self.difficulty: int = 2  # 0=Safety, 1=Easy, 2=Normal, 3=Hard, 4=Merciless
        self.level: int = 1
        self.clear: int = 0
        self.fld_major: int = 0
        self.fld_minor: int = 0
        self.lang0: int = 0xFF
        self.lang1: int = 0
        self.lname: str = "Amamiya"
        self.fname: str = "Ren"
        self.desc: str = "Persona 5 Royal Save Data"

    def unpack(self, buffer: bytes):
        if len(buffer) < 0x190:
            return

        (
            self.playtime,
            self.day,
            self.time,
            self.playthrough,
            self.difficulty,
            self.level,
            self.clear,
            self.fld_major,
            self.fld_minor,
            self.lang0,
            self.lang1,
            raw_lname,
            raw_fname,
            raw_desc,
        ) = struct.unpack("<IHBBBBxBBBBB64s64s256s", buffer[:0x190])

        self.lname = raw_lname.rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.fname = raw_fname.rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.desc = raw_desc.rstrip(b"\x00").decode("utf-8", errors="ignore")

    def pack(self) -> bytes:
        lname_b = pack_fixed_string(self.lname, 64)
        fname_b = pack_fixed_string(self.fname, 64)
        desc_b = pack_fixed_string(self.desc, 256)

        return struct.pack(
            "<IHBBBBxBBBBB64s64s256s",
            self.playtime,
            self.day,
            self.time,
            self.playthrough,
            self.difficulty,
            self.level,
            self.clear,
            self.fld_major,
            self.fld_minor,
            self.lang0,
            self.lang1,
            lname_b,
            fname_b,
            desc_b,
        )


class PlayerNameBlock:
    """Block ID 0x1001C: Fixed-length UTF-8 and Game string player names."""

    def __init__(self):
        self.full_name_utf8: str = "Ren Amamiya"
        self.last_name_game: str = "Amamiya"
        self.first_name_game: str = "Ren"
        self.full_name_game: str = "Ren Amamiya"
        self.group_name_game: str = "Phantom"
        self.group_name_utf8: str = "Phantom Thieves"

    def unpack(self, buffer: bytes):
        if len(buffer) < 198:
            return
        self.full_name_utf8 = buffer[0:56].rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.last_name_game = buffer[56:76].rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.first_name_game = buffer[76:96].rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.full_name_game = buffer[96:136].rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.group_name_game = buffer[136:161].rstrip(b"\x00").decode("utf-8", errors="ignore")
        self.group_name_utf8 = buffer[161:198].rstrip(b"\x00").decode("utf-8", errors="ignore")

    def pack(self) -> bytes:
        b = bytearray()
        b += pack_fixed_string(self.full_name_utf8, 56)
        b += pack_fixed_string(self.last_name_game, 20)
        b += pack_fixed_string(self.first_name_game, 20)
        b += pack_fixed_string(self.full_name_game, 40)
        b += pack_fixed_string(self.group_name_game, 25)
        b += pack_fixed_string(self.group_name_utf8, 37)
        return bytes(b)


class GameDataParser:
    """Parses data payload sub-blocks in 0x2D format.

    NOTE (2026-08-06, verified against real saves): real PC saves use a
    DIFFERENT payload format (version 0x31) that is NOT a 0x2D block stream.
    The 0x2D block walk only applies to converted PS4 saves and synthetic
    saves. For real PC payloads, `data_payload` is preserved verbatim and
    pack() returns it unchanged, so no corruption can occur.
    """

    def __init__(self):
        self.version: int = 0x2D000000
        self.header: SaveHeader = SaveHeader()
        self.player_names: PlayerNameBlock = PlayerNameBlock()
        self.blocks_raw: Dict[int, bytes] = {}
        self.data_payload: bytes = b""
        self.is_pc_0x31: bool = False

    def unpack(self, header_bytes: bytes, data_bytes: bytes):
        # 1. Unpack Header
        if header_bytes:
            self.header.unpack(header_bytes)

        # 2. Unpack Data Blocks
        if len(data_bytes) < 4:
            return

        self.data_payload = data_bytes
        offset = 0
        self.version = struct.unpack("<I", data_bytes[offset:offset+4])[0]
        offset += 4

        # Real PC saves use version 0x31 (verified 2026-08-06). The layout is
        # NOT a block stream; keep the payload verbatim and stop parsing.
        if self.version != 0x2D000000:
            self.is_pc_0x31 = True
            self.blocks_raw = {}
            return

        # 0x2D format (converted PS4 / synthetic): parse sub-header first
        if len(data_bytes) >= 0x48:
            fmt = ">2xHH2xIBBBB24s24sBB2x"
            sz = struct.calcsize(fmt)
            if offset + sz <= len(data_bytes):
                sub_hdr = data_bytes[offset:offset+sz]
                (
                    day, time_slot, playtime, level, difficulty, playthrough, clear,
                    lname, fname, fld_maj, fld_min
                ) = struct.unpack(fmt, sub_hdr)
                self.header.day = day
                self.header.time = time_slot
                self.header.playtime = playtime
                self.header.level = level
                self.header.difficulty = difficulty
                self.header.playthrough = playthrough
                self.header.clear = clear
                offset += sz

        # Read sub-blocks
        while offset + 8 <= len(data_bytes):
            block_id, block_size = struct.unpack(">II", data_bytes[offset:offset+8])
            offset += 8

            if block_id == 0x2000:
                # End block
                self.blocks_raw[0x2000] = b"\x00"
                break

            if offset + block_size > len(data_bytes):
                # Out of bounds safety guard
                self.blocks_raw[block_id] = data_bytes[offset:]
                break

            block_data = data_bytes[offset:offset+block_size]
            offset += block_size

            if block_id == 0x1001C:
                self.player_names.unpack(block_data)
            else:
                self.blocks_raw[block_id] = block_data

    def pack(self) -> Tuple[bytes, bytes]:
        """Pack GameData back to (header_bytes, data_bytes).

        For real PC saves (0x31 payload) the original payload is returned
        verbatim — the 0x2D block rebuild would corrupt it. Only the
        container header is re-serialized.
        """
        header_bytes = self.header.pack()

        if self.is_pc_0x31 and self.data_payload:
            return bytes(header_bytes), self.data_payload

        b_data = bytearray()
        b_data += struct.pack("<I", self.version)

        # 0x2D sub-header
        fmt = ">2xHH2xIBBBB24s24sBB2x"
        lname_24 = pack_fixed_string(self.header.lname, 24)
        fname_24 = pack_fixed_string(self.header.fname, 24)
        sub_hdr = struct.pack(
            fmt,
            self.header.day,
            self.header.time,
            self.header.playtime,
            self.header.level,
            self.header.difficulty,
            self.header.playthrough,
            self.header.clear,
            lname_24,
            fname_24,
            self.header.fld_major,
            self.header.fld_minor,
        )
        b_data += sub_hdr

        # Player names block 0x1001C
        names_data = self.player_names.pack()
        b_data += struct.pack(">II", 0x1001C, len(names_data))
        b_data += names_data

        # Other raw blocks
        for block_id, raw_bytes in self.blocks_raw.items():
            if block_id in (0x1001C, 0x2000):
                continue
            b_data += struct.pack(">II", block_id, len(raw_bytes))
            b_data += raw_bytes

        # End block 0x2000
        b_data += struct.pack(">II", 0x2000, 1)
        b_data += b"\x00"

        return bytes(header_bytes), bytes(b_data)
