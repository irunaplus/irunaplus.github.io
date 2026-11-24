#!/usr/bin/env python3
"""
Translate all remaining English text across data/db/ into natural Thai
while keeping familiar Iruna Online game stats (ATK, MATK, DEF, STR, INT, etc.).
"""

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = REPO_ROOT / "data" / "db"

# =============================================================================
# 1. DICTIONARIES (ELEMENTS, AGGR, CATEGORIES, CLASSES, ABILITIES, ATTR FILTERS)
# =============================================================================
ELEMENT_TH = {
    "Fire": "ไฟ",
    "Water": "น้ำ",
    "Wind": "ลม",
    "Earth": "ดิน",
    "Light": "แสง",
    "Dark": "มืด",
    "Neutral": "ไร้ธาตุ",
    "None": "ไร้ธาตุ",
}

CAT_TH = {
    "Swords": "ดาบ",
    "Bows": "ธนู",
    "Canes": "ไม้เท้า",
    "Claws": "กรงเล็บ",
    "Throwing": "อาวุธขว้าง",
    "Armor": "ชุดเกราะ",
    "Additional": "อุปกรณ์เสริม",
    "Additional Equipment": "อุปกรณ์เสริม",
    "Special": "อุปกรณ์พิเศษ",
    "Special Equipment": "อุปกรณ์พิเศษ",
    "Crystas": "คริสต้า ◇",
    "AlCrystas": "อัลคริสต้า ▲",
    "RelicCrystas": "เรลิกคริสต้า □",
    "Recovery": "ฟื้นฟู",
    "Status": "แก้สถานะ",
    "Strengthening": "เพิ่มพลัง/บัฟ",
    "Teleport": "วาร์ป",
    "Skills": "หนังสือสกิล",
    "Chests": "กล่องสมบัติ",
    "Collectibles": "ของสะสม/วัตถุดิบ",
    "Ores": "แร่ตีบวก",
    "IslandItems": "ของแต่งเกาะ",
    "Points": "ไอเทมช็อป",
    "Pets": "สัตว์เลี้ยง",
    "Fish": "ปลา/ตกปลา",
    "Other": "อื่นๆ",
}

PROF_TH = {
    "Smithing": "ตีเหล็ก",
    "Carpentry": "ช่างไม้",
    "Tailoring": "ตัดเย็บ",
    "Chasing": "แกะสลัก",
    "Alchemy": "เล่นแร่แปรธาตุ",
    "Cooking": "ทำอาหาร",
}

CLASS_TH = {
    "Adventurer": "นักผจญภัย (Adventurer)",
    "App. Warrior": "นักรบฝึกหัด (App. Warrior)",
    "App Warrior": "นักรบฝึกหัด (App. Warrior)",
    "Apprentice Warrior": "นักรบฝึกหัด (Apprentice Warrior)",
    "Warrior": "นักรบ (Warrior)",
    "App. Knight": "อัศวินฝึกหัด (App. Knight)",
    "App Knight": "อัศวินฝึกหัด (App. Knight)",
    "Apprentice Knight": "อัศวินฝึกหัด (Apprentice Knight)",
    "Knight": "อัศวิน (Knight)",
    "App. Paladin": "พาลาดินฝึกหัด (App. Paladin)",
    "App Paladin": "พาลาดินฝึกหัด (App. Paladin)",
    "Paladin": "พาลาดิน (Paladin)",
    "App. Gladiator": "แกลดิเอเตอร์ฝึกหัด (App. Gladiator)",
    "App Gladiator": "แกลดิเอเตอร์ฝึกหัด (App. Gladiator)",
    "Gladiator": "แกลดิเอเตอร์ (Gladiator)",
    "App. Beast Knight": "อัศวินอสูรฝึกหัด (App. Beast Knight)",
    "App Beast Knight": "อัศวินอสูรฝึกหัด (App. Beast Knight)",
    "Beast Knight": "อัศวินอสูร (Beast Knight)",
    "App. Hunter": "นักล่าฝึกหัด (App. Hunter)",
    "App Hunter": "นักล่าฝึกหัด (App. Hunter)",
    "Hunter": "นักล่า (Hunter)",
    "App. Assassin": "แอสซาซินฝึกหัด (App. Assassin)",
    "App Assassin": "แอสซาซินฝึกหัด (App. Assassin)",
    "Assassin": "แอสซาซิน (Assassin)",
    "App. Sniper": "สไนเปอร์ฝึกหัด (App. Sniper)",
    "App Sniper": "สไนเปอร์ฝึกหัด (App. Sniper)",
    "Sniper": "สไนเปอร์ (Sniper)",
    "App. Summoner": "ซัมมอนเนอร์ฝึกหัด (App. Summoner)",
    "App Summoner": "ซัมมอนเนอร์ฝึกหัด (App. Summoner)",
    "Summoner": "ซัมมอนเนอร์ (Summoner)",
    "App. Mage": "นักเวทฝึกหัด (App. Mage)",
    "App Mage": "นักเวทฝึกหัด (App. Mage)",
    "Mage": "นักเวท (Mage)",
    "App. Cleric": "นักบวชฝึกหัด (App. Cleric)",
    "App Cleric": "นักบวชฝึกหัด (App. Cleric)",
    "Cleric": "นักบวช (Cleric)",
    "App. Bishop": "บิชอปฝึกหัด (App. Bishop)",
    "App Bishop": "บิชอปฝึกหัด (App. Bishop)",
    "Bishop": "บิชอป (Bishop)",
    "App. Monk": "มังก์ฝึกหัด (App. Monk)",
    "App Monk": "มังก์ฝึกหัด (App. Monk)",
    "Monk": "มังก์ (Monk)",
    "App. Servant": "เซอร์แวนท์ฝึกหัด (App. Servant)",
    "App Servant": "เซอร์แวนท์ฝึกหัด (App. Servant)",
    "Servant": "เซอร์แวนท์ (Servant)",
    "App. Wizard": "จอมเวทฝึกหัด (App. Wizard)",
    "App Wizard": "จอมเวทฝึกหัด (App. Wizard)",
    "Wizard": "จอมเวท (Wizard)",
    "App. Enchanter": "เอ็นแชนเตอร์ฝึกหัด (App. Enchanter)",
    "App Enchanter": "เอ็นแชนเตอร์ฝึกหัด (App. Enchanter)",
    "Enchanter": "เอ็นแชนเตอร์ (Enchanter)",
    "App. High Wizard": "ไฮวิซาร์ดฝึกหัด (App. High Wizard)",
    "App High Wizard": "ไฮวิซาร์ดฝึกหัด (App. High Wizard)",
    "High Wizard": "ไฮวิซาร์ด (High Wizard)",
    "High_Wizard": "ไฮวิซาร์ด (High Wizard)",
    "App. Necromancer": "เนโครแมนเซอร์ฝึกหัด (App. Necromancer)",
    "App Necromancer": "เนโครแมนเซอร์ฝึกหัด (App. Necromancer)",
    "Necromancer": "เนโครแมนเซอร์ (Necromancer)",
    "Ninja": "นินจา (Ninja)",
    "Samurai": "ซามูไร (Samurai)",
    "Minstrel": "นักดนตรี (Minstrel)",
    "Alchemist": "นักแปรธาตุ (Alchemist)",
}

ABILITY_TH = {
    "accuracy": "ความแม่นยำ (Accuracy)",
    "agility": "ความว่องไว AGI (Agility)",
    "attack": "พลังโจมตี (Attack)",
    "autoskill": "ติดออโต้สกิล (Autoskill)",
    "buddy": "เพื่อนคู่ใจ/สัตว์เลี้ยง (Buddy)",
    "collector": "เพิ่มดรอป (Collector)",
    "critical": "อัตราคริติคอล (Critical)",
    "dark_blessing": "พรแห่งความมืด (Dark Blessing)",
    "dexterity": "ความชำนาญ DEX (Dexterity)",
    "earth_blessing": "พรแห่งดิน (Earth Blessing)",
    "evasion": "หลบหลีก (Evasion)",
    "fatal": "ดาเมจคริติคอล (Fatal)",
    "fire_blessing": "พรแห่งไฟ (Fire Blessing)",
    "fixed_magic": "พลังเวทคงที่ (Fixed Magic)",
    "fixed_melee": "พลังกายภาพคงที่ (Fixed Melee)",
    "fluency": "ลดเวลาร่าย (Fluency)",
    "freeze": "แช่แข็ง (Freeze)",
    "gentleness": "ลดค่าเกลียดชัง (Gentleness)",
    "heal": "เพิ่มพลังฮีล (Heal)",
    "heal_reward": "รับฮีลแรงขึ้น (Heal Reward)",
    "hp": "พลังชีวิต HP (HP)",
    "intelligence": "สติปัญญา INT (Intelligence)",
    "light_blessing": "พรแห่งแสง (Light Blessing)",
    "magic": "พลังเวท MATK (Magic)",
    "magic_defense": "ป้องกันเวท MDEF (Magic Defense)",
    "magic_pierce": "เจาะเกราะเวท (Magic Pierce)",
    "melee_defense": "ป้องกันกายภาพ DEF (Melee Defense)",
    "melee_pierce": "เจาะเกราะกายภาพ (Melee Pierce)",
    "mp": "มานา MP (MP)",
    "mp_cost": "ลดการใช้ MP (MP Cost)",
    "pharmacy": "เพิ่มผลยาฟื้นฟู (Pharmacy)",
    "provoke": "เพิ่มค่าเกลียดชัง (Provoke)",
    "quick_cool": "ลดดีเลย์สกิล (Quick Cool)",
    "quick_use": "ลดดีเลย์ไอเทม (Quick Use)",
    "range_cut": "ลดดาเมจระยะไกล (Range Cut)",
    "rate_cut": "ลดดาเมจ % (Rate Cut)",
    "reflect": "สะท้อนดาเมจ (Reflect)",
    "regenerate": "ฟื้นฟูอัตโนมัติ (Regenerate)",
    "spell_burst": "สเปลเบิร์สต์ (Spell Burst)",
    "strength": "พละกำลัง STR (Strength)",
    "striver": "เพิ่ม EXP (Striver)",
    "technique": "เทคนิค CRT (Technique)",
    "vitality": "ความอึด VIT (Vitality)",
    "water_blessing": "พรแห่งน้ำ (Water Blessing)",
    "wild_dance": "เร่งความเร็วโจมตี (Wild Dance)",
    "wind_blessing": "พรแห่งลม (Wind Blessing)",
}

