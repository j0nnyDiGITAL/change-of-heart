"""
Persona 5 Royal Persona Artwork Batch Downloader
Fetches clean, official 300px PNG portraits for all 232 compendium personas
from the Megami Tensei MediaWiki API into web-app/static/assets/personas/
"""

import os
import sys
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "Personas.txt"
OUT_DIR = PROJECT_ROOT / "web-app" / "static" / "assets" / "personas"
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Special name overrides for Megami Tensei Wiki page titles
NAME_OVERRIDES = {
    "Arsene": "Arsène",
    "M. Izanagi": "Magatsu-Izanagi",
    "M. Izanagi Picaro": "Magatsu-Izanagi",
    "Izanagi-no-Okami": "Izanagi-no-Okami",
    "Izanagi-no-Okami Picaro": "Izanagi-no-Okami",
    "Asterius Picaro": "Asterius",
    "Ariadne Picaro": "Ariadne",
    "Kaguya Picaro": "Kaguya",
    "Izanagi Picaro": "Izanagi",
    "Orpheus Picaro": "Orpheus",
    "Orpheus F": "Orpheus (Female)",
    "Orpheus F Picaro": "Orpheus (Female)",
    "Thanatos Picaro": "Thanatos",
    "Messiah Picaro": "Messiah",
    "Tsukiyomi Picaro": "Tsukiyomi",
    "Athena Picaro": "Athena",
    "Raoul": "Raoul",
    "Cendrillon": "Cendrillon",
    "Vanadis": "Vanadis",
    "Ella": "Ella",
    "Robin Hood": "Robin Hood",
    "Loki": "Loki",
    "Hereward": "Hereward",
    "Captain Kidd": "Captain Kidd",
    "Seiten Taisei": "Seiten Taisei",
    "William": "William",
    "Zorro": "Zorro",
    "Mercurius": "Mercurius",
    "Diego": "Diego",
    "Carmen": "Carmen",
    "Hecate": "Hecate",
    "Celestine": "Celestine",
    "Goemon": "Goemon",
    "Gorokichi": "Gorokichi",
    "Johanna": "Johanna",
    "Anat": "Anat",
    "Agnes": "Agnes",
    "Necronomicon": "Necronomicon",
    "Prometheus": "Prometheus",
    "Al Azif": "Al Azif",
    "Milady": "Milady",
    "Astarte": "Astarte",
    "Lucy": "Lucy",
}


def load_personas():
    personas = []
    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found.")
        return personas
    with open(DATA_PATH, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f):
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                hex_str = parts[0].strip()
                en_name = parts[3].strip()
                if hex_str and hex_str != "Hex" and hex_str != "0000" and en_name and not en_name.startswith("RESERVE"):
                    try:
                        pid = int(hex_str, 16)
                        if 1 <= pid <= 232:
                            personas.append((pid, en_name))
                    except ValueError:
                        pass
    return personas


def get_image_url_for_persona(name):
    # Check override first
    query_name = NAME_OVERRIDES.get(name, name)
    
    # Try Megami Tensei Fandom MediaWiki API
    api_url = f"https://megamitensei.fandom.com/api.php?action=query&titles={urllib.parse.quote(query_name)}&prop=pageimages&format=json&pithumbsize=300"
    req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid_key, page in pages.items():
                if pid_key != "-1" and "thumbnail" in page:
                    return page["thumbnail"]["source"]
    except Exception:
        pass
    
    # Fallback to search query
    search_url = f"https://megamitensei.fandom.com/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(name)}&gsrlimit=1&prop=pageimages&format=json&pithumbsize=300"
    req = urllib.request.Request(search_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            data = json.loads(res.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid_key, page in pages.items():
                if "thumbnail" in page:
                    return page["thumbnail"]["source"]
    except Exception:
        pass

    return None


def download_single_persona(persona_tuple):
    pid, name = persona_tuple
    out_file = OUT_DIR / f"{pid}.png"
    if out_file.exists() and out_file.stat().st_size > 1000:
        return pid, name, "CACHED"

    img_url = get_image_url_for_persona(name)
    if not img_url:
        return pid, name, "NOT_FOUND"

    req = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            content = res.read()
            with open(out_file, "wb") as f:
                f.write(content)
        return pid, name, f"SUCCESS ({len(content)} bytes)"
    except Exception as ex:
        return pid, name, f"ERROR ({str(ex)})"


def main():
    personas = load_personas()
    print(f"Starting download of artwork for {len(personas)} Personas into {OUT_DIR}...")

    success = 0
    cached = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(download_single_persona, p): p for p in personas}
        for future in as_completed(futures):
            pid, name, status = future.result()
            safe_name = name.encode("ascii", errors="replace").decode("ascii")
            if "SUCCESS" in status:
                success += 1
                print(f"  [+] #{pid:03d} {safe_name:20s} -> {status}")
            elif "CACHED" in status:
                cached += 1
            else:
                failed += 1
                print(f"  [-] #{pid:03d} {safe_name:20s} -> {status}")

    print("\n" + "=" * 60)
    print(f"Artwork Download Complete: {success} downloaded, {cached} cached, {failed} failed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
