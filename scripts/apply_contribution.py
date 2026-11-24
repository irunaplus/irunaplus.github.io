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
OBTAIN_DIR = REPO_ROOT / "data" / "obtain"

ALLOWED_FILENAME_RE = re.compile(r"^[a-z0-9_]+\.json$")
ALLOWED_OBTAIN_FOLDERS = {"quest", "drop", "shop"}


def extract_json_block(text: str) -> dict:
    matches = re.findall(r"```json\s*(\{[\s\S]*?\})\s*```", text or "")
    if not matches:
        raise ValueError("ไม่พบบล็อก ```json ... ``` ในเนื้อหา Issue")
    # Use the last JSON block in the issue body
    return json.loads(matches[-1])


def main():
    body = os.environ.get("ISSUE_BODY", "")
    payload = extract_json_block(body)

    ptype = payload.get("type")
    if ptype not in ("job_update", "job_patch", "obtain_update", "obtain_patch"):
        raise ValueError(f"Unsupported contribution type: {ptype}")

    new_skills = payload.get("newSkills") or {}
    skill_patches = payload.get("skillPatches") or {}
    skills_master = None
    obtain_details = payload.get("obtainDetails") or []
    if not isinstance(obtain_details, list):
        raise ValueError("obtainDetails must be a list")
    for entry in obtain_details:
        if not isinstance(entry, dict):
            raise ValueError("Each obtain detail must be an object")
        folder = str(entry.get("folder", "")).strip().lower()
        filename = str(entry.get("file", "")).strip().lower()
        if folder not in ALLOWED_OBTAIN_FOLDERS or not ALLOWED_FILENAME_RE.match(filename):
            raise ValueError(f"Invalid obtain detail path: {folder}/{filename}")
        if ("data" in entry) == ("patch" in entry):
            raise ValueError("Each obtain detail must contain either data or patch")
        if not isinstance(entry.get("data", entry.get("patch")), dict):
            raise ValueError("Obtain detail data or patch must be an object")
        if "patch" in entry and not (OBTAIN_DIR / folder / filename).exists():
            raise ValueError(f"Cannot patch missing obtain detail: {folder}/{filename}")
    if ptype in ("job_update", "job_patch"):
        filename = str(payload.get("file", "")).strip()
        if not ALLOWED_FILENAME_RE.match(filename):
            raise ValueError(f"Invalid job filename: {filename!r}")

        job_obj = payload.get("job")
        if not isinstance(job_obj, dict) or not job_obj.get("jobId"):
            raise ValueError("Missing required job field (jobId)")
        if ptype == "job_update" and not job_obj.get("name"):
            raise ValueError("Missing required job field (name)")
        job_skills = job_obj.get("skills", [])
        if not isinstance(job_skills, list):
            raise ValueError("Job skills must be a list")
        for skill in job_skills:
            if not isinstance(skill, dict):
                raise ValueError("Each job skill must be an object")
            if not isinstance(skill.get("skillId"), str) or not skill["skillId"]:
                raise ValueError("Each job skill must have a skillId")
            if ptype == "job_patch" and any(key not in {"skillId", "obtain", "lv", "maxSkillLevel", "replaceObtain"} for key in skill):
                raise ValueError(f"Unsupported job skill patch fields for {skill['skillId']!r}")
            if "replaceObtain" in skill and not isinstance(skill["replaceObtain"], bool):
                raise ValueError(f"Invalid replaceObtain for skill {skill.get('skillId', '')!r}")
            if "maxSkillLevel" in skill:
                max_level = skill["maxSkillLevel"]
                if max_level is not None and (not isinstance(max_level, int) or isinstance(max_level, bool) or max_level < 1):
                    raise ValueError(f"Invalid maxSkillLevel for skill {skill.get('skillId', '')!r}")
        remove_skills = payload.get("removeSkills", [])
        if ptype == "job_patch" and (
            not isinstance(remove_skills, list)
            or any(not isinstance(skill_id, str) or not skill_id for skill_id in remove_skills)
        ):
            raise ValueError("removeSkills must be a list of skill IDs")
        if not isinstance(new_skills, dict) or not isinstance(skill_patches, dict):
            raise ValueError("newSkills and skillPatches must be objects")
        if ptype == "job_patch":
            for skill_id, skill_data in new_skills.items():
                if (
                    not re.match(r"^[a-z0-9_]+$", str(skill_id))
                    or not isinstance(skill_data, dict)
                    or not str(skill_data.get("name", "")).strip()
                ):
                    raise ValueError(f"Invalid new skill definition: {skill_id!r}")
                if not isinstance(skill_data.get("type", []), list) or not isinstance(skill_data.get("desc", ""), str):
                    raise ValueError(f"Invalid new skill metadata: {skill_id!r}")
                if "summonSkills" in skill_data and not isinstance(skill_data["summonSkills"], list):
                    raise ValueError(f"Invalid summonSkills list for {skill_id!r}")
            if new_skills or skill_patches:
                skills_master = json.loads(SKILLS_FILE.read_text(encoding="utf-8"))
                if not isinstance(skills_master, dict):
                    raise ValueError("Skill master data must be an object")
                for skill_id in skill_patches:
                    if skill_id not in skills_master:
                        raise ValueError(f"Cannot patch missing skill metadata: {skill_id}")
        if isinstance(new_skills, dict):
            for skill_data in new_skills.values():
                if not isinstance(skill_data, dict):
                    continue
                sub_skills = skill_data.get("summonSkills")
                if not isinstance(sub_skills, list):
                    continue
                for sub_skill in sub_skills:
                    if not isinstance(sub_skill, dict) or "requiresSkillLevel" not in sub_skill:
                        continue
                    required_level = sub_skill["requiresSkillLevel"]
                    if not isinstance(required_level, int) or isinstance(required_level, bool) or required_level < 1:
                        raise ValueError(f"Invalid requiresSkillLevel for sub-skill {sub_skill.get('name', '')!r}")
        for skill_id, patch in skill_patches.items():
            if not re.match(r"^[a-z0-9_]+$", str(skill_id)) or not isinstance(patch, dict):
                raise ValueError(f"Invalid skill patch: {skill_id!r}")
            if any(field not in {"name", "type", "desc", "image", "summonSkills"} for field in patch):
                raise ValueError(f"Unsupported skill metadata patch fields for {skill_id!r}")
            for field in ("name", "desc", "image"):
                if field in patch and patch[field] is not None and not isinstance(patch[field], str):
                    raise ValueError(f"Invalid {field} for skill metadata patch {skill_id!r}")
            if "type" in patch and (
                patch["type"] is not None
                and (not isinstance(patch["type"], list) or any(not isinstance(value, str) for value in patch["type"]))
            ):
                raise ValueError(f"Invalid type for skill metadata patch {skill_id!r}")
            if "summonSkills" in patch:
                sub_patch = patch["summonSkills"]
                if not isinstance(sub_patch, dict) or set(sub_patch) - {"upsert", "remove"}:
                    raise ValueError(f"Invalid summonSkills patch for {skill_id!r}")
                if not isinstance(sub_patch.get("upsert", []), list) or not isinstance(sub_patch.get("remove", []), list):
                    raise ValueError(f"summonSkills upsert/remove must be lists for {skill_id!r}")
                for sub_skill in sub_patch.get("upsert", []):
                    if not isinstance(sub_skill, dict) or not str(sub_skill.get("name", "")).strip():
                        raise ValueError(f"Invalid summon sub-skill patch for {skill_id!r}")
                    if "requiresSkillLevel" in sub_skill:
                        required_level = sub_skill["requiresSkillLevel"]
                        if required_level is not None and (
                            not isinstance(required_level, int) or isinstance(required_level, bool) or required_level < 1
                        ):
                            raise ValueError(f"Invalid requiresSkillLevel for sub-skill {sub_skill['name']!r}")
                if any(not isinstance(name, str) for name in sub_patch.get("remove", [])):
                    raise ValueError(f"summonSkills remove must contain names for {skill_id!r}")

        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        target_job = JOBS_DIR / filename
        if ptype == "job_update":
            target_job.write_text(json.dumps(job_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            if not target_job.exists():
                raise ValueError(f"Cannot patch missing job file: {filename}")
            existing_job = json.loads(target_job.read_text(encoding="utf-8"))
            if str(existing_job.get("jobId", "")).lower() != str(job_obj["jobId"]).lower():
                raise ValueError(f"Job ID does not match target file: {filename}")
            updated_job = dict(existing_job)
            for field in ("name", "desc", "obtain", "inherits"):
                if field in job_obj:
                    if field == "inherits" and job_obj[field] == []:
                        updated_job.pop(field, None)
                    else:
                        updated_job[field] = job_obj[field]
            removed_skill_ids = set(remove_skills)
            updated_skills = [
                dict(skill) for skill in existing_job.get("skills", [])
                if skill.get("skillId") not in removed_skill_ids
            ]
            for skill_patch in job_skills:
                skill_id = skill_patch["skillId"]
                current_index = next(
                    (i for i, current_skill in enumerate(updated_skills) if current_skill.get("skillId") == skill_id),
                    None,
                )
                current = dict(updated_skills[current_index]) if current_index is not None else {"skillId": skill_id}
                for field in ("obtain", "lv", "replaceObtain"):
                    if field in skill_patch:
                        current[field] = skill_patch[field]
                if "maxSkillLevel" in skill_patch:
                    if skill_patch["maxSkillLevel"] is None:
                        current.pop("maxSkillLevel", None)
                    else:
                        current["maxSkillLevel"] = skill_patch["maxSkillLevel"]
                if current_index is not None:
                    updated_skills[current_index] = current
                else:
                    updated_skills.append(current)
            updated_job["skills"] = updated_skills
            target_job.write_text(json.dumps(updated_job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {target_job.relative_to(REPO_ROOT)}")

    # Merge any new skills into data/skills.json (without overwriting existing skills accidentally)
    if (isinstance(new_skills, dict) and new_skills) or (isinstance(skill_patches, dict) and skill_patches):
        if skills_master is None:
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
            if isinstance(sub_skills, list):
                clean_subs = []
                for ss in sub_skills:
                    if not isinstance(ss, dict) or not str(ss.get("name", "")).strip():
                        continue
                    sub_obj = {"name": str(ss["name"]).strip()}
                    if str(ss.get("type", "")).strip():
                        sub_obj["type"] = str(ss["type"]).strip()
                    if str(ss.get("req", "")).strip():
                        sub_obj["req"] = str(ss["req"]).strip()
                    if "requiresSkillLevel" in ss:
                        sub_obj["requiresSkillLevel"] = ss["requiresSkillLevel"]
                    if str(ss.get("desc", "")).strip():
                        sub_obj["desc"] = str(ss["desc"]).strip()
                    if str(ss.get("image", "")).strip():
                        sub_obj["image"] = str(ss["image"]).strip()
                    clean_subs.append(sub_obj)
                if clean_subs:
                    entry["summonSkills"] = clean_subs
                else:
                    entry["summonSkills"] = []
            elif existing.get("summonSkills") and "summonSkills" not in sdata:
                entry["summonSkills"] = existing["summonSkills"]
            skills_master[sid] = entry
            added.append(sid)

        for sid, patch in skill_patches.items():
            entry = dict(skills_master[sid])
            for field in ("name", "type", "desc", "image"):
                if field in patch:
                    if patch[field] is None:
                        entry.pop(field, None)
                    else:
                        entry[field] = patch[field]
            sub_patch = patch.get("summonSkills")
            if sub_patch:
                current_subs = {ss["name"]: dict(ss) for ss in entry.get("summonSkills", [])}
                for name in sub_patch.get("remove", []):
                    current_subs.pop(name, None)
                for sub_skill in sub_patch.get("upsert", []):
                    name = sub_skill["name"]
                    current = current_subs.get(name, {"name": name})
                    for field, value in sub_skill.items():
                        if field == "name":
                            continue
                        if value is None:
                            current.pop(field, None)
                        else:
                            current[field] = value
                    current_subs[name] = current
                existing_order = [ss["name"] for ss in entry.get("summonSkills", []) if ss["name"] in current_subs]
                new_names = [name for name in current_subs if name not in existing_order]
                entry["summonSkills"] = [current_subs[name] for name in existing_order + new_names]
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

    # Write any detailed obtain condition files (data/obtain/{quest,drop,shop}/<skill>_<lv>.json)
    if isinstance(obtain_details, list) and obtain_details:
        saved_obt = []
        for entry in obtain_details:
            folder = str(entry.get("folder", "")).strip().lower()
            fname = str(entry.get("file", "")).strip().lower()
            target_dir = OBTAIN_DIR / folder
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / fname
            if "patch" in entry:
                if not target_file.exists():
                    raise ValueError(f"Cannot patch missing obtain detail: {folder}/{fname}")
                data = json.loads(target_file.read_text(encoding="utf-8"))
                data.update(entry["patch"])
            else:
                data = entry["data"]
            target_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            saved_obt.append(f"{folder}/{fname}")
        if saved_obt:
            print(f"Saved {len(saved_obt)} obtain detail file(s): {saved_obt}")


if __name__ == "__main__":
    main()