ATTR_FILTERS_TH = [
    ("atk", "ATK (โจมตีกายภาพ)"),
    ("matk", "MATK (โจมตีเวท)"),
    ("def", "DEF (ป้องกันกายภาพ)"),
    ("mdef", "MDEF (ป้องกันเวท)"),
    ("str", "STR"),
    ("int", "INT"),
    ("vit", "VIT"),
    ("agi", "AGI"),
    ("dex", "DEX"),
    ("crt", "CRT"),
    ("maxhp", "MaxHP"),
    ("maxmp", "MaxMP"),
    ("criticalrate", "อัตราคริติคอล"),
    ("criticaldamage", "ดาเมจคริติคอล"),
    ("autoskill", "ติดออโต้สกิล"),
    ("spellburst", "สเปลเบิร์สต์"),
    ("skilldelay", "ดีเลย์สกิล"),
    ("itemdelay", "ดีเลย์ไอเทม"),
    ("casttime", "เวลาร่ายเวท"),
    ("aspd", "ความเร็วโจมตี (ASPD)"),
    ("mpcost", "การใช้ MP"),
    ("meleer", "ต้านกายภาพ"),
    ("magicr", "ต้านเวท"),
    ("alldamager", "ต้านดาเมจทั้งหมด"),
    ("ratecut", "ลดดาเมจ % (Rate Cut)"),
    ("rangecut", "ลดดาเมจระยะไกล"),
    ("damagecut", "ลดดาเมจคงที่"),
    ("meleepierce", "เจาะเกราะกายภาพ"),
    ("magicpierce", "เจาะเกราะเวท"),
    ("shellbreak", "อัตราเจาะเกราะ (Shell Break)"),
    ("accuracy", "ความแม่นยำ"),
    ("absoluteaccuracy", "แม่นยำสัมบูรณ์"),
    ("evasion", "หลบหลีก"),
    ("absoluteevasion", "หลบหลีกสัมบูรณ์"),
    ("magicevasion", "หลบหลีกเวท"),
    ("haterise", "ค่าเกลียดชัง (Hate)"),
    ("ailmentr", "ต้านสถานะผิดปกติ"),
    ("castdefense", "ป้องกันขณะร่าย"),
    ("healrecovery", "เพิ่มพลังฮีล"),
    ("healreward", "รับฮีลแรงขึ้น"),
    ("itemrecovery", "ผลฟื้นฟูจากไอเทม"),
    ("autohprecovery", "ฟื้นฟู HP อัตโนมัติ"),
    ("automprecovery", "ฟื้นฟู MP อัตโนมัติ"),
    ("reflect", "สะท้อนดาเมจ"),
    ("counteronevasion", "สวนกลับเมื่อหลบได้"),
    ("range", "ระยะโจมตี"),
    ("meleeboss", "โจมตีบอส (กายภาพ)"),
    ("magicboss", "โจมตีบอส (เวท)"),
    ("meleetofire", "กายภาพต่อธาตุไฟ"),
    ("meleetowater", "กายภาพต่อธาตุน้ำ"),
    ("meleetowind", "กายภาพต่อธาตุลม"),
    ("meleetoearth", "กายภาพต่อธาตุดิน"),
    ("meleetolight", "กายภาพต่อธาตุแสง"),
    ("meleetodark", "กายภาพต่อธาตุมืด"),
    ("meleetoneutral", "กายภาพต่อไร้ธาตุ"),
    ("firemagic", "เวทธาตุไฟ"),
    ("watermagic", "เวทธาตุน้ำ"),
    ("windmagic", "เวทธาตุลม"),
    ("earthmagic", "เวทธาตุดิน"),
    ("lightmagic", "เวทธาตุแสง"),
    ("darkmagic", "เวทธาตุมืด"),
    ("neutralmagic", "เวทไร้ธาตุ"),
    ("firer", "ต้านธาตุไฟ"),
    ("waterr", "ต้านธาตุน้ำ"),
    ("windr", "ต้านธาตุลม"),
    ("earthr", "ต้านธาตุดิน"),
    ("lightr", "ต้านธาตุแสง"),
    ("darkr", "ต้านธาตุมืด"),
    ("neutralr", "ต้านไร้ธาตุ"),
    ("exp", "เพิ่ม EXP"),
    ("drop", "เพิ่มอัตราดรอป"),
    ("pet", "เกี่ยวกับสัตว์เลี้ยง"),
    ("poison", "พิษ (Poison)"),
    ("paralysis", "อัมพาต (Paralysis)"),
    ("bleed", "เลือดไหล (Bleed)"),
    ("burn", "เผาไหม้ (Burn)"),
    ("knockout", "มึนงง/สตั๊น"),
]

