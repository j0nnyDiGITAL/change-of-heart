#!/usr/bin/env python3
"""P5R CPK extractor v3 — full TOC listing + targeted extraction."""
import struct, sys, os, re

CPK = r'J:\SteamLibrary\steamapps\common\P5R\CPK\BASE.CPK'
OUT = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\tools\cpk_out'

TYPE_SIZE = {0:1, 1:1, 2:2, 3:2, 4:4, 5:4, 6:8, 7:8, 8:4, 9:8, 10:4, 11:8, 12:16}

def be16(b, o): return struct.unpack_from('>H', b, o)[0]
def be32(b, o): return struct.unpack_from('>I', b, o)[0]
def be64(b, o): return struct.unpack_from('>Q', b, o)[0]

def p5r_xor(buf):
    for i in range(0x20, 0x420):
        if i + 0x400 < len(buf):
            buf[i] ^= buf[i + 0x400]

def decrypt_table(data):
    if len(data) >= 4 and struct.unpack('<I', data[:4])[0] == 0xF5F39E1F:
        out = bytearray(data)
        xor = 0x5F
        for i in range(len(out)):
            out[i] ^= xor
            xor = (xor * 0x15) & 0xFF
        return bytes(out)
    return data

def read_container(f, offset, max_extra=0):
    f.seek(offset)
    head = f.read(16)
    size = be32(head, 8)
    if size > 0x1000000:  # sanity
        raise ValueError(f'size {size} implausible at 0x{offset:X}')
    f.seek(offset + 16)
    table = f.read(size)
    return decrypt_table(table)

class CriTable:
    def __init__(self, data):
        self.data = data
        self.rows_offset = be16(data, 0x0A) + 8
        self.string_pool = be32(data, 0x0C) + 8
        self.data_pool = be32(data, 0x10) + 8
        self.column_count = be16(data, 0x18)
        self.row_size = be16(data, 0x1A)
        self.row_count = be32(data, 0x1C)
        self.encoding = 'shift_jis' if data[0x09] == 0 else 'utf-8'

    def _read_string(self, offset):
        base = self.string_pool + offset
        end = self.data.find(b'\x00', base)
        if end == -1:
            end = len(self.data)
        try:
            return self.data[base:end].decode(self.encoding, errors='replace')
        except Exception:
            return self.data[base:end].decode('utf-8', errors='replace')

    def columns(self):
        ptr = 0x20
        cols = []
        for _ in range(self.column_count):
            flags = self.data[ptr]
            ftype = flags & 0x0F
            size = 1
            name = None
            if flags & 0x10:
                name = self._read_string(be32(self.data, ptr + 1))
                size += 4
            if flags & 0x20:
                size += TYPE_SIZE.get(ftype, 0)
            cols.append((flags, ftype, name, size))
            ptr += size
        return cols

    def rows(self):
        cols = self.columns()
        for r in range(self.row_count):
            row_ptr = self.rows_offset + r * self.row_size
            values = []
            for (flags, ftype, name, size) in cols:
                if flags & 0x40:
                    values.append(self._read_cell(row_ptr, ftype))
                    row_ptr += TYPE_SIZE.get(ftype, 0)
                else:
                    values.append(None)
                    if flags & 0x20:
                        row_ptr += TYPE_SIZE.get(ftype, 0)
            yield values

    def _read_cell(self, ptr, ftype):
        if ftype == 10:
            return self._read_string(be32(self.data, ptr))
        if ftype in (0, 1): return self.data[ptr]
        if ftype in (2, 3): return be16(self.data, ptr)
        if ftype in (4, 5): return be32(self.data, ptr)
        if ftype in (6, 7): return be64(self.data, ptr)
        if ftype == 11: return (be64(self.data, ptr), be64(self.data, ptr+8))
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(CPK, 'rb') as f:
        buf = bytearray(f.read(0x820))
        p5r_xor(buf)
        size = be32(bytes(buf), 8)
        main = decrypt_table(bytes(buf[16:16+size]))
        mtbl = CriTable(main)
        row = next(mtbl.rows())
        col_names = [c[2] for c in mtbl.columns()]
        info = dict(zip(col_names, row))
        toc_off = info.get('TocOffset')
        toc_size = info.get('TocSize')
        content_off = info.get('ContentOffset')
        print(f'TOC: off=0x{toc_off:X} size={toc_size} content=0x{content_off:X}')

        # read TOC container (header table at toc_off has its own container)
        f.seek(toc_off)
        toc_head = f.read(16)
        tsize = be32(toc_head, 8)
        f.seek(toc_off + 16)
        toc_raw = f.read(tsize)
        toc = decrypt_table(toc_raw)
        print('TOC sig:', toc[:4])

        ttbl = CriTable(toc)
        print(f'TOC table: cols={ttbl.column_count} rows={ttbl.row_count} rowsize={ttbl.row_size}')
        tcols = ttbl.columns()
        print('TOC columns:', [c[2] for c in tcols])
        tnames = [c[2] for c in tcols]

        # scan for event/field/script paths
        matches = []
        for r in ttbl.rows():
            d = dict(zip(tnames, r))
            path = d.get('DirName', '') + d.get('FileName', '')
            if not path:
                continue
            pl = path.lower()
            if any(k in pl for k in ('.bf', '.flow', 'event', 'field', 'script', 'fcl', 'confidant')):
                matches.append((d.get('FileOffset'), d.get('FileSize'), d.get('ExtractSize'), path))

        print(f'\n=== {len(matches)} script-ish files ===')
        for off, fsz, xsz, path in matches[:40]:
            print(f'  0x{off:X}  {fsz:>8}  {path}')

        # Save full TOC listing
        with open(os.path.join(OUT, 'toc_listing.txt'), 'w', encoding='utf-8') as out:
            for r in ttbl.rows():
                d = dict(zip(tnames, r))
                path = str(d.get('DirName', '')) + str(d.get('FileName', ''))
                out.write(f"0x{d.get('FileOffset') or 0:X}\t{d.get('FileSize') or 0}\t{path}\n")
        print('\nfull listing -> tools/cpk_out/toc_listing.txt')

if __name__ == '__main__':
    main()
