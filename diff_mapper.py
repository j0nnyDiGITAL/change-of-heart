#!/usr/bin/env python3
"""
P5R 2-Save Diff Mapper
======================
Diffs two decrypted DATA.DAT payloads and produces a labeled offset report.

Usage:
    python diff_mapper.py <saveA> <saveB> [--out report.md]

The report decodes every changed run as u8/u16/u32 LE + float32 + ASCII +
UTF-16LE, and flags proximity to known/candidate offsets.
"""
import argparse
import json
import os
import struct
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.crypto import SaveContainer
from core.parser import GameDataParser

# ---------------------------------------------------------------- known map
KNOWN = [
    (0x35C0, "MONEY (u32, VERIFIED)"),
    (0x2556, "CONFIDANTS candidate (23 bytes, 1/arcana)"),
    (0x4370, "SOCIAL STATS candidate (32B)"),
    (0x437C, "SOCIAL STATS alt candidate (5B)"),
    (0x2C,   "PARTY base candidate (stride 0x2B0)"),
    (0x3D70, "DAY counter candidate (u8, +1/save)"),
]
RADIUS = 0x40


def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    c = SaveContainer()
    c.unpack_raw(raw)
    p = GameDataParser()
    p.unpack(c.header_bytes, c.data_bytes)
    return c, p


def diff_runs(a, b, gap=4):
    n = min(len(a), len(b))
    diffs = [i for i in range(n) if a[i] != b[i]]
    groups = []
    for i in diffs:
        if groups and i - groups[-1][-1] <= gap:
            groups[-1].append(i)
        else:
            groups.append([i])
    return diffs, groups


def decoders(buf, off):
    out = []
    if off + 1 <= len(buf):
        out.append(("u8", buf[off]))
    if off + 2 <= len(buf):
        out.append(("u16", struct.unpack_from("<H", buf, off)[0]))
    if off + 4 <= len(buf):
        out.append(("u32", struct.unpack_from("<I", buf, off)[0]))
    if off + 4 <= len(buf):
        f = struct.unpack_from("<f", buf, off)[0]
        out.append(("f32", round(f, 4)))
    if off + 4 <= len(buf):
        out.append(("i32", struct.unpack_from("<i", buf, off)[0]))
    return out


def ascii_at(buf, off, maxlen=40):
    s = []
    for i in range(off, min(off + maxlen, len(buf))):
        b = buf[i]
        if 32 <= b < 127:
            s.append(chr(b))
        elif b in (0, 9, 10, 13):
            break
        else:
            break
    return "".join(s)


def utf16_at(buf, off, maxlen=20):
    s = []
    for i in range(off, min(off + maxlen * 2, len(buf) - 1), 2):
        ch = struct.unpack_from("<H", buf, i)[0]
        if ch == 0:
            break
        if 32 <= ch < 0x7F:
            s.append(chr(ch))
        else:
            s.append("?")
    return "".join(s)


def nearby(off):
    tags = []
    for ko, label in KNOWN:
        if abs(off - ko) <= RADIUS:
            d = off - ko
            tags.append(f"{label} {'+' if d >= 0 else ''}{d:#x}")
    return tags


def render_run(a, b, offs, idx):
    s, e = offs[0], offs[-1] + 1
    span = e - s
    lines = [f"### Run {idx} @ 0x{s:04X} (len {len(offs)}, span {span})"]
    tags = nearby(s)
    if tags:
        lines.append("**Near:** " + "; ".join(tags))
    # byte-level detail for first 24 offsets
    for off in offs[:24]:
        va, vb = a[off], b[off]
        da = " ".join(f"{x}={y}" for x, y in decoders(a, off) if x in ("u8", "u16", "u32"))
        db = " ".join(f"{x}={y}" for x, y in decoders(b, off) if x in ("u8", "u16", "u32"))
        lines.append(f"  `0x{off:04X}`: {va:02X} -> {vb:02X}   A[{da}]  B[{db}]")
    if len(offs) > 24:
        lines.append(f"  ... +{len(offs) - 24} more bytes")
    # float / ascii / utf16 summary at run start
    fa = " ".join(f"{x}={y}" for x, y in decoders(a, s) if x == "f32")
    fb = " ".join(f"{x}={y}" for x, y in decoders(b, s) if x == "f32")
    if fa or fb:
        lines.append(f"  floats: A[{fa}]  B[{fb}]")
    aa, ab = ascii_at(a, s), ascii_at(b, s)
    if aa or ab:
        lines.append(f"  ascii A: {aa!r}")
        lines.append(f"  ascii B: {ab!r}")
    ua, ub = utf16_at(a, s), utf16_at(b, s)
    if ua or ub:
        lines.append(f"  utf16 A: {ua!r}")
        lines.append(f"  utf16 B: {ub!r}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("saveA")
    ap.add_argument("saveB")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cA, pA = load(args.saveA)
    cB, pB = load(args.saveB)
    a, b = pA.data_payload, pB.data_payload

    diffs, groups = diff_runs(a, b)
    out = []
    out.append(f"# P5R Save Diff Report")
    out.append(f"")
    out.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
    out.append(f"- A: {os.path.basename(args.saveA)} (payload {len(a)} bytes)")
    out.append(f"- B: {os.path.basename(args.saveB)} (payload {len(b)} bytes)")
    out.append(f"- Differing bytes: **{len(diffs)}** in **{len(groups)}** runs")
    out.append(f"")
    out.append(f"## Header (container) differences")
    hdiffs, hgroups = diff_runs(cA.header_bytes, cB.header_bytes, gap=0)
    for g in hgroups:
        s = g[0]
        sa = ascii_at(cA.header_bytes, s, 96)
        sb = ascii_at(cB.header_bytes, s, 96)
        out.append(f"- `0x{s:04X}` ({len(g)}B): A `{sa!r}` -> B `{sb!r}`")
    out.append(f"")
    out.append(f"## Payload runs")
    for i, g in enumerate(groups):
        out.append(render_run(a, b, g, i))
        out.append("")
    report = "\n".join(out)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n[written] {args.out}")

    # machine-readable
    jpath = args.out.replace(".md", ".json") if args.out else None
    if jpath:
        data = {
            "saveA": args.saveA, "saveB": args.saveB,
            "differing_bytes": len(diffs),
            "runs": [
                {"offset": g[0], "len": len(g), "span": g[-1] - g[0] + 1,
                 "a": [a[i] for i in g[:64]], "b": [b[i] for i in g[:64]]}
                for g in groups
            ],
        }
        with open(jpath, "w") as f:
            json.dump(data, f, indent=1)
        print(f"[written] {jpath}")


if __name__ == "__main__":
    main()
