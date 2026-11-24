#!/usr/bin/env python3
"""
Master scraper for https://th.iruna-online.info/iruna/
Extracts ALL sections into structured JSON files under data/db/
for the static GitHub Pages site.
"""

import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "https://th.iruna-online.info/iruna/"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "db"
CACHE_DIR = Path(
    os.environ.get(
        "IRUNA_SCRAPE_CACHE",
        str(Path.home() / ".cache" / "iruna_th_scrape_html"),
    )
)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

EQUIPMENT_CATS = [
    ("Swords", "ดาบ (Swords)"),
    ("Bows", "ธนู (Bows)"),
    ("Canes", "ไม้เท้า (Canes)"),
    ("Claws", "กรงเล็บ (Claws)"),
    ("Throwing", "อาวุธขว้าง (Throwing)"),
    ("Armor", "ชุดเกราะ (Armor)"),
    ("Additional", "อุปกรณ์เสริม (Additional)"),
    ("Special", "อุปกรณ์พิเศษ (Special)"),
    ("Crystas", "คริสต้า ◇ (Crystas)"),
    ("AlCrystas", "อัลคริสต้า ▲ (Al Crystas)"),
    ("RelicCrystas", "เรลิกคริสต้า □ (Relic Crystas)"),
]

ITEM_CATS = [
    ("Recovery", "ฟื้นฟู (Recovery)"),
    ("Status", "แก้สถานะ (Status)"),
    ("Strengthening", "เพิ่มพลัง/บัฟ (Strengthening)"),
    ("Teleport", "วาร์ป (Teleport)"),
    ("Skills", "หนังสือสกิล (Skill)"),
    ("Chests", "กล่องสมบัติ (Chests)"),
    ("Collectibles", "ของสะสม/วัตถุดิบ (Collectibles)"),
    ("Ores", "แร่ตีบวก (Ores)"),
    ("IslandItems", "ของแต่งเกาะ (Island Objects)"),
    ("Points", "ไอเทมช็อป (Store Items)"),
    ("Pets", "ไข่/อาหารสัตว์เลี้ยง (Pets)"),
    ("Fish", "ปลา/ตกปลา (Fish)"),
    ("Other", "อื่นๆ (Other)"),
]

PRODUCTION_PROFS = [
    ("Smithing", "ตีเหล็ก (Smithing)"),
    ("Carpentry", "ช่างไม้ (Carpentry)"),
    ("Tailoring", "ตัดเย็บ (Tailoring)"),
    ("Chasing", "แกะสลัก (Chasing)"),
    ("Alchemy", "เล่นแร่แปรธาตุ (Alchemy)"),
    ("Cooking", "ทำอาหาร (Cooking)"),
]

ZONE_EPS = [
    ("EP1", "Episode 1"),
    ("EP2", "Episode 2"),
    ("EP3", "Episode 3"),
    ("EP4", "Episode 4"),
    ("EP5", "Episode 5"),
    ("EP6", "Episode 6"),
    ("EP7", "Episode 7"),
    ("Raids", "Raids"),
    ("Events", "Events"),
]

EVENT_PAGES = [
    ("anniversary", "Anniversary (ครบรอบ)"),
    ("academy", "Academy Event (โรงเรียน)"),
    ("setsubun", "Setsubun (เซ็ตสึบุน)"),
    ("valentines_day", "Valentines Day (วาเลนไทน์)"),
    ("white_day", "White Day (ไวท์เดย์)"),
    ("easter", "Easter (อีสเตอร์)"),
    ("summer", "Summer (ฤดูร้อน)"),
    ("halloween", "Halloween (ฮาโลวีน)"),
    ("xmas", "Christmas (คริสต์มาส)"),
]

STATIC_GUIDE_PAGES = [
    ("pets", "สัตว์เลี้ยง (Pets Guide)"),
    ("stats", "ค่าสถานะ (Stats)"),
    ("abilities", "อบิลิตี้ (☆Abilities)"),
    ("apostolia", "อโพสโทเลีย (Apostolia)"),
    ("refinement", "การตีบวก (Refinement)"),
    ("raids", "เรดบอส (Raids)"),
    ("lottery", "ลอตเตอรี่ (Lottery)"),
    ("background_music", "เพลงประกอบ (Background Music)"),
]


def cache_path(rel_path: str) -> Path:
    h = hashlib.md5(rel_path.encode("utf-8")).hexdigest()
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", rel_path)[:50]
    return CACHE_DIR / f"{safe}_{h}.html"


def fetch_html(rel_path: str, retries: int = 3) -> str:
    cp = cache_path(rel_path)
    if cp.exists() and cp.stat().st_size > 2000:
        cached = cp.read_text(encoding="utf-8", errors="replace")
        if "</html>" in cached.lower():
            return cached

    encoded = urllib.parse.quote(rel_path, safe="/:?=&")
    url = BASE_URL + encoded
    for attempt in range(retries):
        try:
            r = subprocess.run(
                [
                    "curl.exe",
                    "-s",
                    "-L",
                    "--max-time",
                    "120",
                    "-A",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    url,
                ],
                capture_output=True,
                timeout=130,
            )
            html = r.stdout.decode("utf-8", errors="replace")
            if len(html) > 2000 and "</html>" in html.lower():
                cp.write_text(html, encoding="utf-8")
                return html
        except Exception as e:
            print(f"  [warn] attempt {attempt+1} failed for {rel_path}: {e}", flush=True)
        time.sleep(1.5 * (attempt + 1))
    return ""


def get_main_div(soup: BeautifulSoup):
    main = soup.find("div", class_="col-md-7") or soup.find("div", class_="col-md-9")
    if not main:
        return None
    for t in main.find_all(["script", "ins", "iframe", "style"]):
        t.decompose()
    return main


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def slug_from_href(href: str, prefix: str) -> str:
    if not href:
        return ""
    href = urllib.parse.unquote(href).strip()
    if href.startswith("/iruna/"):
        href = href[len("/iruna/"):]
    if href.startswith(prefix):
        return href[len(prefix):].split("#")[0].strip()
    return href.split("#")[0].strip()


