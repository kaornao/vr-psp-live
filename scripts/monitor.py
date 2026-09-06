#!/usr/bin/env python3
"""轮询 B 站开播状态 → 仓库根目录 status.json（供网页看板读取）。"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROSTER_PATH = ROOT / "roster.json"
STATUS_PATH = ROOT / "status.json"
TEMPLATE_PATH = ROOT / "index.html"
BOARD_PATH = ROOT / "VR-PSP开播看板.html"
API = "https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids"
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; vr-psp-live/1.0)",
    "Referer": "https://live.bilibili.com/",
    "Origin": "https://live.bilibili.com",
}

BATCH = 40
BATCH_PAUSE_S = 1.0
DEFAULT_INTERVAL_S = 60


def load_roster() -> dict:
    if not ROSTER_PATH.exists():
        from build_roster import build

        return build()
    return json.loads(ROSTER_PATH.read_text(encoding="utf-8"))


def post_uids(uids: list[int]) -> dict:
    body = json.dumps({"uids": uids}).encode("utf-8")
    req = urllib.request.Request(
        API,
        data=body,
        headers={**UA, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chunked(items: list[int], n: int):
    for i in range(0, len(items), n):
        yield items[i : i + n]


def fetch_live_map(uids: list[int]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i, batch in enumerate(chunked(uids, BATCH)):
        if i:
            time.sleep(BATCH_PAUSE_S)
        try:
            payload = post_uids(batch)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"[warn] batch failed: {e}", flush=True)
            continue
        if payload.get("code") != 0:
            print(f"[warn] api code={payload.get('code')} msg={payload.get('message')}", flush=True)
            continue
        data = payload.get("data") or {}
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    out[str(k)] = v
        elif isinstance(data, list):
            for v in data:
                if isinstance(v, dict) and "uid" in v:
                    out[str(v["uid"])] = v
    return out


def merge_status(roster: dict, live_map: dict[str, dict]) -> dict:
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    live_rows = []
    offline = 0
    for m in roster.get("members") or []:
        uid = m["uid"]
        info = live_map.get(str(uid)) or {}
        live_status = int(info.get("live_status") or 0)
        room_id = info.get("room_id") or info.get("roomid") or 0
        row = {
            "uid": uid,
            "name": m.get("name") or info.get("uname") or str(uid),
            "bucket": m.get("bucket"),
            "group_name": m.get("group_name"),
            "live_status": live_status,
            "title": info.get("title") or "",
            "online": info.get("online") or 0,
            "room_id": room_id,
            "cover": info.get("cover_from_user") or info.get("keyframe") or "",
            "face": info.get("face") or "",
            "area": info.get("area_v2_name") or info.get("area_name") or "",
            "parent_area": info.get("area_v2_parent_name") or "",
            "live_url": f"https://live.bilibili.com/{room_id}" if room_id else f"https://space.bilibili.com/{uid}",
        }
        if live_status == 1:
            live_rows.append(row)
        else:
            offline += 1

    live_rows.sort(key=lambda r: (-int(r.get("online") or 0), r["bucket"], r["name"]))
    return {
        "updated_at": now,
        "counts": {
            "live": len(live_rows),
            "offline": offline,
            "roster": len(roster.get("members") or []),
            "VR_live": sum(1 for r in live_rows if r["bucket"] == "VR"),
            "PSP_live": sum(1 for r in live_rows if r["bucket"] == "PSP"),
        },
        "live": live_rows,
    }


def print_summary(status: dict) -> None:
    c = status["counts"]
    print(
        f"[{status['updated_at']}] 开播 {c['live']} "
        f"(VR {c['VR_live']} / PSP {c['PSP_live']}) · 名单 {c['roster']}",
        flush=True,
    )
    for r in status["live"]:
        print(
            f"  ● [{r['bucket']}] {r['name']}  "
            f"{r['online']}人  {r['title'][:40]}  {r['live_url']}",
            flush=True,
        )


def write_standalone_board(status: dict) -> Path:
    """生成可双击打开的单文件看板（内嵌数据，不依赖 fetch / 本地服务器）。"""
    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = json.dumps(status, ensure_ascii=False)
    embed = f"<script>window.__STATUS__ = {payload};</script>\n"
    if "<!--EMBED_STATUS-->" in tpl:
        html = tpl.replace("<!--EMBED_STATUS-->", embed + "<!--EMBED_STATUS-->")
    else:
        html = tpl.replace("<script>", embed + "<script>", 1)
    BOARD_PATH.write_text(html, encoding="utf-8")
    return BOARD_PATH


def once() -> dict:
    roster = load_roster()
    uids = [int(m["uid"]) for m in roster.get("members") or []]
    live_map = fetch_live_map(uids)
    status = merge_status(roster, live_map)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    board = write_standalone_board(status)
    print(f"已生成可双击打开的看板: {board}", flush=True)
    return status


def main() -> int:
    ap = argparse.ArgumentParser(description="监控 VirtuaReal / P-SP 开播状态")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.interval < 30:
        print("[warn] interval 过短易撞风控，已抬到 30s", flush=True)
        args.interval = 30

    while True:
        try:
            status = once()
            if not args.quiet:
                print_summary(status)
        except KeyboardInterrupt:
            print("\n已停止", flush=True)
            return 0
        except Exception as e:
            print(f"[error] {e}", flush=True)
        if args.once:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
