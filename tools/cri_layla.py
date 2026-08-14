#!/usr/bin/env python3
"""CRILAYLA decompression — exact Python port of CriFsV2Lib.CriLayla.

Format: [CRILAYLA 16B header][compressed data][0x100 raw header].
Bitstream reads BACKWARD from the end of the compressed region, MSB-first
within each byte. Output: 0x100 header at start, LZ77 data written backward.
"""
import struct

UNCOMP_SIZE = 0x100
MIN_COPY = 3

class BackBitReader:
    """Reads bits backward from the compressed region."""
    def __init__(self, data, end_pos):
        self.data = data
        self.pos = end_pos  # one past the last byte of compressed region
        self.bits_left = 0
        self.cur = 0

    def _fetch(self):
        self.pos -= 1
        if self.pos < 0:
            raise ValueError('bitstream underrun')
        self.cur = self.data[self.pos]
        self.bits_left = 8

    def bit(self):
        if self.bits_left == 0:
            self._fetch()
        self.bits_left -= 1
        return (self.cur >> self.bits_left) & 1  # MSB-first

    def read(self, n):
        """Read n bits, MSB-first, stream advancing backward."""
        v = 0
        for _ in range(n):
            v = (v << 1) | self.bit()
        return v


def decompress(data: bytes) -> bytes:
    if len(data) < 16 or data[:8] != b'CRILAYLA':
        return data
    uncomp_size = struct.unpack_from('<I', data, 8)[0]
    header_off = struct.unpack_from('<I', data, 12)[0]

    raw_start = header_off + 0x10  # 0x100 raw header block begins here
    result = bytearray(uncomp_size + UNCOMP_SIZE)
    result[0:UNCOMP_SIZE] = data[raw_start:raw_start + UNCOMP_SIZE]

    # Compressed region: [0x10 .. raw_start); bitstream begins at raw_start
    # and reads backward.
    br = BackBitReader(data, raw_start)

    write_ptr = UNCOMP_SIZE + uncomp_size - 1
    min_addr = UNCOMP_SIZE

    while write_ptr >= min_addr:
        if br.bit() == 1:
            offset = br.read(13) + MIN_COPY
            length = MIN_COPY
            lvl = br.read(2)
            length += lvl
            if lvl == 3:
                lvl = br.read(3)
                length += lvl
                if lvl == 7:
                    lvl = br.read(5)
                    length += lvl
                    if lvl == 31:
                        while True:
                            lvl = br.read(8)
                            length += lvl
                            if lvl != 255:
                                break
            for _ in range(length):
                result[write_ptr] = result[write_ptr + offset]
                write_ptr -= 1
        else:
            result[write_ptr] = br.read(8)
            write_ptr -= 1

    return bytes(result)


if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        raw = open(path, 'rb').read()
        out = decompress(raw)
        outp = path + '.dec'
        open(outp, 'wb').write(out)
        print(f'{path}: {len(raw)} -> {len(out)} -> {outp}')
        print('  head:', out[:16].hex())
