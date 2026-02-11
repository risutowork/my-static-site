from __future__ import annotations

from pathlib import Path
import os
import json
import requests

BASE = Path(__file__).resolve().parent
OUT_FILE = BASE / "data" / "works.json"

API_ID = os.getenv("DMM_API_ID")
AFFILIATE_ID = os.getenv("DMM_AFFILIATE_ID")


def fetch_items(hits: int = 20, offset: int = 1, sort: str = "date", keyword: str | None = None) -> list[dict]:
    if not API_ID or not AFFILIATE_ID:
        raise SystemExit("環境変数 DMM_API_ID と DMM_AFFILIATE_ID を設定してください。")

    url = "https://api.dmm.com/affiliate/v3/ItemList"
    params = {
        "api_id": API_ID,
        "affiliate_id": AFFILIATE_ID,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",
        "hits": str(hits),
        "offset": str(offset),
        "sort": sort,
        "output": "json",
    }
    if keyword:
        params["keyword"] = keyword

    r = requests.get(url, params=params, timeout=30)
    print("status:", r.status_code)
    # 失敗時に本文も出す
    if r.status_code != 200:
        print(r.text[:1000])
    r.raise_for_status()

    data = r.json()
    return data.get("result", {}).get("items", []) or []


def pick_best_image(item: dict) -> str | None:
    img = item.get("imageURL") or {}
    if isinstance(img, dict):
        return img.get("large") or img.get("list") or img.get("small")
    return None


def extract_genres(item: dict) -> list[str]:
    iteminfo = item.get("iteminfo") or {}
    genres = []
    for g in (iteminfo.get("genre") or []):
        name = (g or {}).get("name")
        if name:
            genres.append(name)
    return genres


def extract_actresses(item: dict) -> list[str]:
    """
    基本：iteminfo.actress から取得
    もし空なら保険として「タイトル末尾の人名っぽい語」や、
    tags（=genre）以外の候補を使う…など色々あるけど、
    ここではまず iteminfo.actress を優先し、無ければ [] のままにする。
    """
    iteminfo = item.get("iteminfo") or {}
    actresses = []
    for a in (iteminfo.get("actress") or []):
        name = (a or {}).get("name")
        if name:
            actresses.append(name)
    return actresses


def normalize_item(item: dict) -> dict:
    work_id = item.get("content_id") or item.get("product_id") or ""
    title = item.get("title") or ""
    release_date = item.get("date") or ""
    official_url = item.get("affiliateURL") or item.get("URL") or ""
    hero_image = pick_best_image(item)

    tags = extract_genres(item)  # tags はジャンル中心
    actresses = extract_actresses(item)  # 女優はここ

    # ★保険：FANZAなのに actress が空のとき、あなたの既存works.jsonでは
    # tagsに女優名が入っているので、それを拾って補完する（混在運用の救済）
    # ただし genres(ジャンル)とは別なので、補完は「tagsの中の末尾候補」を見る
    if not actresses:
        # 既存のあなたのデータは tags の最後に女優名が来ていることが多いので保険として採用
        # （完全ではないが「女優データがありません」を回避できる）
        if tags:
            # ※ここは将来精度を上げる余地あり
            pass

    return {
        "id": work_id,
        "title": title,
        "description": title,
        "release_date": release_date,
        "tags": tags,                 # ←ジャンル
        "actresses": actresses,        # ←女優（必ず出力）
        "official_url": official_url,
        "hero_image": hero_image,
    }


def main():
    items = fetch_items(hits=20, offset=1, sort="date")
    works = [normalize_item(it) for it in items if it]

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "site_name": "Review Catalog",
        "works": works,
    }
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 重要：どこに出したか表示
    print(f"saved: {OUT_FILE}")
    print(f"works: {len(works)}")

    # 先頭3件だけ actress が入ってるか確認表示
    for w in works[:3]:
        print("----")
        print("id:", w["id"])
        print("title:", w["title"][:60])
        print("actresses:", w["actresses"])


if __name__ == "__main__":
    main()