def rewrite_href(href: str) -> str:
    """Rewrite relative links from th.iruna-online.info to our local pages."""
    if not href:
        return "#"
    raw = href.strip()
    if raw.startswith("http://www.iruna-online.info/item/") or raw.startswith("https://www.iruna-online.info/item/"):
        slug = raw.split("/item/", 1)[1]
        return f"db_items.html?item={urllib.parse.quote(slug)}"
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/iruna/"):
        raw = raw[len("/iruna/"):]
    if raw.startswith("bgm/"):
        return BASE_URL + raw
    if raw.startswith("item/"):
        return f"db_items.html?item={urllib.parse.quote(raw[5:])}"
    if raw.startswith("monster/"):
        return f"db_search.html?q={urllib.parse.quote(raw[8:])}"
    if raw.startswith("zone/"):
        return f"db_zones.html?zone={urllib.parse.quote(raw[5:])}"
    if raw.startswith("zones/"):
        ep = raw[6:].split("#")[0]
        ep_map = {"ep_1": "EP1", "ep_2": "EP2", "ep_3": "EP3", "ep_4": "EP4", "ep_5": "EP5", "ep_6": "EP6", "ep_7": "EP7", "ep_10": "Events"}
        ep = ep_map.get(ep.lower(), ep)
        return f"db_zones.html?ep={urllib.parse.quote(ep)}"
    if raw.startswith("blacksmith/"):
        return f"db_zones.html?blacksmith={urllib.parse.quote(raw[11:])}"
    if raw.startswith("quest/"):
        return f"db_quests.html?q={urllib.parse.quote(raw[6:].replace('_', ' '))}"
    if raw.startswith("class/") or raw.startswith("classes/"):
        cls = raw.split("/", 1)[1]
        return f"db_guide.html?page=classes&class={urllib.parse.quote(cls)}"
    if raw.startswith("skills/") or raw.startswith("skill/"):
        sk = raw.split("/", 1)[1]
        return f"db_guide.html?page=skills&class={urllib.parse.quote(sk)}"
    if raw.startswith("abilities2/"):
        return f"db_guide.html?page=abilities2&ability={urllib.parse.quote(raw[11:])}"
    if raw.startswith("productionsen/") or raw.startswith("productionsjp/"):
        prof = raw.split("/")[1]
        return f"db_production.html?prof={urllib.parse.quote(prof)}"
    if raw.startswith("items/"):
        return f"db_items.html?cat={urllib.parse.quote(raw[6:])}"
    if raw.startswith("npc/"):
        return f"db_quests.html?q={urllib.parse.quote(raw[4:].replace('_', ' '))}"
    return "#"


def sanitize_html_fragment(node: Tag) -> str:
    """Clean a BeautifulSoup node for embedding in our dark UI."""
    # Remove search forms and ad wrappers
    for form in node.find_all("form", id="form1"):
        form.decompose()
    for div in node.find_all("div", class_="container-fluid"):
        if not div.get_text(strip=True) and not div.find("img") and not div.find("table"):
            div.decompose()
    for div in node.find_all("div", class_="divider"):
        if not div.get_text(strip=True):
            div.decompose()
    for inp in node.find_all("input"):
        inp.decompose()
    for a in node.find_all("a", href=True):
        href = a["href"]
        new_href = rewrite_href(href)
        a["href"] = new_href
        if new_href.startswith("http"):
            a["target"] = "_blank"
            a["rel"] = "noopener"
    for img in node.find_all("img", src=True):
        src = img["src"]
        if not src.startswith("http"):
            img["src"] = BASE_URL + src.lstrip("/")
        img["loading"] = "lazy"
        img["onerror"] = "this.style.display='none'"
    # Remove inline colors that clash with dark theme
    for el in node.find_all(style=True):
        st = el["style"]
        st = re.sub(r"color\s*:\s*[^;]+;?", "", st, flags=re.I)
        st = re.sub(r"background(-color)?\s*:\s*[^;]+;?", "", st, flags=re.I)
        if st.strip():
            el["style"] = st
        else:
            del el["style"]
    return str(node)


# =============================================================================
# 1. SCRAPE ITEMS & EQUIPMENT
# =============================================================================
def parse_items_page(html: str, cat_key: str):
    soup = BeautifulSoup(html, "html.parser")
    main = get_main_div(soup)
    if not main:
        return [], []

    # Extract available attribute filter buttons (only need once)
    attr_filters = []
    fs = main.find(id="fs")
    if fs:
        for btn in fs.find_all("input", type="button"):
            oc = btn.get("onclick", "")
            m = re.search(r"filter_items\(['\"]([^'\"]+)['\"]\)", oc)
            if m:
                attr_filters.append({"key": m.group(1), "label": btn.get("value", m.group(1))})

    items = []
    seen = set()
    for div in main.find_all("div", class_="default_attr"):
        a = div.find("a", href=lambda h: h and h.startswith("item/"))
        if not a:
            continue
        slug = slug_from_href(a["href"], "item/")
        if not slug or slug in seen:
            continue
        seen.add(slug)

        raw_title = a.get_text(" ", strip=True)
        has_img = "📷" in raw_title
        name = re.sub(r"\s*\[[^\]]+\]\s*📷?\s*$", "", raw_title).strip()
        name = name.replace("📷", "").strip()

        classes = [c for c in (div.get("class") or []) if c not in ("default_attr", cat_key)]

        ds_el = div.find("div", class_="ds")
        tds_el = div.find("div", class_="t_ds")
        desc_th = ds_el.get_text("\n", strip=True) if ds_el else ""
        desc_en = tds_el.get_text(" ", strip=True) if tds_el else ""

        # Extract ATK, DEF, Notes from direct text nodes
        atk = None
        defense = None
        notes = ""
        direct_texts = []
        for child in div.children:
            if isinstance(child, NavigableString):
                t = str(child).strip()
                if t:
                    direct_texts.append(t)
        joined = "\n".join(direct_texts)
        m_atk = re.search(r"ATK:\s*([0-9~+\-]+)", joined)
        if m_atk:
            atk = m_atk.group(1)
        m_def = re.search(r"DEF:\s*([0-9~+\-]+)", joined)
        if m_def:
            defense = m_def.group(1)
        m_notes = re.search(r"Notes:\s*(.+)", joined, flags=re.S)
        if m_notes:
            notes = clean_text(m_notes.group(1))

        item_obj = {
            "slug": slug,
            "name": name,
            "cat": cat_key,
            "attrs": classes,
        }
        if atk:
            item_obj["atk"] = atk
        if defense:
            item_obj["def"] = defense
        if desc_th:
            item_obj["ds"] = desc_th
        if desc_en:
            item_obj["tds"] = desc_en
        if notes:
            item_obj["notes"] = notes
        if has_img:
            item_obj["hasImg"] = True
        items.append(item_obj)

    return items, attr_filters


