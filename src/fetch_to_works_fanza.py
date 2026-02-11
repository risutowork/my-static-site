from __future__ import annotations

from pathlib import Path
import os
import json
import time
import requests
from typing import Any, Dict, List, Optional


BASE = Path(__file__).resolve().parent
OUT_FILE = BASE / "data" / "works.json"

API_ID = os.getenv("DMM_API_ID")
AFFILIATE_ID = os.getenv("DMM_AFFILIATE_ID")


# =========================
# 取得設定（ここだけ触ればOK）
# =========================
SITE_NAME = "Review Catalog"

# FANZA動画（ビデオ）新着
SITE = "FANZA"
SERVICE = "digital"
FLOOR = "videoa"
SORT = "date"

HITS = 100               # 1回で取る件数（最大100）
PAGES = 5                # 何ページ分取るか（100×5=最大500件）
SLEEP_SEC = 0.8          # API負荷回避（少し待つ）

MAX_TOTAL_WORKS = 5000   # works.json の最大保存数（増えすぎ防止）


def load_existing() -> Dict[str, Any]:
    """既存works.jsonを読む。なければ空で作る。"""
    if OUT_FILE.exists():
        try:
            data = json.loads(OUT_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"site_name": SITE_NAME, "works": []}
            if "works" not in data or not isinstance(data["works"], list):
                data["works"] = []
            if "site_name" not in data:
                data["site_name"] = SITE_NAME
            return data
        except Exception:
            # 壊れてたら作り直し（安全側）
            return {"site_name": SITE_NAME, "works": []}
    return {"site_name": SITE_NAME, "works": []}


def fetch_items(hits: int = 100, offset: int = 1, sort: str = "date", keyword: str | None = None) -> List[dict]:
    if not API_ID or not AFFILIATE_ID:
        raise SystemExit("環境変数 DMM_API_ID と DMM_AFFILIATE_ID を設定してください。")

    url = "https://api.dmm.com/affiliate/v3/ItemList"
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": SITE,
        "service": SERVICE,
        "floor": FLOOR,
        "hits": str(hits),
        "offset": str(offset),
        "sort": sort,
        "output": "json",
    }
    if keyword:
        params["keyword"] = keyword

    # 軽いリトライ（回線/一時エラー対策）
    for attempt in range(3):
        r = requests.get(url, params=params, timeout=30)
        print(f"status: {r.status_code} (offset={offset}, hits={hits})")
        if r.status_code == 200:
            data = r.json()
            return data.get("result", {}).get("items", []) or []

        # 失敗時は本文も少し出す
        print(r.text[:1000])
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))
            continue
        r.raise_for_status()

    return []


def pick_best_image(item: dict) -> str | None:
    img = item.get("imageURL") or {}
    if isinstance(img, dict):
        return img.get("large") or img.get("list") or img.get("small")
    return None


def extract_genres(item: dict) -> List[str]:
    iteminfo = item.get("iteminfo") or {}
    genres: List[str] = []
    for g in (iteminfo.get("genre") or []):
        name = (g or {}).get("name")
        if name:
            genres.append(name)
    # 重複除去しつつ順序維持
    seen = set()
    out = []
    for x in genres:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_actresses(item: dict) -> List[str]:
    iteminfo = item.get("iteminfo") or {}
    actresses: List[str] = []
    for a in (iteminfo.get("actress") or []):
        name = (a or {}).get("name")
        if name:
            actresses.append(name)
    # 重複除去しつつ順序維持
    seen = set()
    out = []
    for x in actresses:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def normalize_item(item: dict) -> dict:
    work_id = item.get("content_id") or item.get("product_id") or ""
    title = item.get("title") or ""
    release_date = item.get("date") or ""
    official_url = item.get("affiliateURL") or item.get("URL") or ""
    hero_image = pick_best_image(item)

    tags = extract_genres(item)          # ジャンル（タグ）
    actresses = extract_actresses(item)  # 女優

    return {
        "id": work_id,
        "title": title,
        "description": title,
        "release_date": release_date,
        "tags": tags,
        "actresses": actresses,
        "official_url": official_url,
        "hero_image": hero_image,
    }


def merge_works(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    """
    idで重複排除して追記。
    並びは「新しいものが先」になるように incoming を前へ。
    """
    by_id: Dict[str, Dict[str, Any]] = {}
    # 既存をまず入れる
    for w in existing:
        wid = (w or {}).get("id")
        if wid:
            by_id[wid] = w

    added = 0
    # incoming を優先（同じidなら上書き）
    for w in incoming:
        wid = (w or {}).get("id")
        if not wid:
            continue
        if wid not in by_id:
            added += 1
        by_id[wid] = w

    # 日付でソート（date文字列なので基本そのままでも良いが、空対策して安定化）
    works_all = list(by_id.values())
    works_all.sort(key=lambda x: (x.get("release_date") or ""), reverse=True)

    # 上限カット
    if MAX_TOTAL_WORKS and len(works_all) > MAX_TOTAL_WORKS:
        works_all = works_all[:MAX_TOTAL_WORKS]

    return works_all, added


def main():
    data = load_existing()
    existing_works: List[Dict[str, Any]] = data.get("works", []) or []
    existing_ids = {w.get("id") for w in existing_works if isinstance(w, dict) and w.get("id")}
    print(f"existing works: {len(existing_works)}")

    all_new: List[Dict[str, Any]] = []

    # PAGES分、offsetを回して取得
    for page in range(PAGES):
        offset = 1 + page * HITS
        items = fetch_items(hits=HITS, offset=offset, sort=SORT)

        if not items:
            print("no items. stop.")
            break

        normalized = [normalize_item(it) for it in items if it]
        # 既にあるidを極力スキップ（API負荷は変わらないが、保存データは増分だけ）
        fresh = [w for w in normalized if w.get("id") and w["id"] not in existing_ids]

        print(f"page {page+1}/{PAGES}: fetched={len(normalized)} new={len(fresh)}")
        all_new.extend(fresh)

        # 新着が0なら、これ以上回しても古いだけなので止める（新着追記運用向け）
        if len(fresh) == 0:
            print("no new items on this page. stop early.")
            break

        time.sleep(SLEEP_SEC)

    merged, added = merge_works(existing_works, all_new)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "site_name": data.get("site_name") or SITE_NAME,
        "works": merged,
    }
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"saved: {OUT_FILE}")
    print(f"added: {added}")
    print(f"total works: {len(merged)}")

    # 先頭3件の女優確認
    for w in merged[:3]:
        print("----")
        print("id:", w.get("id"))
        print("title:", (w.get("title") or "")[:60])
        print("actresses:", w.get("actresses") or [])


if __name__ == "__main__":
    main()
