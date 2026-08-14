"""probe_persona_stock2.py — verify array across all 10 member slots + pretty sample w/ skill names."""
import sys, struct
sys.path.insert(0, r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor')
from core.crypto import SaveContainer

PROJ = r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor'
ORACLE = r'C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT'
FRESH  = PROJ + r'/diff/baseline_DATA02_preprobe.DAT'
NAMES = ['Joker','Ryuji','Morgana','Ann','Yusuke','Makoto','Futaba','Haru','Akechi','Kasumi']

def load(path, col=3):
    d = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        p = line.rstrip('\n').split('\t')
        if len(p) <= col: continue
        try: k = int(p[0], 16)
        except ValueError: continue
        d[k] = p[col]
    return d
personas = load(PROJ+'/data/Personas.txt'); skills = load(PROJ+'/data/Skill ID.txt'); traits = load(PROJ+'/data/Traits.txt')

def unpack(path):
    c = SaveContainer(); assert c.unpack_raw(open(path,'rb').read()); return c.data_bytes
oracle, fresh = unpack(ORACLE), unpack(FRESH)
def u16(b,o): return struct.unpack_from('<H',b,o)[0]
def u8(b,o): return b[o]
def u32(b,o): return struct.unpack_from('<I',b,o)[0]

def slot0(b, m):
    o = 0x2C + m*0x2B0 + 0x38
    return (u16(b,o), u16(b,o+2), u8(b,o+4), u16(b,o+6), u32(b,o+8), [u8(b,o+0x1C+i) for i in range(5)])

print("== slot0 (equipped) per member, ORACLE ==")
for m in range(10):
    fl, pid, lvl, tr, exp, st = slot0(oracle, m)
    print(f"  {NAMES[m]:8s}: flags=0x{fl:04X} id=0x{pid:03X} {personas.get(pid,'EMPTY'):<22s} Lv{lvl:3d} trait={traits.get(tr,'?'):<20s} exp={exp:>8d} st={st}")
print("== slot0 per member, FRESH ==")
for m in range(10):
    fl, pid, lvl, tr, exp, st = slot0(fresh, m)
    print(f"  {NAMES[m]:8s}: flags=0x{fl:04X} id=0x{pid:03X} {personas.get(pid,'EMPTY'):<22s} Lv{lvl:3d} trait={traits.get(tr,'?'):<20s} exp={exp:>8d} st={st}")
print()

def full(m, b, k, label):
    o = 0x2C + m*0x2B0 + 0x38 + k*0x30
    sk = [skills.get(u16(b,o+0xC+i*2), f'0x{u16(b,o+0xC+i*2):04X}') for i in range(8)]
    print(f"  {label}: flags=0x{u16(b,o):04X} id=0x{u16(b,o+2):03X} {personas.get(u16(b,o+2),'?')} Lv{u8(b,o+4)} unk={u8(b,o+5):02X} trait=0x{u16(b,o+6):04X} {traits.get(u16(b,o+6),'?')} exp={u32(b,o+8)}")
    print(f"      skills: {sk}")
    print(f"      stats : St={u8(b,o+0x1C)} Ma={u8(b,o+0x1D)} En={u8(b,o+0x1E)} Ag={u8(b,o+0x1F)} Lu={u8(b,o+0x20)}")
    print(f"      pad   : {b[o+0x21:o+0x30].hex()}")

print("== ORACLE Joker sample ==")
for k in range(3): full(0, oracle, k, f"slot{k}")
print("== ORACLE Ryuji sample ==")
for k in range(2): full(1, oracle, k, f"slot{k}")
print("== FRESH Joker sample ==")
for k in range(3): full(0, fresh, k, f"slot{k}")
print("== FRESH Ryuji sample ==")
for k in range(1): full(1, fresh, k, f"slot{k}")

# empty-slot check: bytes of a zero slot
o = 0x2C + 0*0x2B0 + 0x38 + 11*0x30
print("== ORACLE Joker slot11 raw tail (should end at +0x277, next byte +0x278 = equipment) ==")
print(f"  last slot bytes 0x{0x38+11*0x30:03X}..0x{0x38+12*0x30-1:03X}: {oracle[0x2C+0x38+11*0x30 : 0x2C+0x38+12*0x30].hex()}")