def scrape_all_items():
    print("\n=== [1/6] Scraping Items & Equipment (24 categories) ===", flush=True)
    items_dir = OUT_DIR / "items"
    items_dir.mkdir(parents=True, exist_ok=True)

    all_cats = [(k, lbl, "equipment") for k, lbl in EQUIPMENT_CATS] + [
        (k, lbl, "item") for k, lbl in ITEM_CATS
    ]

    meta_cats = []
    attr_filters = []
    all_items_index = {}

    def work(entry):
        k, lbl, group = entry
        html = fetch_html(f"items/{k}")
        items, af = parse_items_page(html, k)
        return k, lbl, group, items, af

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for k, lbl, group, items, af in ex.map(work, all_cats):
            if af and not attr_filters:
                attr_filters = af
            (items_dir / f"{k}.json").write_text(
                json.dumps(items, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            meta_cats.append({"key": k, "label": lbl, "group": group, "count": len(items)})
            for it in items:
                all_items_index[it["slug"]] = {
                    "name": it["name"],
                    "cat": k,
                    "atk": it.get("atk"),
                    "def": it.get("def"),
                }
            print(f"  items/{k:15s}: {len(items):4d} items", flush=True)

    meta = {"categories": meta_cats, "attrFilters": attr_filters}
    (OUT_DIR / "items_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  Total items scraped: {len(all_items_index)}", flush=True)
    return all_items_index


# =============================================================================
# 2. SCRAPE PRODUCTION (6 professions x 6 ranges = 36 pages)
# =============================================================================
def parse_production_page(html: str, prof_key: str):
    soup = BeautifulSoup(html, "html.parser")
    main = get_main_div(soup)
    if not main:
        return []

    # Find container div after <b>Production</b>
    prod_header = None
    for b in main.find_all("b"):
        if b.get_text(strip=True) == "Production":
            prod_header = b
            break
    if not prod_header:
        return []
    row_div = prod_header.find_parent("div", class_="row")
    if not row_div:
        return []
    container = row_div.find_next_sibling("div")
    if not container:
        return []

    recipes = []
    # Split container children by <b><a href="item/...">
    current = None
    mode = None  # None, 'mat', 'successA', 'successB'

    for node in container.children:
        if isinstance(node, Tag) and node.name == "b":
            a = node.find("a", href=lambda h: h and h.startswith("item/"))
            if a:
                if current:
                    recipes.append(current)
                slug = slug_from_href(a["href"], "item/")
                txt = a.get_text(" ", strip=True)
                # e.g. "帯電する刃 x1 [Collectibles]"
                m = re.match(r"^(.*?)\s+x(\d+)\s*\[([^\]]+)\]", txt)
                if m:
                    iname, qty, itype = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
                else:
                    iname, qty, itype = txt, 1, ""
                current = {
                    "slug": slug,
                    "name": iname,
                    "qty": qty,
                    "type": itype,
                    "prof": prof_key,
                    "lv": 0,
                    "mats": [],
                }
                mode = None
        elif current is not None:
            if isinstance(node, NavigableString):
                t = str(node).strip()
                if not t:
                    continue
                m_lv = re.search(r"Lv\s*(\d+)", t)
                if m_lv and current["lv"] == 0:
                    current["lv"] = int(m_lv.group(1))
                elif "Success A:" in t:
                    mode = "successA"
                elif "Success B:" in t:
                    mode = "successB"
                elif re.match(r"^\d+:$", t):
                    mode = "mat"
            elif isinstance(node, Tag) and node.name == "a" and node.get("href", "").startswith("item/"):
                mslug = slug_from_href(node["href"], "item/")
                mtxt = node.get_text(" ", strip=True)
                mm = re.match(r"^(.*?)\s+x(\d+)$", mtxt)
                if mm:
                    mname, mqty = mm.group(1).strip(), int(mm.group(2))
                else:
                    mname, mqty = mtxt, 1
                entry = {"slug": mslug, "name": mname, "qty": mqty}
                if mode == "successA":
                    current["successA"] = entry
                    mode = None
                elif mode == "successB":
                    current["successB"] = entry
                    mode = None
                else:
                    current["mats"].append(entry)

    if current:
        recipes.append(current)
    return recipes


def scrape_all_production():
    print("\n=== [2/6] Scraping Production (6 professions x 6 tiers) ===", flush=True)
    prod_dir = OUT_DIR / "production"
    prod_dir.mkdir(parents=True, exist_ok=True)

    tasks = [(pk, tier) for pk, _ in PRODUCTION_PROFS for tier in range(1, 7)]
    by_prof = {pk: [] for pk, _ in PRODUCTION_PROFS}

    def work(task):
        pk, tier = task
        html = fetch_html(f"productionsen/{pk}/{tier}")
        return pk, tier, parse_production_page(html, pk)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for pk, tier, recs in ex.map(work, tasks):
            by_prof[pk].extend(recs)

    all_recipes = []
    meta = []
    for pk, lbl in PRODUCTION_PROFS:
        recs = by_prof[pk]
        # Deduplicate exact duplicates while preserving level-up/reinforce recipes
        seen = set()
        dedup = []
        for r in recs:
            key = (r["slug"], r["lv"], tuple((m["slug"], m["qty"]) for m in r["mats"]))
            if key not in seen:
                seen.add(key)
                dedup.append(r)
        dedup.sort(key=lambda x: (x["lv"], x["name"]))
        (prod_dir / f"{pk}.json").write_text(
            json.dumps(dedup, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        all_recipes.extend(dedup)
        meta.append({"key": pk, "label": lbl, "count": len(dedup)})
        print(f"  production/{pk:12s}: {len(dedup):4d} recipes", flush=True)

    (OUT_DIR / "production_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Also save compact production_all.json for the Materials Calculator
    (OUT_DIR / "production_all.json").write_text(
        json.dumps(all_recipes, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"  Total production recipes: {len(all_recipes)}", flush=True)
    return all_recipes


# =============================================================================
# 3. SCRAPE ZONES, MONSTERS, AND BLACKSMITHS
# =============================================================================
def parse_zone_tree_ul(ul_tag: Tag):
    """Parse zone tree handling both standard <ul><li> and unclosed <li> nesting."""
    nodes = []

    def parse_li(li: Tag):
        z_a = li.find("a", href=lambda h: h and h.startswith("zone/"), recursive=False)
        if not z_a:
            return []
        z_slug = slug_from_href(z_a["href"], "zone/")
        z_name = z_a.get_text(" ", strip=True)
        z_cls = (z_a.get("class") or ["zone_field"])[0]
        z_type = z_cls.replace("zone_", "")
        z_id = z_a.get("name", "")

        bs_a = li.find("a", href=lambda h: h and h.startswith("blacksmith/"), recursive=False)
        bs_slug = slug_from_href(bs_a["href"], "blacksmith/") if bs_a else None

        ep_a = li.find("a", href=lambda h: h and "/zones/" in h, recursive=False)
        cross_ep = clean_text(ep_a.get_text()) if ep_a else None

        children = []
        for sub_ul in li.find_all("ul", recursive=False):
            children.extend(parse_zone_tree_ul(sub_ul))

        node = {
            "slug": z_slug,
            "name": z_name,
            "type": z_type,
        }
        if z_id:
            node["id"] = z_id
        if bs_slug:
            node["blacksmith"] = bs_slug
        if cross_ep:
            node["crossEp"] = cross_ep
        if children:
            node["children"] = children

        result = [node]
        # Handle unclosed <li> tags that html.parser nested directly inside this <li>
        for direct_li in li.find_all("li", recursive=False):
            result.extend(parse_li(direct_li))
        return result

    for li in ul_tag.find_all("li", recursive=False):
        nodes.extend(parse_li(li))
    return nodes


def parse_monsters_from_container(container: Tag):
    monsters = []
    current = None
    last_img = ""
    in_drop = False

    for node in container.children:
        if isinstance(node, Tag) and node.name == "img":
            src = node.get("src", "")
            if src:
                last_img = src
        elif isinstance(node, Tag) and node.name == "b":
            a = node.find("a", href=lambda h: h and h.startswith("monster/"))
            if a:
                if current:
                    monsters.append(current)
                mslug = slug_from_href(a["href"], "monster/")
                mtxt = a.get_text(" ", strip=True)
                mm = re.match(r"^(.*?)\s*\(Lv\s*([0-9?~+\-]+)\)$", mtxt)
                if mm:
                    mname, mlv = mm.group(1).strip(), mm.group(2).strip()
                else:
                    mname, mlv = mtxt, ""
                current = {
                    "slug": mslug,
                    "name": mname,
                    "lv": mlv,
                    "drops": [],
                }
                if last_img:
                    current["img"] = last_img
                    last_img = ""
                in_drop = False
        elif current is not None:
            if isinstance(node, NavigableString):
                t = str(node).strip()
                if not t:
                    continue
                if "Drop:" in t:
                    in_drop = True
                if "Attr:" in t:
                    in_drop = False
                    m = re.search(r"Attr:\s*([^\n]+)", t)
                    if m:
                        current["attr"] = m.group(1).strip()
                if "Weak:" in t:
                    in_drop = False
                    m = re.search(r"Weak:\s*([^\n]+)", t)
                    if m:
                        current["weak"] = m.group(1).strip()
                if "Aggr:" in t:
                    in_drop = False
                    m = re.search(r"Aggr:\s*([^\n]+)", t)
                    if m:
                        current["aggr"] = m.group(1).strip()
                if "EXP:" in t:
                    m = re.search(r"EXP:\s*([0-9,]+)", t)
                    if m:
                        current["exp"] = m.group(1).strip()
                if "HP:" in t:
                    m = re.search(r"HP:\s*([0-9,]+)", t)
                    if m:
                        current["hp"] = m.group(1).strip()
            elif isinstance(node, Tag) and node.name == "a":
                href = node.get("href", "")
                if href.startswith("item/"):
                    islug = slug_from_href(href, "item/")
                    iname = node.get_text(" ", strip=True)
                    current["drops"].append({"slug": islug, "name": iname})
                elif href.startswith("zone/"):
                    ztxt = clean_text(node.get_text(" ", strip=True))
                    # Check if subarea like "ตำหนักแห่งความมืด [Second Floor]"
                    m_sub = re.search(r"\[([^\]]+)\]", ztxt)
                    if m_sub:
                        current["area"] = m_sub.group(1).strip()
                    current["zoneName"] = re.sub(r"\s*\[[^\]]+\]", "", ztxt).strip()
                    current["zoneSlug"] = slug_from_href(href, "zone/")

    if current:
        monsters.append(current)
    return monsters


def parse_quests_from_main(main: Tag):
    quests = []
    current_zone = ""
    current_zone_slug = ""
    current_q = None

    rows = main.find_all("div", class_="row")
    for row in rows:
        if "divider" in (row.get("class") or []):
            if current_q:
                quests.append(current_q)
                current_q = None
            continue
        col = row.find("div", class_="col-md-12")
        if not col:
            continue

        h3 = col.find("h3")
        if h3:
            if current_q:
                quests.append(current_q)
                current_q = None
            current_zone = h3.get_text(" ", strip=True)
            za = col.find("a", href=lambda h: h and h.startswith("zone/"))
            current_zone_slug = slug_from_href(za["href"], "zone/") if za else ""
            continue

        qa = col.find("a", href=lambda h: h and h.startswith("quest/"))
        if qa and col.find("b"):
            if current_q:
                quests.append(current_q)
            raw_t = clean_text(qa.get_text(" ", strip=True))
            mq = ""
            m_mq = re.match(r"^\((MQ[^)]*)\)\s*(.+)$", raw_t)
            if m_mq:
                mq = m_mq.group(1).strip()
                title = m_mq.group(2).strip()
            else:
                title = raw_t
            current_q = {
                "slug": slug_from_href(qa["href"], "quest/"),
                "title": title,
                "zone": current_zone,
                "zoneSlug": current_zone_slug,
            }
            if mq:
                current_q["mq"] = mq
            continue

        if not current_q:
            continue

        txt = clean_text(col.get_text(" ", strip=True))
        if txt.startswith("Quest:"):
            current_q["desc"] = txt[len("Quest:"):].strip()
        elif txt.startswith("Skill Reward:"):
            current_q["skillReward"] = txt[len("Skill Reward:"):].strip()
        elif txt.startswith("Reward:"):
            rewards = []
            for a in col.find_all("a", href=lambda h: h and h.startswith("item/")):
                rewards.append({"slug": slug_from_href(a["href"], "item/"), "text": clean_text(a.get_text())})
            current_q["reward"] = txt[len("Reward:"):].strip()
            if rewards:
                current_q["rewardItems"] = rewards
        elif txt.startswith("Objective:"):
            objs = []
            for a in col.find_all("a", href=True):
                h = a["href"]
                if h.startswith("monster/"):
                    objs.append({"kind": "monster", "slug": slug_from_href(h, "monster/"), "text": clean_text(a.get_text())})
                elif h.startswith("item/"):
                    objs.append({"kind": "item", "slug": slug_from_href(h, "item/"), "text": clean_text(a.get_text())})
            if objs:
                current_q["objectives"] = objs
            elif len(txt) > len("Objective:"):
                current_q["objectiveText"] = txt[len("Objective:"):].strip()
        elif txt.startswith("Requirement:"):
            current_q["req"] = txt[len("Requirement:"):].strip()
        elif txt.startswith("Experience:"):
            current_q["exp"] = txt[len("Experience:"):].strip()
        elif txt.startswith("Location:"):
            za = col.find("a", href=lambda h: h and h.startswith("zone/"))
            na = col.find("a", href=lambda h: h and h.startswith("npc/"))
            if za:
                current_q["zone"] = clean_text(za.get_text())
                current_q["zoneSlug"] = slug_from_href(za["href"], "zone/")
            if na:
                current_q["npc"] = clean_text(na.get_text())

    if current_q:
        quests.append(current_q)
    return quests


def parse_zone_detail(html: str, z_slug: str):
    soup = BeautifulSoup(html, "html.parser")
    main = get_main_div(soup)
    if not main:
        return {"slug": z_slug, "name": z_slug, "monsters": [], "quests": []}

    h4 = main.find("h4")
    name = clean_text(h4.get_text()) if h4 else z_slug

    bs_a = main.find("a", href=lambda h: h and h.startswith("blacksmith/"))
    bs_slug = slug_from_href(bs_a["href"], "blacksmith/") if bs_a else None

    monsters = []
    for b in main.find_all("b"):
        if b.get_text(strip=True) == "Monsters":
            row = b.find_parent("div", class_="row")
            if row:
                cont = row.find_next_sibling("div")
                if cont:
                    monsters.extend(parse_monsters_from_container(cont))

    quests = parse_quests_from_main(main)
    for q in quests:
        if not q.get("zone"):
            q["zone"] = name
            q["zoneSlug"] = z_slug

    res = {"slug": z_slug, "name": name, "monsters": monsters}
    if quests:
        res["quests"] = quests
    if bs_slug:
        res["blacksmith"] = bs_slug
    return res


def parse_blacksmith_page(html: str, bs_slug: str):
    soup = BeautifulSoup(html, "html.parser")
    main = get_main_div(soup)
    if not main:
        return {"slug": bs_slug, "name": bs_slug, "categories": []}

    h4 = main.find("h4")
    name = clean_text(h4.get_text()).replace(" Blacksmith", "").strip() if h4 else bs_slug

    categories = []
    for tbl in main.find_all("table"):
        th = tbl.find("th")
        cat = clean_text(th.get_text()) if th else "Other"
        entries = []
        for tr in tbl.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            a = tds[0].find("a", href=lambda h: h and h.startswith("item/"))
            if not a:
                continue
            islug = slug_from_href(a["href"], "item/")
            iname = clean_text(a.get_text())
            stat_txt = clean_text(tds[1].get_text(" ", strip=True))
            entries.append({"slug": islug, "name": iname, "stats": stat_txt})
        if entries:
            categories.append({"cat": cat, "items": entries})
    return {"slug": bs_slug, "name": name, "categories": categories}


def scrape_all_zones_and_blacksmiths():
    print("\n=== [3/6] Scraping Zones (9 groups), All Zone Details & Blacksmiths ===", flush=True)
    zones_dir = OUT_DIR / "zones"
    zones_dir.mkdir(parents=True, exist_ok=True)

    ep_trees = {}
    ep_zone_slugs = {}
    all_zone_slugs = []
    seen_z = set()
    all_bs_slugs = []
    seen_bs = set()

    def collect_slugs(nodes, ep_list):
        for n in nodes:
            s = n["slug"]
            ep_list.append(s)
            if s not in seen_z:
                seen_z.add(s)
                all_zone_slugs.append(s)
            bs = n.get("blacksmith")
            if bs and bs not in seen_bs:
                seen_bs.add(bs)
                all_bs_slugs.append(bs)
            if n.get("children"):
                collect_slugs(n["children"], ep_list)

    for ep_key, ep_label in ZONE_EPS:
        html = fetch_html(f"zones/{ep_key}")
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        tree = []
        if main:
            for ul in main.find_all("ul", class_="tree"):
                tree.extend(parse_zone_tree_ul(ul))
            # Fallback: capture any zone/blacksmith links outside/missed by malformed HTML trees
            in_tree = set()
            def mark(ns):
                for n in ns:
                    in_tree.add(n["slug"])
                    if n.get("children"):
                        mark(n["children"])
            mark(tree)
            bs_by_id = {}
            for a in main.find_all("a", href=lambda h: h and h.startswith("blacksmith/")):
                bs_s = slug_from_href(a["href"], "blacksmith/")
                bs_by_id[a.get("name", "") or bs_s] = bs_s
            for a in main.find_all("a", href=lambda h: h and h.startswith("zone/")):
                z_s = slug_from_href(a["href"], "zone/")
                if z_s and z_s not in in_tree:
                    in_tree.add(z_s)
                    z_cls = (a.get("class") or ["zone_field"])[0]
                    node = {
                        "slug": z_s,
                        "name": a.get_text(" ", strip=True),
                        "type": z_cls.replace("zone_", ""),
                    }
                    zid = a.get("name", "")
                    if zid and zid in bs_by_id:
                        node["blacksmith"] = bs_by_id[zid]
                    tree.append(node)
        ep_trees[ep_key] = tree
        ep_list = []
        collect_slugs(tree, ep_list)
        ep_zone_slugs[ep_key] = list(dict.fromkeys(ep_list))
        print(f"  zones/{ep_key:6s}: {len(ep_zone_slugs[ep_key]):3d} zones in tree", flush=True)

    print(f"  Fetching {len(all_zone_slugs)} individual zone pages...", flush=True)
    zone_details = {}

    def work_zone(zslug):
        html = fetch_html(f"zone/{zslug}")
        return zslug, parse_zone_detail(html, zslug)

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for zslug, detail in ex.map(work_zone, all_zone_slugs):
            zone_details[zslug] = detail
            done += 1
            if done % 50 == 0 or done == len(all_zone_slugs):
                print(f"    zones fetched: {done}/{len(all_zone_slugs)}", flush=True)

    print(f"  Fetching {len(all_bs_slugs)} blacksmith pages...", flush=True)
    blacksmiths = {}

    def work_bs(bslug):
        html = fetch_html(f"blacksmith/{bslug}")
        return bslug, parse_blacksmith_page(html, bslug)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for bslug, bdata in ex.map(work_bs, all_bs_slugs):
            blacksmiths[bslug] = bdata

    # Save each EP file with its tree + its zone details
    zones_meta = []
    for ep_key, ep_label in ZONE_EPS:
        zmap = {s: zone_details[s] for s in ep_zone_slugs[ep_key] if s in zone_details}
        mon_count = sum(len(z.get("monsters", [])) for z in zmap.values())
        payload = {
            "ep": ep_key,
            "label": ep_label,
            "tree": ep_trees[ep_key],
            "zones": zmap,
        }
        (zones_dir / f"{ep_key}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        zones_meta.append({
            "key": ep_key,
            "label": ep_label,
            "zoneCount": len(zmap),
            "monsterCount": mon_count,
        })

    (OUT_DIR / "zones_meta.json").write_text(
        json.dumps(zones_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "blacksmiths.json").write_text(
        json.dumps(blacksmiths, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    # Zone slug -> EP lookup
    zone_to_ep = {}
    for ep_key, _ in ZONE_EPS:
        for s in ep_zone_slugs[ep_key]:
            if s not in zone_to_ep:
                zone_to_ep[s] = ep_key
    (OUT_DIR / "zone_ep_map.json").write_text(
        json.dumps(zone_to_ep, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"  Saved {len(zone_details)} zones & {len(blacksmiths)} blacksmiths!", flush=True)
    return zone_details, blacksmiths, zone_to_ep


# =============================================================================
# 4. SCRAPE QUESTS
# =============================================================================
def scrape_all_quests():
    print("\n=== [4/6] Scraping Quests ===", flush=True)
    ep_defs = [
        ("1", "Episode 1"),
        ("2", "Episode 2"),
        ("3", "Episode 3"),
        ("4", "Episode 4"),
        ("5", "Episode 5"),
        ("10", "Events"),
    ]
    all_ep_quests = []
    total = 0
    for ep_id, ep_label in ep_defs:
        html = fetch_html(f"quests/{ep_id}")
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        qs = parse_quests_from_main(main) if main else []
        if qs:
            all_ep_quests.append({"id": ep_id, "label": ep_label, "quests": qs})
            total += len(qs)
        print(f"  quests/{ep_id:2s} ({ep_label}): {len(qs)} quests", flush=True)

    (OUT_DIR / "quests.json").write_text(
        json.dumps(all_ep_quests, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"  Total quests scraped: {total}", flush=True)
    return all_ep_quests


# =============================================================================
# 5. SCRAPE EVENTS (9 pages)
# =============================================================================
def scrape_all_events():
    print("\n=== [5/6] Scraping Events (9 event pages) ===", flush=True)
    events = []
    for key, label in EVENT_PAGES:
        html = fetch_html(key)
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        monsters = []
        quests = []
        body_html = ""
        if main:
            # Extract structured monsters if present
            for b in main.find_all("b"):
                if b.get_text(strip=True) == "Monsters":
                    row = b.find_parent("div", class_="row")
                    if row:
                        cont = row.find_next_sibling("div")
                        if cont:
                            monsters.extend(parse_monsters_from_container(cont))
            quests = parse_quests_from_main(main)
            # Also store clean full HTML for any special event guides/tables/notes
            h4 = main.find("h4")
            if h4:
                h4.decompose()
            hr = main.find("hr")
            if hr:
                hr.decompose()
            body_html = sanitize_html_fragment(main)
        events.append({
            "key": key,
            "label": label,
            "monsterCount": len(monsters),
            "questCount": len(quests),
            "monsters": monsters,
            "quests": quests,
            "html": body_html,
        })
        print(f"  event/{key:15s}: {len(monsters):3d} monsters, {len(quests):2d} quests, html={len(body_html)}", flush=True)

    (OUT_DIR / "events.json").write_text(
        json.dumps(events, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return events


# =============================================================================
# 6. SCRAPE GUIDES (static guides + classes + skills + abilities2)
# =============================================================================
def scrape_all_guides():
    print("\n=== [6/6] Scraping All Guides (Static + Classes + Skills + Abilities2) ===", flush=True)
    guides_dir = OUT_DIR / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)

    # 6a. Static/Rich HTML guides
    for key, label in STATIC_GUIDE_PAGES:
        html = fetch_html(key)
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        body_html = ""
        if main:
            h4 = main.find("h4")
            if h4:
                h4.decompose()
            hr = main.find("hr")
            if hr:
                hr.decompose()
            body_html = sanitize_html_fragment(main)
        payload = {"key": key, "label": label, "html": body_html}
        (guides_dir / f"{key}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"  guide/{key:18s}: html={len(body_html)} chars", flush=True)

    # 6b. Classes + 24 class detail pages
    cls_html = fetch_html("classes")
    cls_soup = BeautifulSoup(cls_html, "html.parser")
    cls_main = get_main_div(cls_soup)
    class_links = []
    seen_cls = set()
    if cls_main:
        for a in cls_main.find_all("a", href=True):
            h = a["href"]
            if h.startswith("class/") or h.startswith("classes/"):
                cname = h.split("/", 1)[1]
                if cname not in seen_cls:
                    seen_cls.add(cname)
                    class_links.append((cname, h))
        h4 = cls_main.find("h4")
        if h4:
            h4.decompose()
        hr = cls_main.find("hr")
        if hr:
            hr.decompose()
        tree_html = sanitize_html_fragment(cls_main)
    else:
        tree_html = ""

    def work_class(item):
        cname, path = item
        html = fetch_html(path)
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        body = ""
        if main:
            h4 = main.find("h4")
            if h4:
                h4.decompose()
            hr = main.find("hr")
            if hr:
                hr.decompose()
            body = sanitize_html_fragment(main)
        return cname, body

    class_details = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for cname, body in ex.map(work_class, class_links):
            class_details[cname] = body

    (guides_dir / "classes.json").write_text(
        json.dumps(
            {
                "key": "classes",
                "label": "ข้อมูลอาชีพ (Classes)",
                "treeHtml": tree_html,
                "classList": [c for c, _ in class_links],
                "details": class_details,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"  guide/classes           : {len(class_details)} classes scraped", flush=True)

    # 6c. Skills (23 classes)
    sk_html = fetch_html("skills")
    sk_soup = BeautifulSoup(sk_html, "html.parser")
    sk_main = get_main_div(sk_soup)
    skill_classes = []
    if sk_main:
        sel = sk_main.find("select", id="class_name")
        if sel:
            for opt in sel.find_all("option"):
                v = opt.get("value", "").strip()
                if v:
                    skill_classes.append(v)

    def work_skill_class(cname):
        html = fetch_html(f"skills/{cname}")
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        body = ""
        if main:
            for el in main.find_all(["h4", "hr", "select", "form"]):
                el.decompose()
            body = sanitize_html_fragment(main)
        return cname, body

    skills_by_class = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for cname, body in ex.map(work_skill_class, skill_classes):
            skills_by_class[cname] = body

    (guides_dir / "skills.json").write_text(
        json.dumps(
            {
                "key": "skills",
                "label": "สกิลทุกอาชีพ (Skills)",
                "classList": skill_classes,
                "byClass": skills_by_class,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"  guide/skills            : {len(skills_by_class)} classes scraped", flush=True)

    # 6d. Abilities2 (46 abilities)
    ab_html = fetch_html("abilities2")
    ab_soup = BeautifulSoup(ab_html, "html.parser")
    ab_main = get_main_div(ab_soup)
    ability_list = []
    if ab_main:
        sel = ab_main.find("select", id="ability_name")
        if sel:
            for opt in sel.find_all("option"):
                v = opt.get("value", "").strip()
                lbl = opt.get_text(strip=True)
                if v:
                    ability_list.append({"key": v, "label": lbl})

    def work_ability(entry):
        akey = entry["key"]
        html = fetch_html(f"abilities2/{akey}")
        soup = BeautifulSoup(html, "html.parser")
        main = get_main_div(soup)
        body = ""
        if main:
            for el in main.find_all(["h4", "hr", "select", "form"]):
                el.decompose()
            body = sanitize_html_fragment(main)
        return akey, body

    abilities_data = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for akey, body in ex.map(work_ability, ability_list):
            abilities_data[akey] = body

    (guides_dir / "abilities2.json").write_text(
        json.dumps(
            {
                "key": "abilities2",
                "label": "อบิลิตี้ ค้นหาดรอป (Abilities Beta)",
                "list": ability_list,
                "details": abilities_data,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"  guide/abilities2        : {len(abilities_data)} abilities scraped", flush=True)
    return ability_list


# =============================================================================
# 7. BUILD CROSS-REFERENCE & GLOBAL SEARCH INDEX
# =============================================================================
def build_indexes(all_items_index, all_recipes, zone_details, blacksmiths, zone_to_ep, all_ep_quests, ability_list):
    print("\n=== [7/7] Building Cross-Reference & Global Search Index ===", flush=True)

    # item_xref: slug -> {drops: [...], bs: [...], prod: [...], usedIn: [...], quests: [...]}
    xref = {}

    def ensure(slug):
        if slug not in xref:
            xref[slug] = {}
        return xref[slug]

    # From Monsters in Zones
    monster_search = []
    seen_mon_search = set()
    for zslug, z in zone_details.items():
        zname = z["name"]
        ep = zone_to_ep.get(zslug, "")
        for m in z.get("monsters", []):
            mkey = (m["name"], m.get("lv", ""), zslug)
            if mkey not in seen_mon_search:
                seen_mon_search.add(mkey)
                monster_search.append({
                    "t": "m",
                    "n": m["name"],
                    "lv": m.get("lv", ""),
                    "z": zname,
                    "zs": zslug,
                    "ep": ep,
                    "a": m.get("attr", ""),
                })
            for d in m.get("drops", []):
                entry = ensure(d["slug"])
                entry.setdefault("drops", []).append({
                    "m": m["name"],
                    "lv": m.get("lv", ""),
                    "z": zname,
                    "zs": zslug,
                    "ep": ep,
                    "area": m.get("area", ""),
                })

    # Deduplicate drops per item
    for slug, info in xref.items():
        if "drops" in info:
            seen_d = set()
            clean_d = []
            for d in info["drops"]:
                k = (d["m"], d["lv"], d["zs"], d["area"])
                if k not in seen_d:
                    seen_d.add(k)
                    clean_d.append(d)
            info["drops"] = clean_d

    # From Blacksmiths
    for bslug, bs in blacksmiths.items():
        bname = bs["name"]
        for cat_obj in bs.get("categories", []):
            for it in cat_obj.get("items", []):
                entry = ensure(it["slug"])
                entry.setdefault("bs", []).append({
                    "town": bname,
                    "bsSlug": bslug,
                    "cat": cat_obj["cat"],
                })

    # From Production
    for r in all_recipes:
        entry = ensure(r["slug"])
        entry.setdefault("prod", []).append({
            "prof": r["prof"],
            "lv": r["lv"],
            "qty": r["qty"],
            "mats": r["mats"],
        })
        for mat in r.get("mats", []):
            mentry = ensure(mat["slug"])
            mentry.setdefault("usedIn", []).append({
                "slug": r["slug"],
                "name": r["name"],
                "prof": r["prof"],
                "lv": r["lv"],
                "qty": mat["qty"],
            })

    # From Quests
    quest_search = []
    for ep_obj in all_ep_quests:
        for q in ep_obj.get("quests", []):
            quest_search.append({
                "t": "q",
                "n": q["title"],
                "z": q.get("zone", ""),
                "ep": ep_obj["label"],
                "npc": q.get("npc", ""),
            })
            for ri in q.get("rewardItems", []):
                entry = ensure(ri["slug"])
                entry.setdefault("quests", []).append({
                    "title": q["title"],
                    "zone": q.get("zone", ""),
                    "role": "reward",
                })

    (OUT_DIR / "item_xref.json").write_text(
        json.dumps(xref, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    # Global Search Index (items + zones + monsters + quests + abilities)
    search_items = []
    for slug, it in all_items_index.items():
        search_items.append({
            "t": "i",
            "s": slug,
            "n": it["name"],
            "c": it["cat"],
        })
    zone_search = [
        {"t": "z", "s": zslug, "n": z["name"], "ep": zone_to_ep.get(zslug, ""), "mc": len(z.get("monsters", []))}
        for zslug, z in zone_details.items()
    ]
    ab_search = [{"t": "a", "s": a["key"], "n": f"☆{a['label']}"} for a in ability_list]

    search_payload = {
        "items": search_items,
        "zones": zone_search,
        "monsters": monster_search,
        "quests": quest_search,
        "abilities": ab_search,
    }
    (OUT_DIR / "search_index.json").write_text(
        json.dumps(search_payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    stats = {
        "items": len(search_items),
        "zones": len(zone_search),
        "monsters": len(monster_search),
        "blacksmiths": len(blacksmiths),
        "productionRecipes": len(all_recipes),
        "quests": len(quest_search),
        "events": len(EVENT_PAGES),
        "abilities": len(ab_search),
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (OUT_DIR / "db_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("  DB Stats:", json.dumps(stats, ensure_ascii=False), flush=True)


def main():
    t0 = time.time()
    all_items_index = scrape_all_items()
    all_recipes = scrape_all_production()
    zone_details, blacksmiths, zone_to_ep = scrape_all_zones_and_blacksmiths()
    all_ep_quests = scrape_all_quests()
    scrape_all_events()
    ability_list = scrape_all_guides()
    build_indexes(all_items_index, all_recipes, zone_details, blacksmiths, zone_to_ep, all_ep_quests, ability_list)
    print(f"\nALL DONE in {time.time() - t0:.1f}s!", flush=True)


if __name__ == "__main__":
    main()
