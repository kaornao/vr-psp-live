#!/usr/bin/env python3
"""从 vtbs.moe VDB 生成 VirtuaReal / P-SP 监控名单 → 仓库根目录 roster.json"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VDB_URL = "https://vdb.vtbs.moe/json/list.json"
VDB_PATH = ROOT / "data" / "vdb_list.json"
ROSTER_PATH = ROOT / "roster.json"

GROUPS = {
    "6a8d2bed-dc2e-5ce1-a3bd-e31317aa4e23": "VR",  # VirtuaReal
    "f076e35d-500d-57ba-9149-6caed8275768": "PSP",  # P-SP / PSPlive
}

UA = {"User-Agent": "vr-psp-live/1.0 (https://github.com/; open-source live board)"}


def fetch_vdb(force: bool = False) -> Path:
    VDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if VDB_PATH.exists() and VDB_PATH.stat().st_size > 1000 and not force:
        return VDB_PATH
    print(f"下载 VDB → {VDB_PATH}", flush=True)
    req = urllib.request.Request(VDB_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp, open(VDB_PATH, "wb") as f:
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return VDB_PATH


def pick_name(name: dict | None) -> str:
    if not name:
        return ""
    prefer = name.get("default")
    if prefer and name.get(prefer):
        return str(name[prefer])
    for key in ("cn", "en", "jp"):
        if name.get(key):
            return str(name[key])
    extras = name.get("extra") or []
    return str(extras[0]) if extras else ""


def bilibili_uid(accounts: list | None) -> int | None:
    for acc in accounts or []:
        if acc.get("platform") == "bilibili" and acc.get("id"):
            try:
                return int(acc["id"])
            except (TypeError, ValueError):
                continue
    return None


def build(force_vdb: bool = False) -> dict:
    fetch_vdb(force=force_vdb)
    data = json.loads(VDB_PATH.read_text(encoding="utf-8"))
    members: list[dict] = []
    seen: set[int] = set()

    for v in data.get("vtbs") or []:
        if v.get("type") != "vtuber" or v.get("bot"):
            continue
        bucket = GROUPS.get(v.get("group"))
        if not bucket:
            continue
        uid = bilibili_uid(v.get("accounts"))
        if not uid or uid in seen:
            continue
        seen.add(uid)
        members.append(
            {
                "uid": uid,
                "name": pick_name(v.get("name")),
                "bucket": bucket,
                "group_name": v.get("group_name") or ("VirtuaReal" if bucket == "VR" else "P-SP"),
                "uuid": v.get("uuid"),
            }
        )

    members.sort(key=lambda m: (m["bucket"], m["name"].lower()))
    roster = {
        "source": "vdb.vtbs.moe",
        "vdb_timestamp": (data.get("meta") or {}).get("timestamp"),
        "groups": {"VR": "VirtuaReal", "PSP": "P-SP / PSPlive"},
        "count": {
            "total": len(members),
            "VR": sum(1 for m in members if m["bucket"] == "VR"),
            "PSP": sum(1 for m in members if m["bucket"] == "PSP"),
        },
        "members": members,
    }
    ROSTER_PATH.write_text(json.dumps(roster, ensure_ascii=False, indent=2), encoding="utf-8")
    return roster


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 VR / PSP 开播监控名单")
    ap.add_argument("--force-vdb", action="store_true")
    args = ap.parse_args()
    roster = build(force_vdb=args.force_vdb)
    print(
        f"已写入 {ROSTER_PATH}  total={roster['count']['total']} "
        f"VR={roster['count']['VR']} PSP={roster['count']['PSP']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
