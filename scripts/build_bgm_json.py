#!/usr/bin/env python3
"""Build playable data/db/guides/background_music.json from cached or live background_music HTML."""

import glob
import json
import os
import pathlib
import re
import subprocess
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = pathlib.Path(
    os.environ.get(
        "IRUNA_SCRAPE_CACHE",
        r"C:\Users\Asus\.gemini\antigravity-cli\brain\b100dde5-d4f9-4213-8aba-979e0e814498\scratch\raw_html",
    )
)

PLACE_TH = {
    "Title": "หน้าไตเติล (Title)",
    "Fort Bailune": "ฐานทัพไบลูน (Fort Bailune)",
    "Micerne Plains": "ทุ่งราบมิเชิร์น (Micerne Plains)",
    "Rokoko Mining Village": "หมู่บ้านเหมืองแร่โลโคโค (Rokoko Mining Village)",
    "Rokoko Tunnels": "อุโมงค์โลโคโค (Rokoko Tunnels)",
    "Rokoko Windhole": "ช่องลมโลโคโค (Rokoko Windhole)",
    "Rokoko City": "เมืองโลโคโค (Rokoko City)",
    "Rokoko Plains": "ทุ่งราบโลโคโค (Rokoko Plains)",
    "Forgotten Cave": "ถ้ำที่ถูกลืม (Forgotten Cave)",
    "Capital City Sofya": "มหานครโซเฟีย (Capital City Sofya)",
    "Capital City Saterica": "มหานครซาเทริกา (Capital City Saterica)",
    "Capital City Elban": "มหานครเออร์แบน (Capital City Elban)",
    "Minaula City": "เมืองมินาอุละ (Minaula City)",
    "Port Spargas": "เมืองท่าสปาร์กัส (Port Spargas)",
    "Kleya City": "เมืองเคลย่า (Kleya City)",
    "Bailune City": "เมืองไบลูน (Bailune City)",
    "Diel Village": "หมู่บ้านดีล (Diel Village)",
    "Wibo City": "เมืองวิโบ (Wibo City)",
    "Lograth City": "เมืองโลกราธ (Lograth City)",
    "Creldan": "เมืองเครอร์ดัน (Creldan)",
    "Music": "เพลงประกอบ (Music)",
}


def get_html():
    cached = sorted(CACHE_DIR.glob("background_music_*.html"))
    if cached:
        return cached[0].read_text(encoding="utf-8", errors="replace")
    r = subprocess.run(
        ["curl.exe", "-s", "-L", "-A", "Mozilla/5.0", "https://th.iruna-online.info/iruna/background_music"],
        capture_output=True,
    )
    return r.stdout.decode("utf-8", errors="replace")


def main():
    html = get_html()
    soup = BeautifulSoup(html, "html.parser")
    main_div = soup.find("div", class_="col-md-9") or soup.find("div", class_="col-md-7")

    tracks = []
    seen = set()
    for a in main_div.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("bgm/"):
            continue
        if href in seen:
            continue
        seen.add(href)
        url = "https://th.iruna-online.info/iruna/" + href
        txt = a.get_text(" ", strip=True)
        m = re.match(r"^(\d+)\s*:\s*(.*)$", txt)
        if m:
            tid = int(m.group(1))
            title = m.group(2).strip()
        else:
            tid = len(tracks)
            title = txt
        tracks.append({
            "id": tid,
            "file": href.split("/")[-1],
            "title": PLACE_TH.get(title, title),
            "url": url,
        })

    out = {
        "key": "background_music",
        "label": "เพลงประกอบ (Background Music)",
        "tracks": tracks,
    }
    dest = REPO_ROOT / "data" / "db" / "guides" / "background_music.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Saved {len(tracks)} playable BGM tracks! Sample:", tracks[:5])


if __name__ == "__main__":
    main()
