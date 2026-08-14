#!/usr/bin/env python3
"""Extract specific files from the P5R CPK by TOC offset."""
import struct, sys, os

CPK = r'J:\SteamLibrary\steamapps\common\P5R\CPK\BASE.CPK'
OUT = r'E:\ai-workspace\knowledge-base\projects\p5r-save-editor\tools\cpk_out'

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

def read_container(f, offset):
    f.seek(offset)
    head = f.read(16)
    size = be32(head, 8)
    f.seek(offset + 16)
    return decrypt_table(f.read(size))

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
        if end == -1: end = len(self.data)
        try: return self.data[base:end].decode(self.encoding, errors='replace')
        except Exception: return self.data[base:end].decode('utf-8', errors='replace')

    def columns(self):
        ptr = 0x20; cols = []
        for _ in range(self.column_count):
            flags = self.data[ptr]; ftype = flags & 0x0F; size = 1; name = None
            if flags & 0x10:
                name = self._read_string(be32(self.data, ptr + 1)); size += 4
            if flags & 0x20: size += {0:1,1:1,2:2,3:2,4:4,5:4,6:8,7:8,8:4,9:8,10:4,11:8,12:16}.get(ftype, 0)
            cols.append((flags, ftype, name, size)); ptr += size
        return cols

    def rows(self):
        cols = self.columns()
        for r in range(self.row_count):
            row_ptr = self.rows_offset + r * self.row_size; values = []
            for (flags, ftype, name, size) in cols:
                if flags & 0x40:
                    values.append(self._read_cell(row_ptr, ftype)); row_ptr += {0:1,1:1,2:2,3:2,4:4,5:4,6:8,7:8,8:4,9:8,10:4,11:8,12:16}.get(ftype, 0)
                else:
                    values.append(None)
                    if flags & 0x20: row_ptr += {0:1,1:1,2:2,3:2,4:4,5:4,6:8,7:8,8:4,9:8,10:4,11:8,12:16}.get(ftype, 0)
            yield values

    def _read_cell(self, ptr, ftype):
        if ftype == 10: return self._read_string(be32(self.data, ptr))
        if ftype in (0,1): return self.data[ptr]
        if ftype in (2,3): return be16(self.data, ptr)
        if ftype in (4,5): return be32(self.data, ptr)
        if ftype in (6,7): return be64(self.data, ptr)
        if ftype == 11: return (be64(self.data, ptr), be64(self.data, ptr+8))
        return None


def get_toc():
    with open(CPK, 'rb') as f:
        buf = bytearray(f.read(0x820)); p5r_xor(buf)
        main = decrypt_table(bytes(buf[16:16+be32(bytes(buf), 8)]))
        mtbl = CriTable(main)
        row = next(mtbl.rows())
        info = dict(zip([c[2] for c in mtbl.columns()], row))
        toc_off = info['TocOffset']
        content_off = info['ContentOffset']
        # CpkHelper: "In some CPKs offsets are relative to TOC as opposed to
        # ContentOffset in header. This happens when TOC address is before
        # ContentOffset." -> offset_base = min(toc_off, content_off)
        offset_base = min(toc_off, content_off) if content_off else toc_off
        toc = read_container(f, toc_off)
        ttbl = CriTable(toc)
        tnames = [c[2] for c in ttbl.columns()]
        files = []
        for r in ttbl.rows():
            d = dict(zip(tnames, r))
            path = str(d.get('DirName','')) + str(d.get('FileName',''))
            if path:
                files.append({'off': offset_base + (d.get('FileOffset') or 0),
                              'size': d.get('FileSize'),
                              'xsize': d.get('ExtractSize'), 'path': path})
        return files

def extract(files, patterns):
    os.makedirs(OUT, exist_ok=True)
    count = 0
    with open(CPK, 'rb') as f:
        for fi in files:
            if any(p in fi['path'].lower() for p in patterns):
                f.seek(fi['off'])
                raw = f.read(fi['size'])
                # CRI may compress with CriLayla; if compressed, header starts with CrLay
                out_path = os.path.join(OUT, fi['path'].replace('/', os.sep))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'wb') as o:
                    o.write(raw)
                count += 1
                print(f'  {fi["path"]} ({fi["size"]}B)')
    print(f'extracted {count} files')

if __name__ == '__main__':
    files = get_toc()
    print(f'TOC: {len(files)} files')
    patterns = sys.argv[1:] or ['kf_event']
    extract(files, [p.lower() for p in patterns])
