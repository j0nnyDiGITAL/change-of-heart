"""Dump candidate regions across all saves."""
import sys
sys.path.insert(0, r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor')
from core.crypto import SaveContainer

SAVES = {
    'oracle(D11)': r'C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT',
    'fresh': r'E:/ai-workspace/knowledge-base/projects/p5r-save-editor/diff/baseline_DATA02_preprobe.DAT',
    'D14': r'C:/Users/kufis/p5r_buff_save/DATA14/DATA.DAT',
    'D15': r'C:/Users/kufis/p5r_buff_save/DATA15/DATA.DAT',
    'D16': r'C:/Users/kufis/p5r_buff_save/DATA16/DATA.DAT',
}


def load(path):
    c = SaveContainer()
    c.unpack_raw(open(path, 'rb').read())
    return c.data_bytes


def dump(buf, start, end, label):
    print(f"\n--- {label} {start:#x}..{end:#x} ---")
    for off in range(start, end, 16):
        row = buf[off:off + 16]
        hexs = ' '.join(f'{b:02x}' for b in row)
        print(f"  {off:#06x}: {hexs}")


def main():
    data = {k: load(v) for k, v in SAVES.items()}
    regions = [
        (0xc6c0, 0xc720),
        (0x24be0, 0x24c20),
        (0x55f0, 0x57a0),
        (0x1db10, 0x1dc90),
        (0x23f0, 0x2460),
        (0x1a900, 0x1a960),
    ]
    for start, end in regions:
        print(f"\n################ REGION {start:#x}..{end:#x} ################")
        for name, buf in data.items():
            dump(buf, start, end, name)

    # Mirror consistency check in oracle
    o = data['oracle(D11)']
    print("\n=== Mirror check oracle: region [0x2400..0xc700] vs +0x18510 ===")
    mism = []
    for off in range(0x2400, 0xc700):
        if o[off] != o[off + 0x18510]:
            mism.append(off)
    if mism:
        # cluster
        cl = []
        for m in mism:
            if cl and m - cl[-1][1] <= 8:
                cl[-1][1] = m
            else:
                cl.append([m, m])
        print(f"  {len(mism)} mismatched bytes in {len(cl)} clusters:")
        for a, b in cl[:40]:
            print(f"    {a:#06x}..{b:#06x}")
    else:
        print("  identical throughout!")


if __name__ == '__main__':
    main()
