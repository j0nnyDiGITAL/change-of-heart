"""probe_persona_stock.py — Locate/decode the 12-slot persona STOCK array per party member.

Hypothesis (PS4 ref): persona struct = 0x30 bytes: [flags u16][id u16][level u8][unk u8][trait u16][exp u32][8x skill u16][st ma en ag lu 5x u8][pad].
PC equipped-persona fields at +0x38..+0x59 match that layout exactly, so test array base = +0x38, stride 0x30, 12 slots (spans +0x38..+0x278).
"""
import sys, struct
sys.path.insert(0, r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor')
from core.crypto import SaveContainer

PROJ = r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor'
ORACLE = r'C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT'
FRESH  = PROJ + r'/diff/baseline_DATA02_preprobe.DAT'

MEMBER_BASE = 0x2C
MEMBER_STRIDE = 0x2B0
NAMES = ['Joker','Ryuji','Morgana','Ann','Yusuke','Makoto','Futaba','Haru','Akechi','Kasumi']

def load_table(path, name_col=3):
    d = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < name_col+1: continue
            try: key = int(parts[0], 16)
            except ValueError: continue
            d[key] = parts[name_col]
    return d

personas = load_table(PROJ + '/data/Personas.txt')
skills   = load_table(PROJ + '/data/Skill ID.txt')
traits   = load_table(PROJ + '/data/Traits.txt')

def unpack(path):
    c = SaveContainer(); ok = c.unpack_raw(open(path,'rb').read())
    print(f"[unpack] {path} ok={ok} payload={len(c.data_bytes)}B")
    return c.data_bytes

oracle = unpack(ORACLE)
fresh  = unpack(FRESH)

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u8(b, o):  return b[o]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def member_base(slot): return MEMBER_BASE + slot*MEMBER_STRIDE

def scatter(b, slot, lo=0x30, hi=0x2AF):
    """All u16 offsets in member block whose value is a valid persona id."""
    mb = member_base(slot)
    hits = []
    for o in range(lo, hi-1):
        v = u16(b, mb+o)
        if v in personas and v != 0:
            hits.append((o, v, personas[v]))
    return hits

def score_bases(b, slot, strides=(0x30,), idoffs=(2,), lo=0x30, hi=0x2B0, nslots=12):
    """For each base, count slots whose id is valid-or-zero, weighted."""
    mb = member_base(slot)
    best = []
    for base in range(lo, hi - nslots*max(strides) + 1):
        for stride in strides:
            for idoff in idoffs:
                score = 0; details = []
                for k in range(nslots):
                    o = base + k*stride + idoff
                    if o+2 > hi + lo: break
                    v = u16(b, mb+o)
                    lvl = u8(b, mb+base+k*stride+4) if idoff == 2 else 0
                    if v == 0:
                        score += 0.5
                    elif v in personas:
                        score += 1.0
                        details.append((k, v, personas[v], lvl))
                best.append((score, base, stride, idoff, details))
    best.sort(key=lambda x: -x[0])
    return best[:8]

def decode_slots(b, slot, base, stride=0x30, nslots=12):
    mb = member_base(slot)
    out = []
    for k in range(nslots):
        o = mb + base + k*stride
        flags = u16(b, o+0); pid = u16(b, o+2)
        lvl = u8(b, o+4); unk = u8(b, o+5)
        trait = u16(b, o+6); exp = u32(b, o+8)
        sk = [u16(b, o+0xC+i*2) for i in range(8)]
        stats = [u8(b, o+0x1C+i) for i in range(5)]
        out.append(dict(k=k, flags=flags, pid=pid, name=personas.get(pid, '???'),
                        lvl=lvl, unk=unk, trait=trait, trait_name=traits.get(trait,'?'),
                        exp=exp, skills=sk, skill_names=[skills.get(s,'?') for s in sk],
                        stats=stats))
    return out

def dump_hex(b, slot, lo=0x30, hi=0x2AF, label=''):
    mb = member_base(slot)
    print(f"--- hex dump {label} member {slot} ({NAMES[slot]}) +0x{lo:03X}..+0x{hi:03X} ---")
    for o in range(lo, hi+1, 16):
        row = b[mb+o:mb+min(o+16, hi+1)]
        print(f"+0x{o:03X}: " + ' '.join(f'{x:02X}' for x in row))
    print()

# ---- 1. Scatter for Joker + Ryuji, oracle + fresh ----
for slot in (0, 1):
    for label, b in (('ORACLE', oracle), ('FRESH', fresh)):
        hits = scatter(b, slot)
        print(f"[scatter] {NAMES[slot]} {label}: {len(hits)} valid-persona u16 in +0x30..+0x2AF")
        for o, v, name in hits:
            print(f"   +0x{o:03X} = 0x{v:03X} {name}")
        print()

# ---- 2. Earlier-clue offsets (0x6A..0x88) reconciliation ----
print("[reconcile] Joker ORACLE u16 values +0x38..+0x2AF at every 0x30-stride id-offset (base+2):")
for base in (0x38, 0x58, 0x68):
    row = []
    for k in range(12):
        o = base + k*0x30 + 2
        v = u16(oracle, member_base(0)+o)
        row.append(f"slot{k}@+0x{o:03X}=0x{v:03X}({personas.get(v,'?')})")
    print(f"  base +0x{base:02X}: " + ' | '.join(row))
print()

# ---- 3. Stride scoring, all members, oracle ----
print("[score] oracle save, stride-0x30 id@+2 candidates (top base per member):")
for slot in range(10):
    best = score_bases(oracle, slot)[0]
    print(f"  {NAMES[slot]:8s} slot{slot}: score={best[0]:.1f} base=+0x{best[1]:03X}")
print()

# ---- 4. Hex dumps ----
dump_hex(oracle, 0, label='ORACLE')
dump_hex(fresh, 0, label='FRESH ')
dump_hex(oracle, 1, label='ORACLE')

# ---- 5. Decode winning base (+0x38) ----
print("[decode] ORACLE Joker @ base +0x38 stride 0x30:")
for e in decode_slots(oracle, 0, 0x38):
    print(f"  [{e['k']:2d}] flags=0x{e['flags']:04X} id=0x{e['pid']:03X} {e['name']:<22s} Lv{e['lvl']:3d} unk={e['unk']:02X} trait={e['trait_name']:<14s} exp={e['exp']:>8d} st={e['stats']}")
print()
print("[decode] ORACLE Ryuji @ base +0x38 stride 0x30:")
for e in decode_slots(oracle, 1, 0x38):
    print(f"  [{e['k']:2d}] flags=0x{e['flags']:04X} id=0x{e['pid']:03X} {e['name']:<22s} Lv{e['lvl']:3d} unk={e['unk']:02X} trait={e['trait_name']:<14s} exp={e['exp']:>8d} st={e['stats']}")
print()
print("[decode] FRESH Joker @ base +0x38 stride 0x30:")
for e in decode_slots(fresh, 0, 0x38):
    print(f"  [{e['k']:2d}] flags=0x{e['flags']:04X} id=0x{e['pid']:03X} {e['name']:<22s} Lv{e['lvl']:3d} unk={e['unk']:02X} trait={e['trait_name']:<14s} exp={e['exp']:>8d} st={e['stats']}")
print()
print("[decode] FRESH Ryuji @ base +0x38 stride 0x30:")
for e in decode_slots(fresh, 1, 0x38):
    print(f"  [{e['k']:2d}] flags=0x{e['flags']:04X} id=0x{e['pid']:03X} {e['name']:<22s} Lv{e['lvl']:3d} unk={e['unk']:02X} trait={e['trait_name']:<14s} exp={e['exp']:>8d} st={e['stats']}")
print()

# ---- 6. What is the +0x250..+0x2AF region? decode as slots 10/11 continuation ----
print("[decode] ORACLE Joker slots 10-11 raw +0x248..+0x2AF (u16 view):")
for o in range(0x248, 0x2B0, 2):
    v = u16(oracle, member_base(0)+o)
    tag = personas.get(v, '')
    print(f"  +0x{o:03X}: 0x{v:04X} {tag}")