# =============================================================================
# 2. STAT & FORMULA TRANSLATOR (ordered longest-first to avoid partial matches)
# =============================================================================
STAT_REPLACEMENTS = [
    # Full stat phrases
    (r"\bMelee to Neutral\b", "โจมตีกายภาพต่อไร้ธาตุ"),
    (r"\bMelee to Fire\b", "โจมตีกายภาพต่อธาตุไฟ"),
    (r"\bMelee to Water\b", "โจมตีกายภาพต่อธาตุน้ำ"),
    (r"\bMelee to Wind\b", "โจมตีกายภาพต่อธาตุลม"),
    (r"\bMelee to Earth\b", "โจมตีกายภาพต่อธาตุดิน"),
    (r"\bMelee to Light\b", "โจมตีกายภาพต่อธาตุแสง"),
    (r"\bMelee to Dark\b", "โจมตีกายภาพต่อธาตุมืด"),
    (r"\bMelee to Boss\b", "โจมตีกายภาพต่อบอส"),
    (r"\bMagic to Boss\b", "โจมตีเวทต่อบอส"),
    (r"\bMagic to Neutral\b", "โจมตีเวทต่อไร้ธาตุ"),
    (r"\bMagic to Fire\b", "โจมตีเวทต่อธาตุไฟ"),
    (r"\bMagic to Water\b", "โจมตีเวทต่อธาตุน้ำ"),
    (r"\bMagic to Wind\b", "โจมตีเวทต่อธาตุลม"),
    (r"\bMagic to Earth\b", "โจมตีเวทต่อธาตุดิน"),
    (r"\bMagic to Light\b", "โจมตีเวทต่อธาตุแสง"),
    (r"\bMagic to Dark\b", "โจมตีเวทต่อธาตุมืด"),
    (r"\bNeutral Magic\b", "เวทไร้ธาตุ"),
    (r"\bFire Magic\b", "เวทธาตุไฟ"),
    (r"\bWater Magic\b", "เวทธาตุน้ำ"),
    (r"\bWind Magic\b", "เวทธาตุลม"),
    (r"\bEarth Magic\b", "เวทธาตุดิน"),
    (r"\bLight Magic\b", "เวทธาตุแสง"),
    (r"\bDark Magic\b", "เวทธาตุมืด"),
    (r"\bAll Magic\b", "เวททุกธาตุ"),
    (r"\bAll damage R\b", "ต้านทานดาเมจทั้งหมด"),
    (r"\bAll element R\b", "ต้านทานทุกธาตุ"),
    (r"\bAll elements R\b", "ต้านทานทุกธาตุ"),
    (r"\bNeutral R\b", "ต้านไร้ธาตุ"),
    (r"\bFire R\b", "ต้านธาตุไฟ"),
    (r"\bWater R\b", "ต้านธาตุน้ำ"),
    (r"\bWind R\b", "ต้านธาตุลม"),
    (r"\bEarth R\b", "ต้านธาตุดิน"),
    (r"\bLight R\b", "ต้านธาตุแสง"),
    (r"\bDark R\b", "ต้านธาตุมืด"),
    (r"\bMelee R\b", "ต้านกายภาพ"),
    (r"\bMagic R\b", "ต้านเวท"),
    (r"\bAilment R\b", "ต้านสถานะผิดปกติ"),
    (r"\bPoison R\b", "ต้านพิษ"),
    (r"\bParalysis R\b", "ต้านอัมพาต"),
    (r"\bBlind R\b", "ต้านตาบอด"),
    (r"\bFreeze R\b", "ต้านแช่แข็ง"),
    (r"\bBurn R\b", "ต้านเผาไหม้"),
    (r"\bStun R\b", "ต้านมึนงง"),
    (r"\bBleed R\b", "ต้านเลือดไหล"),
    (r"\bFear R\b", "ต้านหวาดกลัว"),
    (r"\bDizzy R\b", "ต้านเวียนหัว"),
    (r"\bAbsolute Evasion\b", "หลบหลีกสัมบูรณ์"),
    (r"\bAbsolute evasion\b", "หลบหลีกสัมบูรณ์"),
    (r"\bAbsolute Accuracy\b", "แม่นยำสัมบูรณ์"),
    (r"\bAbsolute accuracy\b", "แม่นยำสัมบูรณ์"),
    (r"\bMagic Evasion\b", "หลบหลีกเวท"),
    (r"\bMagic evasion\b", "หลบหลีกเวท"),
    (r"\bMelee Pierce\b", "เจาะเกราะกายภาพ"),
    (r"\bMelee pierce\b", "เจาะเกราะกายภาพ"),
    (r"\bMagic Pierce\b", "เจาะเกราะเวท"),
    (r"\bMagic pierce\b", "เจาะเกราะเวท"),
    (r"\bPhysical Power\b", "พลังกายภาพคงที่"),
    (r"\bMagic Power\b", "พลังเวทคงที่"),
    (r"\bCritical rate\b", "อัตราคริติคอล"),
    (r"\bCritical Rate\b", "อัตราคริติคอล"),
    (r"\bCritical damage\b", "ดาเมจคริติคอล"),
    (r"\bCritical Damage\b", "ดาเมจคริติคอล"),
    (r"\bSkill Delay\b", "ดีเลย์สกิล"),
    (r"\bSkill delay\b", "ดีเลย์สกิล"),
    (r"\bItem Delay\b", "ดีเลย์ไอเทม"),
    (r"\bItem delay\b", "ดีเลย์ไอเทม"),
    (r"\bCast Time\b", "เวลาร่ายเวท"),
    (r"\bCast time\b", "เวลาร่ายเวท"),
    (r"\bCast Defense\b", "ป้องกันขณะร่าย"),
    (r"\bCast defense\b", "ป้องกันขณะร่าย"),
    (r"\bHate Rise\b", "เพิ่มค่าเกลียดชัง"),
    (r"\bHate rise\b", "เพิ่มค่าเกลียดชัง"),
    (r"\bHate\b", "ค่าเกลียดชัง"),
    (r"\bRate cut\b", "ลดดาเมจ %"),
    (r"\bRate Cut\b", "ลดดาเมจ %"),
    (r"\bRange cut\b", "ลดดาเมจระยะไกล"),
    (r"\bRange Cut\b", "ลดดาเมจระยะไกล"),
    (r"\bDamage cut\b", "ลดดาเมจคงที่"),
    (r"\bDamage Cut\b", "ลดดาเมจคงที่"),
    (r"\bAuto HP Recovery\b", "ฟื้นฟู HP อัตโนมัติ"),
    (r"\bAuto HP recovery\b", "ฟื้นฟู HP อัตโนมัติ"),
    (r"\bAuto MP Recovery\b", "ฟื้นฟู MP อัตโนมัติ"),
    (r"\bAuto MP recovery\b", "ฟื้นฟู MP อัตโนมัติ"),
    (r"\bNatural HP Recovery\b", "ฟื้นฟู HP ตามธรรมชาติ"),
    (r"\bNatural MP Recovery\b", "ฟื้นฟู MP ตามธรรมชาติ"),
    (r"\bHeal Recovery\b", "เพิ่มพลังฮีล"),
    (r"\bHeal recovery\b", "เพิ่มพลังฮีล"),
    (r"\bHeal Reward\b", "รับฮีลแรงขึ้น"),
    (r"\bHeal reward\b", "รับฮีลแรงขึ้น"),
    (r"\bItem Recovery\b", "ผลฟื้นฟูไอเทม"),
    (r"\bItem recovery\b", "ผลฟื้นฟูไอเทม"),
    (r"\bMP Cost\b", "การใช้ MP"),
    (r"\bMP cost\b", "การใช้ MP"),
    (r"\bMP Consumption\b", "การใช้ MP"),
    (r"\bAutoskill\b", "ติดออโต้สกิล"),
    (r"\bSpellburst\b", "สเปลเบิร์สต์"),
    (r"\bSpell burst\b", "สเปลเบิร์สต์"),
    (r"\bSpell Burst\b", "สเปลเบิร์สต์"),
    (r"\bShell Break\b", "อัตราเจาะเกราะ (Shell Break)"),
    (r"\bShell break\b", "อัตราเจาะเกราะ (Shell Break)"),
    (r"\bCounter on Evasion\b", "สวนกลับเมื่อหลบหลีก"),
    (r"\bCounter on evasion\b", "สวนกลับเมื่อหลบหลีก"),
    (r"\bReflect\b", "สะท้อนดาเมจ"),
    (r"\bRecoil\b", "ดาเมจสะท้อนกลับ"),
    (r"\bAccuracy\b", "ความแม่นยำ"),
    (r"\bEvasion\b", "หลบหลีก"),
    (r"\bRange\b", "ระยะโจมตี"),
    (r"\bDrop rate\b", "อัตราดรอป"),
    (r"\bDrop Rate\b", "อัตราดรอป"),
    (r"\bEXP\b", "EXP"),
    (r"\bPoison damage\b", "ดาเมจพิษ"),
    (r"\bPoison Damage\b", "ดาเมจพิษ"),
    (r"\bPoison duration\b", "ระยะเวลาพิษ"),
    (r"\bBleed damage\b", "ดาเมจเลือดไหล"),
    (r"\bBurn damage\b", "ดาเมจเผาไหม้"),
    (r"\bMelee\b", "พลังกายภาพ"),
    (r"\bMagic\b", "พลังเวท"),
    (r"\bNeutral\b", "ไร้ธาตุ"),
    (r"\bAttack Speed\b", "ความเร็วโจมตี"),
    (r"\bMovement Speed\b", "ความเร็วเคลื่อนที่"),
    (r"\bMove Speed\b", "ความเร็วเคลื่อนที่"),
    (r"\bPet ATK\b", "ATK สัตว์เลี้ยง"),
    (r"\bPet MATK\b", "MATK สัตว์เลี้ยง"),
    (r"\bPet MaxHP\b", "MaxHP สัตว์เลี้ยง"),
    (r"\bPet Heal\b", "ฮีลสัตว์เลี้ยง"),
    (r"\bPet Melee\b", "กายภาพสัตว์เลี้ยง"),
    (r"\bPet Magic\b", "เวทสัตว์เลี้ยง"),
    (r"\bPet\b", "สัตว์เลี้ยง"),
    (r"\bUnbreakable\b", "ไม่แตกเมื่อตีบวก"),
    (r"\bDouble Attack\b", "โจมตีสองครั้ง"),
    (r"\bDouble attack\b", "โจมตีสองครั้ง"),
    (r"\bAdditional attack\b", "โจมตีเพิ่มเติม"),
    (r"\bAdditional Attack\b", "โจมตีเพิ่มเติม"),
    (r"\bAdditional magic\b", "เวทโจมตีเพิ่มเติม"),
    # Formula keywords in True Stats
    (r"\bup by\b", "เพิ่มขึ้นตาม"),
    (r"\bdown by\b", "ลดลงตาม"),
    (r"\bIf\b", "ถ้า"),
    (r"\bthen\b", "จะได้รับ"),
    (r"\bUnknown\b", "เงื่อนไขพิเศษ"),
    (r"\bWhen equipped on\b", "เมื่อใส่ใน"),
    (r"\bOn Weapon\b", "เมื่อใส่ในอาวุธ"),
    (r"\bOn Armor\b", "เมื่อใส่ในชุดเกราะ"),
    (r"\bOn Additional\b", "เมื่อใส่ในอุปกรณ์เสริม"),
    (r"\bOn Special\b", "เมื่อใส่ในอุปกรณ์พิเศษ"),
    (r"\bWeapons\b", "อาวุธ"),
    (r"\bWeapon\b", "อาวุธ"),
    (r"\bArmor\b", "ชุดเกราะ"),
    (r"\bAdditional\b", "อุปกรณ์เสริม"),
    (r"\bSpecial\b", "อุปกรณ์พิเศษ"),
    (r"\bSwords\b", "ดาบ"),
    (r"\bBows\b", "ธนู"),
    (r"\bCanes\b", "ไม้เท้า"),
    (r"\bClaws\b", "กรงเล็บ"),
    (r"\bThrowing\b", "อาวุธขว้าง"),
    (r"\bRed Line\b", "เส้นสีแดง"),
    (r"\bBlue Line\b", "เส้นสีน้ำเงิน"),
    (r"\bGreen Line\b", "เส้นสีเขียว"),
    (r"\bYellow Line\b", "เส้นสีเหลือง"),
    (r"\bAqua Line\b", "เส้นสีฟ้า"),
    (r"\bPurple Line\b", "เส้นสีม่วง"),
    # Common notes terms
    (r"\bhidden correction:\b", "โบนัสซ่อน:"),
    (r"\bHidden correction:\b", "โบนัสซ่อน:"),
    (r"\bHidden stats:\b", "สเตตัสซ่อน:"),
    (r"\bTrade X\b", "แลกเปลี่ยนไม่ได้"),
    (r"\bUntradeable\b", "แลกเปลี่ยนไม่ได้"),
    (r"\bNot tradeable\b", "แลกเปลี่ยนไม่ได้"),
    (r"\bCannot be traded\b", "แลกเปลี่ยนไม่ได้"),
    (r"\bchance to\b", "มีโอกาส"),
    (r"\bChance to\b", "มีโอกาส"),
    (r"\bincreases\b", "เพิ่มขึ้น"),
    (r"\bdecreases\b", "ลดลง"),
    (r"\brestore\b", "ฟื้นฟู"),
    (r"\bRestores\b", "ฟื้นฟู"),
    (r"\bRestore\b", "ฟื้นฟู"),
    (r"\bRecovers\b", "ฟื้นฟู"),
    (r"\bRecover\b", "ฟื้นฟู"),
    (r"\bfor (\d+) min(?:utes?|s)?\b", r"เป็นเวลา \1 นาที"),
    (r"\bfor (\d+) sec(?:onds?|s)?\b", r"เป็นเวลา \1 วินาที"),
    (r"\bAll Stats\b", "ทุกสเตตัส"),
    (r"\bAll stats\b", "ทุกสเตตัส"),
    (r"\bElement\b", "ธาตุ"),
]
COMPILED_STAT_RULES = [(re.compile(p), r) for p, r in STAT_REPLACEMENTS]


def has_thai(s: str) -> bool:
    return any("\u0e00" <= c <= "\u0e7f" for c in (s or ""))


def translate_stat_text(s: str) -> str:
    if not s:
        return s
    out = s
    for pat, rep in COMPILED_STAT_RULES:
        out = pat.sub(rep, out)
    # Translate [ClassName] tags inside True Stats
    for en, th in CLASS_TH.items():
        if f"[{en}]" in out:
            out = out.replace(f"[{en}]", f"[{th.split(' (')[0]}]")
    return out


def translate_element(val: str) -> str:
    if not val:
        return val
    out = val
    for en, th in ELEMENT_TH.items():
        out = re.sub(rf"\b{en}\b", th, out)
    return out


def translate_aggr(val: str) -> str:
    if not val:
        return val
    out = val
    out = re.sub(r"Passive\s*BOSS", "บอส (ไม่โจมตีก่อน)", out, flags=re.I)
    out = re.sub(r"Under[\s\-]?Active", "โจมตีก่อน (ถ้าเลเวลต่ำกว่า)", out, flags=re.I)
    out = re.sub(r"Over[\s\-]?Active", "โจมตีก่อนตลอด", out, flags=re.I)
    out = re.sub(r"\bPassive\b", "ไม่โจมตีก่อน", out, flags=re.I)
    out = re.sub(r"\bActive\b", "โจมตีก่อน", out, flags=re.I)
    return out


