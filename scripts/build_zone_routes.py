#!/usr/bin/env python3
"""
Build data/db/zone_routes.json from data/db/zones/*.json
Gives every map across EP1-EP7, Raids, and Events:
- ep, name, type (town/field/dungeon)
- path: step-by-step breadcrumb chain from top-level road/town to this map
- prev / next: adjacent maps on the episode main road (for root-level maps)
- nearestTown: closest town before this map in the episode
- children: directly connected sub-maps you can walk to from this map
"""

import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ZONES_DIR = REPO_ROOT / "data" / "db" / "zones"
OUT_FILE = REPO_ROOT / "data" / "db" / "zone_routes.json"

EP_ORDER = ["EP1", "EP2", "EP3", "EP4", "EP5", "EP6", "EP7", "Raids", "Events"]


def main():
    routes = {}  # slug -> info
    by_name = {}  # lowercase name -> slug (for fuzzy lookup from obtain.html)

    for ep in EP_ORDER:
        p = ZONES_DIR / f"{ep}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        tree = data.get("tree", [])

        # Walk top-level road to track prev/next and nearest town
        last_town = None
        for idx, root_node in enumerate(tree):
            if root_node.get("type") == "town":
                last_town = {"slug": root_node["slug"], "name": root_node["name"], "ep": ep}

            prev_node = tree[idx - 1] if idx > 0 else None
            next_node = tree[idx + 1] if idx + 1 < len(tree) else None

            def walk(node, chain, nearest_town, is_root=False):
                slug = node["slug"]
                name = node["name"]
                ztype = node.get("type", "field")
                cur_town = {"slug": slug, "name": name, "ep": ep} if ztype == "town" else nearest_town
                cur_chain = chain + [{"slug": slug, "name": name, "ep": ep, "type": ztype}]
                children = [
                    {"slug": c["slug"], "name": c["name"], "ep": ep, "type": c.get("type", "field")}
                    for c in (node.get("children") or [])
                ]

                entry = {
                    "slug": slug,
                    "name": name,
                    "ep": ep,
                    "type": ztype,
                    "path": cur_chain,
                    "children": children,
                }
                if is_root and prev_node:
                    entry["prev"] = {"slug": prev_node["slug"], "name": prev_node["name"], "ep": ep, "type": prev_node.get("type", "field")}
                if is_root and next_node:
                    entry["next"] = {"slug": next_node["slug"], "name": next_node["name"], "ep": ep, "type": next_node.get("type", "field")}
                if nearest_town and nearest_town["slug"] != slug:
                    entry["nearestTown"] = nearest_town

                # Prefer the first/canonical episode occurrence (e.g. EP1 over Raids) or deeper path
                if slug not in routes:
                    routes[slug] = entry
                else:
                    # Merge additional children connections if map appears in multiple EP trees
                    ex = routes[slug]
                    ex_child_slugs = {c["slug"] for c in ex.get("children", [])}
                    for c in children:
                        if c["slug"] not in ex_child_slugs:
                            ex.setdefault("children", []).append(c)
                            ex_child_slugs.add(c["slug"])

                by_name.setdefault(name.strip().lower(), slug)
                by_name.setdefault(slug.strip().lower(), slug)

                for c in (node.get("children") or []):
                    walk(c, cur_chain, cur_town, is_root=False)

            walk(root_node, [], last_town, is_root=True)

    payload = {"routes": routes, "byName": by_name}
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Built zone_routes.json: {len(routes)} maps, {OUT_FILE.stat().st_size / 1024:.1f} KB")

    # Quick sample check
    for sample_name in ["ช่องลมโลโคโค", "หอคอยแห่งทวยเทพ", "ถ้ำแห่งลม", "ฐานทัพไบลูน"]:
        s = by_name.get(sample_name.lower())
        if s:
            r = routes[s]
            path_str = " -> ".join(x["name"] for x in r["path"])
            prev_str = r.get("prev", {}).get("name", "-")
            town_str = r.get("nearestTown", {}).get("name", "-")
            print(f"  [{sample_name}] path={path_str} | prev={prev_str} | nearestTown={town_str} | children={len(r['children'])}")


if __name__ == "__main__":
    main()
