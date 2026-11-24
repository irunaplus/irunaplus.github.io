#!/usr/bin/env python3
"""
Apply an owner-approved job/skill contribution from a GitHub Issue body.
Reads ISSUE_BODY from environment variable, extracts the ```json ... ``` payload,
validates it strictly against allowlisted paths, and updates data/jobs/<file>
and data/skills.json cleanly.
"""

import json
import os
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
JOBS_DIR = REPO_ROOT / "data" / "jobs"
SKILLS_FILE = REPO_ROOT / "data" / "skills.json"
NPC_DIR = REPO_ROOT / "data" / "NPC"
NPC_MAP_FILE = NPC_DIR / "npc_id_map.json"

ALLOWED_FILENAME_RE = re.compile(r"^[a-z0-9_]+\.json$")


def extract_json_block(text: str) -> dict:
    matches = re.findall(r"```json\s*(\{[\s\S]*?\})\s*```", text or "")
    if not matches:
        raise ValueError("ไม่พบบล็อก ```json ... ``` ในเนื้อหา Issue")
    # Use the last JSON block in the issue body
    return json.loads(matches[-1])


def main():
    body = os.environ.get("ISSUE_BODY", "")
    payload = extract_json_block(body)

    if payload.get("type") != "job_update":
        raise ValueError(f"Unsupported contribution type: {payload.get('type')}")

    filename = str(payload.get("file", "")).strip()
    if not ALLOWED_FILENAME_RE.match(filename):
        raise ValueError(f"Invalid job filename: {filename!r}")

    job_obj = payload.get("job")
    if not isinstance(job_obj, dict) or not job_obj.get("jobId") or not job_obj.get("name"):
        raise ValueError("Missing required job fields (jobId, name)")

    # Write job JSON
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    target_job = JOBS_DIR / filename
    target_job.write_text(
        json.dumps(job_obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {target_job.relative_to(REPO_ROOT)}")

    # Merge any new skills into data/skills.json (without overwriting existing skills accidentally)
    new_skills = payload.get("newSkills") or {}
    if isinstance(new_skills, dict) and new_skills:
        skills_master = json.loads(SKILLS_FILE.read_text(encoding="utf-8"))
        added = []
        for sid, sdata in new_skills.items():
            if not re.match(r"^[a-z0-9_]+$", str(sid)):
                continue
            if not isinstance(sdata, dict) or not sdata.get("name"):
                continue
            existing = skills_master.get(sid) or {}
            entry = {
                "name": str(sdata["name"]).strip(),
                "type": list(sdata.get("type") or ["สกิลกดใช้"]),
                "desc": str(sdata.get("desc") or "").strip(),
            }
            img = sdata.get("image") or existing.get("image")
            if img:
                entry["image"] = str(img).strip()
            sub_skills = sdata.get("summonSkills")
            if isinstance(sub_skills, list) and sub_skills:
                clean_subs = []
                for ss in sub_skills:
                    if not isinstance(ss, dict) or not str(ss.get("name", "")).strip():
                        continue
                    sub_obj = {"name": str(ss["name"]).strip()}
                    if str(ss.get("type", "")).strip():
                        sub_obj["type"] = str(ss["type"]).strip()
                    if str(ss.get("req", "")).strip():
                        sub_obj["req"] = str(ss["req"]).strip()
                    if str(ss.get("desc", "")).strip():
                        sub_obj["desc"] = str(ss["desc"]).strip()
                    if str(ss.get("image", "")).strip():
                        sub_obj["image"] = str(ss["image"]).strip()
                    clean_subs.append(sub_obj)
                if clean_subs:
                    entry["summonSkills"] = clean_subs
            elif existing.get("summonSkills") and "summonSkills" not in sdata:
                entry["summonSkills"] = existing["summonSkills"]
            skills_master[sid] = entry
            added.append(sid)
        if added:
            SKILLS_FILE.write_text(
                json.dumps(skills_master, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Merged {len(added)} skill(s) into data/skills.json: {added}")

    # Merge any new NPCs into data/NPC/npc_id_map.json and data/NPC/<npc_id>.json
    new_npcs = payload.get("newNpcs") or {}
    if isinstance(new_npcs, dict) and new_npcs:
        NPC_DIR.mkdir(parents=True, exist_ok=True)
        npc_map = json.loads(NPC_MAP_FILE.read_text(encoding="utf-8")) if NPC_MAP_FILE.exists() else {}
        added_npcs = []
        for nid, ndata in new_npcs.items():
            nid = str(nid).strip().lower()
            if not re.match(r"^[a-z0-9_]+$", nid):
                continue
            if not isinstance(ndata, dict) or not str(ndata.get("name", "")).strip():
                continue
            n_name = str(ndata["name"]).strip()
            npc_map[n_name] = nid
            npc_file = NPC_DIR / f"{nid}.json"
            existing_npc = json.loads(npc_file.read_text(encoding="utf-8")) if npc_file.exists() else {}
            npc_obj = {}
            img = str(ndata.get("image") or existing_npc.get("image") or "").strip()
            loc = str(ndata.get("location") or existing_npc.get("location") or "").strip()
            desc = str(ndata.get("desc") or existing_npc.get("desc") or "").strip()
            if img:
                npc_obj["image"] = img
            if loc:
                npc_obj["location"] = loc
            if desc:
                npc_obj["desc"] = desc
            npc_file.write_text(
                json.dumps(npc_obj, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            added_npcs.append(f"{n_name} ({nid})")
        if added_npcs:
            NPC_MAP_FILE.write_text(
                json.dumps(npc_map, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"Merged {len(added_npcs)} NPC(s) into data/NPC/: {added_npcs}")


if __name__ == "__main__":
    main()