def translate_area(val: str) -> str:
    if not val:
        return val
    m = {
        "First Floor": "ชั้น 1",
        "Second Floor": "ชั้น 2",
        "Third Floor": "ชั้น 3",
        "Fourth Floor": "ชั้น 4",
        "Fifth Floor": "ชั้น 5",
        "Basement": "ชั้นใต้ดิน",
        "Boss": "ห้องบอส",
        "Area 1": "พื้นที่ 1",
        "Area 2": "พื้นที่ 2",
        "Area 3": "พื้นที่ 3",
        "Area 4": "พื้นที่ 4",
        "East": "ทิศตะวันออก",
        "West": "ทิศตะวันตก",
        "North": "ทิศเหนือ",
        "South": "ทิศใต้",
        "Center": "ใจกลาง",
        "Entrance": "ทางเข้า",
        "Top": "ยอดสุด",
    }
    out = val
    for en, th in m.items():
        out = re.sub(rf"\b{re.escape(en)}\b", th, out)
    return out


# =============================================================================
# 3. HAND-CRAFTED NATURAL THAI STATIC GUIDES
# =============================================================================
THAI_GUIDES = {
    "stats": {
        "key": "stats",
        "label": "ค่าสถานะ (Stats)",
        "html": """
<h3>ค่าสถานะพื้นฐานตัวละคร</h3>
<table>
  <tr><th>ค่าสถานะ</th><th>คำอธิบาย</th></tr>
  <tr><td><strong>Level (เลเวล)</strong></td><td>ส่งผลต่อ MaxHP, MaxMP, ความแม่นยำ (HIT) และหลบหลีก (EVA)</td></tr>
  <tr><td><strong>HP</strong></td><td>พลังชีวิตสูงสุด (MaxHP)</td></tr>
  <tr><td><strong>MP</strong></td><td>มานาสูงสุด (MaxMP)</td></tr>
</table>

<h3>ค่าสถานะหลัก (Primary Stats)</h3>
<table>
  <tr><th>สเตตัส</th><th>คำอธิบาย</th></tr>
  <tr><td><strong>STR</strong></td><td>เพิ่มพลังโจมตีกายภาพ (ATK)</td></tr>
  <tr><td><strong>INT</strong></td><td>เพิ่มพลังโจมตีเวท (MATK), ป้องกันเวท (MDEF) และ MaxMP</td></tr>
  <tr><td><strong>VIT</strong></td><td>เพิ่มพลังชีวิตสูงสุด (MaxHP) และป้องกันกายภาพ (DEF)</td></tr>
  <tr><td><strong>AGI</strong></td><td>เพิ่มความเร็วในการโจมตี (ASPD) และค่าหลบหลีก (EVA)</td></tr>
  <tr><td><strong>DEX</strong></td><td>เพิ่มความเร็วในการร่ายเวท (CSPD) และความแม่นยำ (HIT)</td></tr>
  <tr><td><strong>CRT</strong></td><td>เพิ่มอัตราการติดคริติคอล (Critical Rate) และความแรงคริติคอล (Critical Damage)</td></tr>
</table>

<h3>ค่าสถานะรอง (Secondary Stats)</h3>
<table>
  <tr><th>สเตตัส</th><th>คำอธิบาย</th></tr>
  <tr><td><strong>ATK</strong></td><td>พลังโจมตีกายภาพ</td></tr>
  <tr><td><strong>MATK</strong></td><td>พลังโจมตีเวทมนตร์</td></tr>
  <tr><td><strong>DEF</strong></td><td>พลังป้องกันกายภาพ</td></tr>
  <tr><td><strong>MDEF</strong></td><td>พลังป้องกันเวทมนตร์</td></tr>
  <tr><td><strong>HIT</strong></td><td>ความแม่นยำ</td></tr>
  <tr><td><strong>EVA</strong></td><td>อัตราการหลบหลีก</td></tr>
  <tr><td><strong>ASPD</strong></td><td>ความเร็วในการโจมตีปกติ</td></tr>
  <tr><td><strong>CSPD</strong></td><td>ความเร็วในการร่ายเวท</td></tr>
</table>

<h3>ค่าสถานะขั้นสูง (Tertiary Stats)</h3>
<table>
  <tr><th>สเตตัส</th><th>คำอธิบาย</th></tr>
  <tr><td><strong>Critical Rate (อัตราคริติคอล)</strong></td><td>โอกาสโจมตีติดคริติคอล</td></tr>
  <tr><td><strong>Critical Damage (ดาเมจคริติคอล)</strong></td><td>ความแรงของการโจมตีเมื่อติดคริติคอล</td></tr>
  <tr><td><strong>Autoskill (ออโต้สกิล)</strong></td><td>โอกาสที่สกิลอัตโนมัติหรือเอฟเฟกต์โจมตีเสริมจะทำงาน</td></tr>
  <tr><td><strong>Skill Delay (ดีเลย์สกิล)</strong></td><td>ระยะเวลาหน่วงระหว่างการใช้สกิลแต่ละครั้ง</td></tr>
  <tr><td><strong>Item Delay (ดีเลย์ไอเทม)</strong></td><td>ระยะเวลาหน่วงระหว่างการกดใช้ไอเทมแต่ละครั้ง</td></tr>
  <tr><td><strong>Physical Power (พลังกายภาพคงที่)</strong></td><td>โบนัสดาเมจกายภาพที่บวกเพิ่มโดยตรง</td></tr>
  <tr><td><strong>Magic Power (พลังเวทคงที่)</strong></td><td>โบนัสดาเมจเวทที่บวกเพิ่มโดยตรง</td></tr>
  <tr><td><strong>Physical Penetration (เจาะเกราะกายภาพ)</strong></td><td>โจมตีกายภาพโดยไม่สนค่าป้องกันของศัตรูบางส่วน</td></tr>
  <tr><td><strong>Magic Penetration (เจาะเกราะเวท)</strong></td><td>โจมตีเวทโดยไม่สนค่าป้องกันเวทของศัตรูบางส่วน</td></tr>
  <tr><td><strong>Magic Evasion (หลบหลีกเวท)</strong></td><td>โอกาสหลบหลีกการโจมตีด้วยเวทมนตร์</td></tr>
  <tr><td><strong>Absolute Evasion (หลบหลีกสัมบูรณ์)</strong></td><td>โอกาสหลบการโจมตีกายภาพแบบสมบูรณ์</td></tr>
  <tr><td><strong>Absolute Hit (แม่นยำสัมบูรณ์)</strong></td><td>โอกาสโจมตีโดนแน่นอนไม่พลาดเป้า</td></tr>
  <tr><td><strong>Physical Resistance (ต้านกายภาพ)</strong></td><td>ลดความเสียหายจากการโจมตีกายภาพเป็น %</td></tr>
  <tr><td><strong>Magic Resistance (ต้านเวท)</strong></td><td>ลดความเสียหายจากการโจมตีเวทมนตร์เป็น %</td></tr>
  <tr><td><strong>Range Cut (ลดดาเมจระยะไกล)</strong></td><td>ลดความเสียหายจากการโจมตีระยะไกล</td></tr>
  <tr><td><strong>Rate Cut (ลดดาเมจ %)</strong></td><td>ลดความเสียหายจากการโจมตีแบบคิดเป็น % ของ HP</td></tr>
  <tr><td><strong>Ailment Resistance (ต้านสถานะผิดปกติ)</strong></td><td>ลดโอกาสติดสถานะผิดปกติต่างๆ (พิษ อัมพาต สตั๊น ฯลฯ)</td></tr>
  <tr><td><strong>Cast Defense (ป้องกันขณะร่าย)</strong></td><td>เพิ่มพลังป้องกันระหว่างกำลังร่ายสกิล</td></tr>
  <tr><td><strong>Spell Burst (สเปลเบิร์สต์)</strong></td><td>โอกาสที่การโจมตีด้วยเวทมนตร์จะติดคริติคอลเวท</td></tr>
</table>

<h3>ตารางการเพิ่ม ATK ตามประเภทอาวุธ (ต่อ 1 แต้มสเตตัส)</h3>
<table>
  <tr><th>ประเภทอาวุธ</th><th>STR</th><th>INT</th><th>VIT</th><th>AGI</th><th>DEX</th><th>CRT</th></tr>
  <tr><td>ดาบ (Sword)</td><td>+3</td><td>-</td><td>-</td><td>-</td><td>+1</td><td>-</td></tr>
  <tr><td>ธนู (Bow)</td><td>+2</td><td>-</td><td>-</td><td>-</td><td>+2</td><td>-</td></tr>
  <tr><td>ไม้เท้า (Cane)</td><td>+3</td><td>-</td><td>-</td><td>-</td><td>+1</td><td>-</td></tr>
  <tr><td>กรงเล็บ (Claw)</td><td>+2</td><td>-</td><td>-</td><td>+2</td><td>-</td><td>-</td></tr>
  <tr><td>อาวุธขว้าง (Throwing)</td><td>+2</td><td>-</td><td>-</td><td>+2</td><td>+1</td><td>-</td></tr>
  <tr><td>ดาบเวท (Magic Sword)</td><td>+2.5</td><td>+1</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>ธนูเวท (Magic Bow)</td><td>+2</td><td>+1.5</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>ไม้เท้าเวท (Magic Cane)</td><td>+1</td><td>+2.5</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>ดาบพิเศษ (Special Sword)</td><td>+1</td><td>-</td><td>+2</td><td>-</td><td>+1.5</td><td>-1</td></tr>
  <tr><td>ธนูพิเศษ (Special Bow)</td><td>-1</td><td>-1</td><td>-</td><td>+2.5</td><td>+1</td><td>-</td></tr>
  <tr><td>กรงเล็บพิเศษ (Special Claw)</td><td>-</td><td>-</td><td>-</td><td>+4</td><td>-</td><td>+1</td></tr>
  <tr><td>อาวุธขว้างพิเศษ (Special Throwing)</td><td>+1</td><td>+1</td><td>-</td><td>-</td><td>+1</td><td>-</td></tr>
</table>
"""
    },

    "apostolia": {
        "key": "apostolia",
        "label": "อโพสโทเลีย (Apostolia)",
        "html": """
<p><strong>อโพสโทเลีย (Apostolia)</strong> คือระบบที่ช่วยให้ตัวละครสามารถอัปค่าสเตตัสเกินขีดจำกัด 256 ได้ และยังสามารถติดตั้ง <strong>อัลคริสต้า (▲ Al Crysta)</strong> ได้สูงสุดถึง 5 ชิ้น</p>
<p>สามารถปลดล็อกระบบ Apostolia ได้หลังจากผ่านเนื้อเรื่องหลัก <strong>Episode 2</strong> และทำเควสต์เนื้อเรื่องหลักในช่วงต้นของ <strong>Episode 3</strong></p>

<h3>อัลคริสต้า (▲ Al Crysta)</h3>
<p>บอสตั้งแต่ Episode 3 เป็นต้นไปจะมีโอกาสดรอปคริสต้าชนิดใหม่เรียกว่า <strong>Artificial Light Crysta (Al Crysta)</strong> ซึ่งมี 3 สี ได้แก่ <strong>สีแดง (Red)</strong>, <strong>สีน้ำเงิน (Blue)</strong> และ <strong>สีเขียว (Green)</strong></p>
<p>นอกจากสเตตัสพื้นฐานของตัวอัลคริสต้าแล้ว เมื่อติดตั้งลงในหน้าต่าง Apostolia จะเกิดการเชื่อม <strong>เส้นสี (Lines)</strong> ระหว่างเม็ดคริสต้าเพื่อมอบโบนัสพิเศษเพิ่มตามคู่สี</p>

<h3>การจับคู่เส้นสี (Lines)</h3>
<table>
  <tr><th>สีเส้น</th><th>การเชื่อมต่อ</th><th>โบนัสที่ได้รับ</th></tr>
  <tr><td><strong>สีแดง (Red)</strong></td><td>แดง + แดง</td><td>ฟื้นฟู HP อัตโนมัติ / MaxHP / DEF</td></tr>
  <tr><td><strong>สีเขียว (Green)</strong></td><td>เขียว + เขียว</td><td>หลบหลีกสัมบูรณ์ / หลบหลีกกายภาพ / หลบหลีกเวท</td></tr>
  <tr><td><strong>สีน้ำเงิน (Blue)</strong></td><td>น้ำเงิน + น้ำเงิน</td><td>ฟื้นฟู MP อัตโนมัติ / MaxMP / MDEF</td></tr>
  <tr><td><strong>สีฟ้า (Aqua)</strong></td><td>น้ำเงิน + เขียว</td><td>MATK / เจาะเกราะเวท / พลังเวท</td></tr>
  <tr><td><strong>สีเหลือง (Yellow)</strong></td><td>เขียว + แดง</td><td>ATK / พลังกายภาพ / เจาะเกราะกายภาพ</td></tr>
  <tr><td><strong>สีม่วง (Purple)</strong></td><td>แดง + น้ำเงิน</td><td>ติดออโต้สกิล / ASPD / อัตราคริติคอล</td></tr>
</table>
<p>ยิ่งเชื่อมเส้นสีเดียวกันได้หลายเส้น เอฟเฟกต์โบนัสก็จะยิ่งแรงขึ้น</p>

<h3>การปลดล็อกขีดจำกัดสเตตัส (Stat Release)</h3>
<p>ช่วยให้สามารถอัปสเตตัสเกิน 256 ได้ โดยเข้าไปที่ <strong>เมนู &gt; ตัวละคร &gt; สถานะ (Stats) &gt; Apostolia</strong> กดลูกศรขวาแล้วเลือกสเตตัสที่ต้องการฝึก (STR, VIT, INT, DEX, AGI, CRT) แล้วกดเพิ่มระดับ (Raise)</p>
<p>เมื่อเปิดโหมดฝึกสเตตัส หลอด EXP จะเปลี่ยนเป็นสีเขียว และเลเวลสเตตัสจะแสดงแทนที่เลเวลตัวละครด้านซ้ายบน</p>
<ul>
  <li>สามารถอัปเลเวลแต่ละสเตตัสได้สูงสุดเท่ากับ <strong>เลเวลตัวละคร ÷ 2</strong></li>
  <li>ทุกๆ การอัปเลเวลสเตตัสครบ <strong>3 เลเวล</strong> จะได้รับแต้มสเตตัสเพิ่ม <strong>1 แต้ม</strong></li>
  <li>เพดานสเตตัสใหม่ของแต่ละค่าจะเท่ากับ <strong>256 + เลเวลสเตตัสนั้นๆ</strong></li>
</ul>

<h3>สเตตัสพิเศษ (Special Stats)</h3>
<table>
  <tr><th>สเตตัสพิเศษ</th><th>คำอธิบาย</th></tr>
  <tr><td><strong>EXP</strong></td><td>เพิ่มอัตราการได้รับค่าประสบการณ์ (EXP)</td></tr>
  <tr><td><strong>IgR</strong></td><td>เพิ่มความเร็วในการชาร์จเกจ Ignition</td></tr>
  <tr><td><strong>IgT</strong></td><td>เพิ่มระยะเวลาการทำงานของ Ignition</td></tr>
  <tr><td><strong>RD</strong></td><td>เพิ่มความแรงโบนัสของเส้นสีแดง เหลือง และม่วง</td></tr>
  <tr><td><strong>GR</strong></td><td>เพิ่มความแรงโบนัสของเส้นสีเขียว ฟ้า และเหลือง</td></tr>
  <tr><td><strong>BL</strong></td><td>เพิ่มความแรงโบนัสของเส้นสีน้ำเงิน ม่วง และฟ้า</td></tr>
</table>

<h3>ระบบอิกนิชัน (Ignition)</h3>
<p>การกดใช้ <strong>Ignition</strong> จะช่วยบัฟค่าสถานะและอัตราดรอปชั่วคราว ยิ่งใช้งานบ่อยครั้ง ระยะเวลาสูงสุดของ Ignition จะยิ่งเพิ่มขึ้น และเมื่อสะสมจำนวนครั้งถึงกำหนดจะปลดล็อก <strong>หน้าต่าง Al Crysta เพิ่มเติม</strong> ทำให้สลับเซตสายโจมตี/ป้องกัน/ธาตุได้อย่างอิสระ</p>
<table>
  <tr><th>จำนวนครั้งที่ใช้ Ignition</th><th>รางวัลปลดล็อก</th></tr>
  <tr><td><strong>500 ครั้ง</strong></td><td>ปลดล็อกหน้า Al Crysta หน้าที่ 2</td></tr>
  <tr><td><strong>1,000 ครั้ง</strong></td><td>ปลดล็อกหน้า Al Crysta หน้าที่ 3</td></tr>
  <tr><td><strong>2,000 ครั้ง</strong></td><td>ปลดล็อกหน้า Al Crysta หน้าที่ 4 และเพิ่มเวลา Ignition สูงสุดเป็น 600 วินาที</td></tr>
</table>
"""
    },

    "refinement": {
        "key": "refinement",
        "label": "การตีบวก (Refinement)",
        "html": """
<h3>ระบบการตีบวกอุปกรณ์ (Refinement)</h3>
<p>การตีบวกช่วยเพิ่มประสิทธิภาพของอุปกรณ์โดยตรง สำหรับ <strong>อาวุธ</strong> จะเพิ่มค่า ATK ของอาวุธ ส่วน <strong>ชุดเกราะและอุปกรณ์เสริม</strong> จะเพิ่มค่า DEF</p>
<p>การตีบวกชุดเกราะและอุปกรณ์เสริมสำคัญมากต่อความอึด เพราะค่า DEF และค่าระดับตีบวกแต่ละขั้นบนเกราะ/อุปกรณ์เสริมจะช่วยลดความเสียหายกายภาพลง <strong>1% ต่อขั้น</strong></p>
<p>สามารถตีบวกได้ที่ <strong>ช่างตีเหล็ก (Blacksmith)</strong> ตามเมืองต่างๆ (แร่ที่รับตีบวกจะขึ้นอยู่กับแต่ละเมือง) ยิ่งระดับบวกสูง โอกาสสำเร็จก็จะยิ่งลดลง</p>

<h3>แร่ที่ใช้ในการตีบวก (Refining Ores)</h3>
<table>
  <tr><th>แร่ตีบวก</th><th>คุณสมบัติ</th></tr>
  <tr><td><a href="db_items.html?item=เฮมาไทต์">เฮมาไทต์ (Hematite)</a></td><td>ตีบวกได้สูงสุดถึง +5</td></tr>
  <tr><td><a href="db_items.html?item=เหล็กดามัสกัส">เหล็กดามัสกัส (Damascus Steel)</a></td><td>ตีบวกได้สูงสุดถึง +7</td></tr>
  <tr><td><a href="db_items.html?item=มิธริล">มิธริล (Mythril)</a></td><td>ตีบวกได้สูงสุดถึง +8</td></tr>
  <tr><td><a href="db_items.html?item=โอริคัลคุม">โอริคัลคุม (Orichalcum)</a></td><td>ตีบวกได้สูงสุดถึง +9</td></tr>
  <tr><td>เหล็ก (Iron)</td><td>ตีบวกสำเร็จ 100% ถึง +4</td></tr>
  <tr><td>เหล็กดัด (Wrought Iron)</td><td>ตีบวกสำเร็จ 100% ถึง +5</td></tr>
  <tr><td>ไฮมิธริล (High Mythril)</td><td>ตีบวกสำเร็จ 100% ถึง +6</td></tr>
  <tr><td>ฮิฮิอิโระคาเนะ (Hihiirokane)</td><td>ตีบวกสำเร็จ 100% ถึง +7</td></tr>
</table>

<h3>ตารางอัตราความสำเร็จ (ปกติ)</h3>
<table>
  <tr><th>แร่</th><th>+1</th><th>+2</th><th>+3</th><th>+4</th><th>+5</th><th>+6</th><th>+7</th><th>+8</th><th>+9</th></tr>
  <tr><td>Hematite</td><td>100%</td><td>90%</td><td>80%</td><td>60%</td><td>30%</td><td>10%</td><td>5%</td><td>1%</td><td>1%</td></tr>
  <tr><td>Damascus Steel</td><td>100%</td><td>100%</td><td>90%</td><td>80%</td><td>60%</td><td>30%</td><td>10%</td><td>5%</td><td>1%</td></tr>
  <tr><td>Mythril</td><td>100%</td><td>100%</td><td>100%</td><td>90%</td><td>80%</td><td>60%</td><td>30%</td><td>10%</td><td>5%</td></tr>
  <tr><td>Orichalcum</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>90%</td><td>80%</td><td>60%</td><td>30%</td><td>10%</td></tr>
  <tr><td>Iron</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>Wrought Iron</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>-</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>High Mythril</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>-</td><td>-</td><td>-</td></tr>
  <tr><td>Hihiirokane</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>-</td><td>-</td></tr>
</table>

<h3>ตารางอัตราความสำเร็จ (ช่วงอีเวนต์ตีบวก ที่ฐานทัพไบลูน)</h3>
<p>บางช่วงจะมีอีเวนต์เพิ่มโอกาสตีบวกสำเร็จ ช่วยประหยัด Spina และแร่ได้มาก</p>
<table>
  <tr><th>แร่</th><th>+1</th><th>+2</th><th>+3</th><th>+4</th><th>+5</th><th>+6</th><th>+7</th><th>+8</th><th>+9</th></tr>
  <tr><td>Hematite</td><td>100%</td><td>100%</td><td>100%</td><td>90%</td><td>45%</td><td>15%</td><td>7%</td><td>1%</td><td>1%</td></tr>
  <tr><td>Damascus Steel</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>90%</td><td>45%</td><td>15%</td><td>7%</td><td>1%</td></tr>
  <tr><td>Mythril</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>90%</td><td>45%</td><td>15%</td><td>7%</td></tr>
  <tr><td>Orichalcum</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>100%</td><td>90%</td><td>45%</td><td>15%</td></tr>
</table>

<h3>ผลลัพธ์เมื่อตีบวกพลาด (Refinement Penalties)</h3>
<table>
  <tr><th>จำนวนรูคริสต้า (Slot)</th><th>การเปลี่ยนแปลงระดับบวก</th></tr>
  <tr><td>ไม่มีรู (0 Slot)</td><td>-1 / +0 / +1</td></tr>
  <tr><td>1 รู (1 Slot)</td><td>-2 / -1 / +0 / +1</td></tr>
  <tr><td>2 รู (2 Slot)</td><td>-3 / -2 / -1 / +0 / +1</td></tr>
</table>

<h3>ตัวคูณ ATK อาวุธตามระดับตีบวก</h3>
<table>
  <tr><th>ระดับตีบวก</th><th>ตัวคูณ ATK อาวุธ</th></tr>
  <tr><td>+1</td><td>ATK อาวุธ × 1.01</td></tr>
  <tr><td>+2</td><td>ATK อาวุธ × 1.04</td></tr>
  <tr><td>+3</td><td>ATK อาวุธ × 1.09</td></tr>
  <tr><td>+4</td><td>ATK อาวุธ × 1.16</td></tr>
  <tr><td>+5</td><td>ATK อาวุธ × 1.25</td></tr>
  <tr><td>+6</td><td>ATK อาวุธ × 1.36</td></tr>
  <tr><td>+7</td><td>ATK อาวุธ × 1.50</td></tr>
  <tr><td>+8</td><td>ATK อาวุธ × 1.66</td></tr>
  <tr><td>+9</td><td>ATK อาวุธ × 1.83</td></tr>
</table>

<h3>การตีบวกขั้นสุดยอด (Super Refinement / ซูเปอร์รีไฟน์)</h3>
<p><strong>Super Refinement</strong> ช่วยเพิ่มค่าพลังพื้นฐาน (Base ATK ของอาวุธ และ Base DEF ของชุดเกราะ/อุปกรณ์เสริม) โดย<strong>การันตีว่าอุปกรณ์จะไม่แตกหาย</strong> ต่างจากการเพิ่มค่าด้วยสกิลผลิตแบบเดิม</p>
<ul>
  <li>ต้องตีบวกอุปกรณ์ให้ถึง <strong>+9</strong> ก่อน</li>
  <li>นำไปคุยกับ <strong>ช่างตีเหล็กไดรอน (Dyron)</strong> ที่ <strong>ฐานทัพไบลูน</strong></li>
  <li>ใช้หิน Super Refinement ในการสุ่มเพิ่มค่าคุณภาพ (อาวุธเพิ่มได้สูงสุด Quality +30, ชุดเกราะและอุปกรณ์เสริมเพิ่มได้สูงสุด Quality +20)</li>
</ul>
"""
    },

    "pets": {
        "key": "pets",
        "label": "สัตว์เลี้ยง (Pets Guide)",
        "html": """
<h3>1) สัตว์เลี้ยง (Pet) คืออะไร?</h3>
<p>สัตว์เลี้ยงใช้เป็นผู้ช่วยเวลาลงดันเจี้ยนหรือโซโล่บอส สามารถช่วยฮีล ช่วยโจมตี ใช้สกิลบัฟ ช่วยชุบชีวิต หรือเก็บของได้ โดยสัตว์เลี้ยงจะอาศัยอยู่บนเกาะส่วนตัว (Island) เราสามารถให้อาหารเพื่อเพิ่มเลเวลและเรียนสกิลได้</p>

<h3>2) วิธีหาสัตว์เลี้ยง (3 ช่องทางหลัก)</h3>
<ul>
  <li><strong>A) สัตว์เลี้ยงจรจัดบนเกาะ (Stray Pet)</strong> — วิธีที่ประหยัดที่สุด เพียงวางเฟอร์นิเจอร์แต่งเกาะ (Island Objects) บนเกาะ สัตว์เลี้ยงจรจัดจะสุ่มมาเยี่ยมเกาะ จากนั้นให้อาหารทุกๆ 8 ชั่วโมงเพื่อเพิ่มค่าความสนิท (Affinity) จนครบ <strong>500</strong> ก็จะกลายเป็นสัตว์เลี้ยงของเรา (อาหาร <em>Fancy Pet Food</em> ใช้เพิ่มความสนิทได้กับสัตว์เลี้ยงแทบทุกชนิด) หากไม่ถูกใจสามารถไล่ออกเพื่อให้ตัวใหม่สุ่มมาแทนได้</li>
  <li><strong>B) ไข่สัตว์เลี้ยงจากอีเวนต์ (Event Eggs)</strong> — ได้รับจากกิจกรรมประจำปี ไม่ต้องเก็บค่าสนิท 500 ฟักแล้วเป็นของเราทันที (ไม่สามารถแลกเปลี่ยนได้ และอาจเรียนสกิลระดับบอส/เทพบางสกิลไม่ได้)</li>
  <li><strong>C) ไข่สัตว์เลี้ยงจากร้านค้า (Item Shop)</strong> — ซื้อจากช็อปในเกม ฟักใช้งานได้ทันที และสัตว์เลี้ยงระดับบอส/เทพจากช็อปมีโอกาสเรียนสกิลพิเศษระดับสูงได้ครบทั้งหมด</li>
</ul>

<h3>3) วิธีให้สัตว์เลี้ยงเรียนสกิล</h3>
<ul>
  <li>เมื่อสัตว์เลี้ยงมี <strong>เลเวล 50 ขึ้นไป</strong> และมีค่าความสนิท <strong>1,000</strong> จะสุ่มเรียนรู้สกิลอัตโนมัติ (หากเลเวล <strong>75 ขึ้นไป</strong> สามารถเรียนสกิลได้โดยไม่ต้องรอความสนิทครบ 1,000)</li>
  <li>สามารถให้สัตว์เลี้ยงกินไข่สัตว์เลี้ยงเพื่อลุ้นเรียนสกิล หรือใช้ <strong>500 Island Points</strong> เพื่อสุ่มรีเซ็ตสกิลใหม่ได้</li>
  <li>สกิลที่ได้จะเป็นแบบสุ่มทั้งหมด ไม่ขึ้นอยู่กับสเตตัสหรือชนิดอาหารที่ให้กิน</li>
</ul>

<h3>รายการสกิลสัตว์เลี้ยงทั้งหมด (Pet Skills List)</h3>
<table>
  <tr><th>สกิลพาสซีฟ (เพิ่มสเตตัส)</th><th>สกิลใช้งาน (Active Skills)</th></tr>
  <tr>
    <td>
      STR +1 / STR +2<br>
      INT +1 / INT +2<br>
      VIT +1 / VIT +2<br>
      AGI +1 / AGI +2<br>
      DEX +1 / DEX +2<br>
      CRT +1 / CRT +2<br>
      ความแม่นยำ (Accuracy) +4 / +6<br>
      หลบหลีก (Evasion) +4 / +6<br>
      รับฮีลแรงขึ้น (Heal Reward) +50 / +75<br>
      พลังกายภาพ (Melee) +10 / +20<br>
      ผลฟื้นฟูจากไอเทม +2% / +4%<br>
      อัตราคริติคอล +1 / +2<br>
      MaxHP +75 / +100<br>
      ฟื้นฟู HP อัตโนมัติ +15 / +25<br>
      MaxMP +25 / +50<br>
      ฟื้นฟู MP อัตโนมัติ +5 / +15
    </td>
    <td>
      <strong>Vampire Blow Lv1</strong> — โจมตีพร้อมดูดเลือด<br>
      <strong>Aid Lv1</strong> — ฮีลตัวเองตามเลเวลและ MP (ใช้ MP 10%)<br>
      <strong>Assault Lv1</strong> — โจมตีเจาะเกราะศัตรูเล็กน้อย (MP 84)<br>
      <strong>Provoke Lv1</strong> — ยั่วยุเพิ่มค่าเกลียดชัง<br>
      <strong>Hard Hit Lv1</strong> — โจมตีกายภาพรุนแรง<br>
      <strong>Evasion Lv1</strong> — บัฟ AGI +16 นาน 3 นาที (MP 48)<br>
      <strong>Protection Lv1</strong> — บัฟเพิ่ม DEF<br>
      <strong>Mana Wave Lv1</strong> — โจมตีด้วยคลื่นเวท<br>
      <strong>Homing Lv1</strong> — โจมตีแม่นยำสูง<br>
      <strong>Dual Blow Lv1</strong> — โจมตีต่อเนื่อง 2 ครั้ง<br>
      <strong>Self Healing Lv1</strong> — ฟื้นฟู HP ตนเอง<br>
      <strong>Spell Boost Lv1</strong> — บัฟเพิ่มพลังเวท (MATK) ชั่วคราว<br>
      <strong>Double Attack Lv1</strong> — เพิ่มโอกาสโจมตีเบิ้ล<br>
      <strong>Sonic Boom Lv1</strong> — โจมตีคลื่นเสียงระยะไกล<br>
      <strong>All Around Lv1</strong> — บัฟต้านทานทุกธาตุ<br>
      <strong>Escape Lv1</strong> — เพิ่มความเร็วเคลื่อนที่/หลบหนี<br>
      <strong>Hide Attack Lv1</strong> — โจมตีจากเงามืด (คริติคอลสูง)<br>
      <strong>Dark Blast Lv1</strong> — โจมตีเวทธาตุมืด<br>
      <strong>Large Shield Lv1</strong> — บัฟลดความเสียหายกายภาพ<br>
      <strong>Quick Turn Lv1</strong> — บัฟหลบหลีกและลดดีเลย์<br>
      <strong>High Cycle Lv1</strong> — เร่งความเร็วโจมตีและลดเวลาร่ายสูงสุด
    </td>
  </tr>
</table>
"""
    },
}


