"""P5R confidant probe: unique rank ramp 1..10 on the 11 active entries.

Writes DISTINCT ranks so one in-game confidant-menu screenshot maps
entry ID -> arcana in a single load. Baseline is preserved at
diff/baseline_DATA02_preprobe.DAT. Writes to DATA02/DATA.DAT (slot 2).
"""
import sys
import struct
import shutil

sys.path.insert(0, r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
from core.crypto import SaveContainer

SRC = r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor\diff\baseline_DATA02_preprobe.DAT"
DST = r"C:\Users\kufis\AppData\Roaming\SEGA\P5R\Steam\76561197984149929\savedata\DATA02\DATA.DAT"
BASE = 0x136A0
STRIDE = 16
RANK_OFF = 8  # within entry

# Unique ramp 1..10 on the 11 active (nonzero-id) entries
RAMP = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 % 11]  # last active entry gets 1 -> hmm
# Better: entries 0..9 get 1..10; entry 10 (id=9) leave unchanged to keep
# at least one control. Actually make it clean: 0..10 -> 1..11%? rank max 10.
# Decide: entries 0..9 -> ranks 1..10. Entry 10 untouched (control).
RAMP = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

cont = SaveContainer()
cont.unpack_raw(open(SRC, "rb").read())
d = bytearray(cont.data_bytes)

for i, r in enumerate(RAMP):
    off = BASE + i * STRIDE + RANK_OFF
    d[off] = r  # rank byte (u16 low byte; high byte already 0)
    # also max out points so the game never clamps the displayed rank
    struct.pack_into("<H", d, BASE + i * STRIDE + 10, 0xFFFF)

cont.data_bytes = bytes(d)
out = cont.pack_raw(compress=True, encrypt=True)

# safety: verify we can roundtrip what we wrote
cont2 = SaveContainer()
cont2.unpack_raw(out)
d2 = cont2.data_bytes
print("roundtrip ranks:")
for i in range(11):
    off = BASE + i * STRIDE + RANK_OFF
    cid = struct.unpack_from("<H", d2, BASE + i * STRIDE + 6)[0]
    pts = struct.unpack_from("<H", d2, BASE + i * STRIDE + 10)[0]
    print(f"  entry[{i:2d}] id={cid:3d} rank={d2[off]:2d} pts=0x{pts:04X}")

# write probe to slot 2
with open(DST, "wb") as f:
    f.write(out)
print(f"\nwrote probe ({len(out)} bytes) -> {DST}")