# =============================================================================
# 4. TRANSLATE ALL DATABASE FILES
# =============================================================================
def translate_items_and_meta():
    print("=== [1/6] Translating Items & Meta (24 categories + 78 Attr Filters) ===", flush=True)
    # 1a. Update items_meta.json with Thai attr filters
    meta_path = DB_DIR / "items_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["attrFilters"] = [{"key": k, "label": lbl} for k, lbl in ATTR_FILTERS_TH]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 1b. Translate non-Thai ds, tds, and notes in all items/*.json
    translated_ds = 0
    translated_tds = 0
    translated_notes = 0
    for p in sorted((DB_DIR / "items").glob("*.json")):
        arr = json.loads(p.read_text(encoding="utf-8"))
        for it in arr:
            if it.get("ds") and not has_thai(it["ds"]):
                new_ds = translate_stat_text(it["ds"])
                if new_ds != it["ds"]:
                    it["ds"] = new_ds
                    translated_ds += 1
            if it.get("tds"):
                new_tds = translate_stat_text(it["tds"])
                if new_tds != it["tds"]:
                    it["tds"] = new_tds
                    translated_tds += 1
            if it.get("notes"):
                new_n = translate_stat_text(it["notes"])
                if new_n != it["notes"]:
                    it["notes"] = new_n
                    translated_notes += 1
        p.write_text(json.dumps(arr, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Translated items: ds={translated_ds}, tds={translated_tds}, notes={translated_notes}", flush=True)


def translate_blacksmiths():
    print("=== [2/6] Translating Blacksmiths ===", flush=True)
    bp = DB_DIR / "blacksmiths.json"
    bs = json.loads(bp.read_text(encoding="utf-8"))
    cnt = 0
    for b in bs.values():
        for cat in b.get("categories", []):
            raw_cat = cat["cat"]
            if raw_cat in CAT_TH:
                cat["cat"] = f"{CAT_TH[raw_cat]} ({raw_cat})"
            for it in cat.get("items", []):
                if it.get("stats"):
                    it["stats"] = translate_stat_text(it["stats"])
                    cnt += 1
    bp.write_text(json.dumps(bs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Translated {cnt} blacksmith entries", flush=True)


def translate_zones_and_search():
    print("=== [3/6] Translating Zones (Monster Attr/Weak/Aggr/Area) & Search Index ===", flush=True)
    mobs_done = 0
    for p in sorted((DB_DIR / "zones").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for z in d.get("zones", {}).values():
            for m in z.get("monsters", []):
                if m.get("attr"):
                    m["attr"] = translate_element(m["attr"])
                if m.get("weak"):
                    m["weak"] = translate_element(m["weak"])
                if m.get("aggr"):
                    m["aggr"] = translate_aggr(m["aggr"])
                if m.get("area"):
                    m["area"] = translate_area(m["area"])
                mobs_done += 1
            for q in z.get("quests", []):
                translate_quest_obj(q)
        p.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # Also update search_index.json monster attrs & ability labels
    sp = DB_DIR / "search_index.json"
    si = json.loads(sp.read_text(encoding="utf-8"))
    for m in si.get("monsters", []):
        if m.get("a"):
            m["a"] = translate_element(m["a"])
    for a in si.get("abilities", []):
        if a["s"] in ABILITY_TH:
            a["n"] = f"☆{ABILITY_TH[a['s']]}"
    sp.write_text(json.dumps(si, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Translated {mobs_done} monster records & updated search index", flush=True)


def translate_quest_obj(q: dict):
    if q.get("req"):
        req = q["req"]
        for en, th in CLASS_TH.items():
            req = re.sub(rf"\b{re.escape(en)}\b", th.split(" (")[0], req)
        req = req.replace("Lv", "เลเวล ")
        q["req"] = req
    if q.get("desc") and not has_thai(q["desc"]):
        desc = q["desc"]
        # Common quest phrasing
        repls = [
            (r"\bDefeat the monsters infesting\b", "กำจัดมอนสเตอร์ที่อาละวาดอยู่ใน"),
            (r"\bDefeat the\b", "กำจัด"),
            (r"\bDefeat\b", "กำจัด"),
            (r"\bCollect\b", "รวบรวม"),
            (r"\bGather\b", "รวบรวม"),
            (r"\bDeliver\b", "นำส่ง"),
            (r"\bSpeak to\b", "คุยกับ"),
            (r"\bTalk to\b", "คุยกับ"),
            (r"\bInvestigate\b", "สำรวจ"),
            (r"\bFind\b", "ตามหา"),
            (r"\bBring\b", "นำมามอบ"),
            (r"\bmonsters\b", "มอนสเตอร์"),
            (r"\bmonster\b", "มอนสเตอร์"),
        ]
        for pat, rep in repls:
            desc = re.sub(pat, rep, desc)
        q["desc"] = desc


def translate_quests():
    print("=== [4/6] Translating Quests ===", flush=True)
    qp = DB_DIR / "quests.json"
    eps = json.loads(qp.read_text(encoding="utf-8"))
    cnt = 0
    for ep in eps:
        if ep["label"] == "Events":
            ep["label"] = "อีเวนต์ (Events)"
        for q in ep.get("quests", []):
            translate_quest_obj(q)
            cnt += 1
    qp.write_text(json.dumps(eps, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Updated {cnt} quests", flush=True)


def translate_html_text_nodes(html_str: str, extra_rules=None) -> str:
    if not html_str:
        return html_str
    soup = BeautifulSoup(html_str, "html.parser")
    rules = list(extra_rules or []) + COMPILED_STAT_RULES
    for node in soup.find_all(string=True):
        if not isinstance(node, NavigableString):
            continue
        if node.parent and node.parent.name in ("script", "style"):
            continue
        txt = str(node)
        if not txt.strip():
            continue
        new_txt = txt
        for pat, rep in rules:
            new_txt = pat.sub(rep, new_txt)
        if new_txt != txt:
            node.replace_with(new_txt)
    return str(soup)


def translate_events():
    print("=== [5/6] Translating Events (9 events) ===", flush=True)
    ep = DB_DIR / "events.json"
    evs = json.loads(ep.read_text(encoding="utf-8"))
    event_rules = [
        (re.compile(r"\bMonsters\b"), "มอนสเตอร์"),
        (re.compile(r"\bDrop:\b"), "ดรอป:"),
        (re.compile(r"\bAttr:\b"), "ธาตุ:"),
        (re.compile(r"\bWeak:\b"), "แพ้ธาตุ:"),
        (re.compile(r"\bAggr:\b"), "นิสัย:"),
        (re.compile(r"\bSee Map\b"), "ดูแผนที่"),
        (re.compile(r"\bQuests\b"), "เควสต์"),
        (re.compile(r"\bQuest:\b"), "ภารกิจ:"),
        (re.compile(r"\bReward\b"), "รางวัล"),
        (re.compile(r"\bObjective:\b"), "เป้าหมาย:"),
        (re.compile(r"\bLocation:\b"), "สถานที่:"),
        (re.compile(r"\bExperience:\b"), "ค่าประสบการณ์ (EXP):"),
        (re.compile(r"\bTalk to\b"), "คุยกับ"),
        (re.compile(r"\bDefeat\b"), "กำจัด"),
        (re.compile(r"\bWater\b"), "น้ำ"),
        (re.compile(r"\bFire\b"), "ไฟ"),
        (re.compile(r"\bWind\b"), "ลม"),
        (re.compile(r"\bEarth\b"), "ดิน"),
        (re.compile(r"\bLight\b"), "แสง"),
        (re.compile(r"\bDark\b"), "มืด"),
        (re.compile(r"\bPassive\b"), "ไม่โจมตีก่อน"),
        (re.compile(r"\bUnder Active\b"), "โจมตีก่อน (ถ้าเลเวลต่ำกว่า)"),
        (re.compile(r"\bOver Active\b"), "โจมตีก่อนตลอด"),
        (re.compile(r"\bActive\b"), "โจมตีก่อน"),
    ]
    for ev in evs:
        for m in ev.get("monsters", []):
            if m.get("attr"):
                m["attr"] = translate_element(m["attr"])
            if m.get("weak"):
                m["weak"] = translate_element(m["weak"])
            if m.get("aggr"):
                m["aggr"] = translate_aggr(m["aggr"])
            if m.get("area"):
                m["area"] = translate_area(m["area"])
        for q in ev.get("quests", []):
            translate_quest_obj(q)
        if ev.get("html"):
            ev["html"] = translate_html_text_nodes(ev["html"], event_rules)
    ep.write_text(json.dumps(evs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Translated all {len(evs)} events", flush=True)


def translate_guides():
    print("=== [6/6] Translating All 11 Guides ===", flush=True)
    gdir = DB_DIR / "guides"

    # 6a. Hand-crafted Thai guides (stats, apostolia, refinement, pets)
    for k, payload in THAI_GUIDES.items():
        (gdir / f"{k}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        print(f"  guide/{k:18s}: Hand-crafted Thai guide written", flush=True)

    # 6b. abilities.json — translate intro + all tables & headers
    ab_path = gdir / "abilities.json"
    ab = json.loads(ab_path.read_text(encoding="utf-8"))
    ab_rules = [
        (re.compile(r"Ability allow you to add extra stats onto equipment\..*?combining them\.", re.S),
         "อบิลิตี้ (☆Ability) ช่วยเพิ่มสเตตัสพิเศษให้กับอุปกรณ์ สามารถหาได้จากบอสดรอปหรือโบนัสล็อกอิน อุปกรณ์ที่มีสัญลักษณ์ ☆ สามารถย้ายอบิลิตี้ไปใส่อุปกรณ์อื่น หรือรวมเพื่ออัปเลเวลได้"),
        (re.compile(r"Ability can be leveled up by combining them.*?increase success rate\.", re.S),
         "การอัปเลเวลอบิลิตี้ทำได้โดยนำอุปกรณ์ประเภทเดียวกันที่มีอบิลิตี้เลเวลเท่ากันมารวมกัน หากสำเร็จอุปกรณ์ชิ้นที่ 2 จะหายไป หากพลาดอุปกรณ์ชิ้นแรกอาจลดค่า ATK/DEF หรือเลเวลอบิลิตี้ลดลง (ใช้แร่เพื่อเพิ่มโอกาสสำเร็จได้)"),
        (re.compile(r"When combining, transfer the second ability to a cheap equipment because it will get destroyed\."),
         "คำแนะนำ: ก่อนรวมอบิลิตี้ ควรย้ายอบิลิตี้ชิ้นที่ 2 ไปไว้บนอุปกรณ์ราคาถูกก่อน เพราะอุปกรณ์ชิ้นที่ 2 จะถูกทำลายเมื่อรวม"),
        (re.compile(r"There are 8 types of equipment"), "อุปกรณ์แบ่งออกเป็น 8 ประเภท (ย้าย/รวมได้เฉพาะประเภทเดียวกัน)"),
        (re.compile(r"Leveling Ability"), "การอัปเลเวลอบิลิตี้"),
        (re.compile(r"High Quality lowers Transfer Rate but increases Combine Rate"),
         "อุปกรณ์คุณภาพสูงจะลดโอกาสย้ายอบิลิตี้ แต่ช่วยเพิ่มโอกาสสำเร็จในการรวมอบิลิตี้"),
        (re.compile(r"\bOres\b"), "แร่"),
        (re.compile(r"\bTransfer\b"), "การย้าย (Transfer)"),
        (re.compile(r"\bCombine\b"), "การรวม (Combine)"),
        (re.compile(r"Success Rate"), "โอกาสสำเร็จ"),
        (re.compile(r"Prevents Ability Degrading"), "ป้องกันเลเวลอบิลิตี้ลดลงเมื่อพลาด"),
        (re.compile(r"\bAdditional Equipment\b"), "อุปกรณ์เสริม"),
        (re.compile(r"\bSpecial Equipment\b"), "อุปกรณ์พิเศษ"),
    ]
    ab["html"] = translate_html_text_nodes(ab["html"], ab_rules)
    ab_path.write_text(json.dumps(ab, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("  guide/abilities         : Translated to Thai", flush=True)

    # 6c. abilities2.json — Thai labels + Thai tables
    ab2_path = gdir / "abilities2.json"
    ab2 = json.loads(ab2_path.read_text(encoding="utf-8"))
    for item in ab2.get("list", []):
        if item["key"] in ABILITY_TH:
            item["label"] = ABILITY_TH[item["key"]]
    ab2_rules = [
        (re.compile(r"\bDescription\b"), "คำอธิบาย (ผลลัพธ์แต่ละเลเวล)"),
        (re.compile(r"\bSwords\b"), "ดาบ (Swords)"),
        (re.compile(r"\bBows\b"), "ธนู (Bows)"),
        (re.compile(r"\bCanes\b"), "ไม้เท้า (Canes)"),
        (re.compile(r"\bClaws\b"), "กรงเล็บ (Claws)"),
        (re.compile(r"\bThrowing\b"), "อาวุธขว้าง (Throwing)"),
        (re.compile(r"\bArmor\b"), "ชุดเกราะ (Armor)"),
        (re.compile(r"\bAdditional\b"), "อุปกรณ์เสริม (Additional)"),
        (re.compile(r"\bSpecial\b"), "อุปกรณ์พิเศษ (Special)"),
    ]
    for k in list(ab2.get("details", {}).keys()):
        ab2["details"][k] = translate_html_text_nodes(ab2["details"][k], ab2_rules)
    ab2_path.write_text(json.dumps(ab2, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("  guide/abilities2        : Translated 46 abilities to Thai", flush=True)

    # 6d. raids.json
    raids_path = gdir / "raids.json"
    raids = json.loads(raids_path.read_text(encoding="utf-8"))
    raid_rules = [
        (re.compile(r"\bTalk to Entrata in Capital City Sofya\b"), "คุยกับ Entrata ที่ มหานครโซเฟีย"),
        (re.compile(r"\bTalk to Entrata in Capital City Saterica\b"), "คุยกับ Entrata ที่ มหานครซาเทริกา"),
        (re.compile(r"\bTalk to Entrata in Capital City Elban\b"), "คุยกับ Entrata ที่ มหานครเออร์แบน"),
        (re.compile(r"\bTalk to Entrata in Minaula\b"), "คุยกับ Entrata ที่ เมืองมินาอุละ"),
        (re.compile(r"\bTalk to Entrata in Port Spargas\b"), "คุยกับ Entrata ที่ เมืองท่าสปาร์กัส"),
        (re.compile(r"\bTalk to Entrata in Rokoko\b"), "คุยกับ Entrata ที่ เมืองโลโคโค"),
        (re.compile(r"\bTalk to Tilia in Fort Bailune\b"), "คุยกับ Tilia ที่ ฐานทัพไบลูน"),
        (re.compile(r"\bTalk to\b"), "คุยกับ"),
        (re.compile(r"\bBoss\b"), "บอส"),
        (re.compile(r"\bReward\b"), "รางวัล"),
        (re.compile(r"\bLocation\b"), "สถานที่รับเรด"),
        (re.compile(r"\bRaid Box\b"), "กล่องเรด (Raid Box)"),
    ]
    raids["html"] = translate_html_text_nodes(raids["html"], raid_rules)
    raids_path.write_text(json.dumps(raids, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("  guide/raids             : Translated to Thai", flush=True)

    # 6e. lottery.json
    lot_path = gdir / "lottery.json"
    lot = json.loads(lot_path.read_text(encoding="utf-8"))
    lot_rules = [
        (re.compile(r"\bItems\b"), "รายการไอเทมรางวัล"),
        (re.compile(r"\bLocation\b"), "สถานที่"),
        (re.compile(r"\bCost\b"), "ค่าใช้จ่าย"),
        (re.compile(r"\bSpina\b"), "Spina"),
    ]
    lot["html"] = translate_html_text_nodes(lot["html"], lot_rules)
    lot_path.write_text(json.dumps(lot, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("  guide/lottery           : Translated to Thai", flush=True)

    # 6f. classes.json — Thai headers, requirements, locations, and class names
    cls_path = gdir / "classes.json"
    cls = json.loads(cls_path.read_text(encoding="utf-8"))
    cls_rules = [
        (re.compile(r"\bDescription\b"), "คำอธิบายอาชีพ"),
        (re.compile(r"\bRequirement\b"), "เงื่อนไขการเปลี่ยนอาชีพ"),
        (re.compile(r"\bMust be level (\d+)\b"), r"ต้องมีเลเวล \1 ขึ้นไป"),
        (re.compile(r"\bMust be an?\b"), "ต้องเป็นอาชีพ"),
        (re.compile(r"\bLocation:\b"), "สถานที่เปลี่ยนอาชีพ:"),
        (re.compile(r"\bSkills\b"), "สกิลประจำอาชีพ"),
        (re.compile(r"\bQuest -\b"), "เควสต์ -"),
        (re.compile(r"\bItem -\b"), "ไอเทม -"),
        (re.compile(r"\bFort Bailune\b"), "ฐานทัพไบลูน"),
        (re.compile(r"\bBailune City\b"), "เมืองไบลูน"),
        (re.compile(r"\bRokoko City\b"), "เมืองโลโคโค"),
        (re.compile(r"\bCapital City Sofya\b"), "มหานครโซเฟีย"),
        (re.compile(r"\bCapital City Saterica\b"), "มหานครซาเทริกา"),
        (re.compile(r"\bCapital City Elban\b"), "มหานครเออร์แบน"),
        (re.compile(r"\bPort Spargas\b"), "เมืองท่าสปาร์กัส"),
        (re.compile(r"\bMinaula City\b"), "เมืองมินาอุละ"),
        (re.compile(r"\bKleya City\b"), "เมืองเคลย่า"),
        (re.compile(r"\bDraug\b"), "ดราอุก"),
        (re.compile(r"\bLograth City\b"), "เมืองโลกราธ"),
    ]
    for en, th in CLASS_TH.items():
        if "_" not in en:
            cls_rules.append((re.compile(rf"\b{re.escape(en)}\b"), th.split(" (")[0]))
    cls["treeHtml"] = translate_html_text_nodes(cls["treeHtml"], cls_rules)
    cls["classLabels"] = {c: CLASS_TH.get(c, c) for c in cls.get("classList", [])}
    for cname in list(cls.get("details", {}).keys()):
        cls["details"][cname] = translate_html_text_nodes(cls["details"][cname], cls_rules)
    cls_path.write_text(json.dumps(cls, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("  guide/classes           : Translated 23 classes to Thai", flush=True)

    # 6g. skills.json — Thai labels + obtain labels
    sk_path = gdir / "skills.json"
    sk = json.loads(sk_path.read_text(encoding="utf-8"))
    sk_rules = [
        (re.compile(r"\bSkills\b"), "รายการสกิล"),
        (re.compile(r"\bQuest -"), "เควสต์ -"),
        (re.compile(r"\bItem -"), "ไอเทม -"),
    ]
    for en, th in CLASS_TH.items():
        if "_" not in en:
            sk_rules.append((re.compile(rf"\b{re.escape(en)}\b"), th.split(" (")[0]))
    sk["classLabels"] = {c: CLASS_TH.get(c, c) for c in sk.get("classList", [])}
    for cname in list(sk.get("byClass", {}).keys()):
        sk["byClass"][cname] = translate_html_text_nodes(sk["byClass"][cname], sk_rules)
    sk_path.write_text(json.dumps(sk, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("  guide/skills            : Translated 23 skill pages to Thai", flush=True)


def main():
    translate_items_and_meta()
    translate_blacksmiths()
    translate_zones_and_search()
    translate_quests()
    translate_events()
    translate_guides()
    print("\nALL THAI TRANSLATIONS COMPLETED!", flush=True)


if __name__ == "__main__":
    main()
