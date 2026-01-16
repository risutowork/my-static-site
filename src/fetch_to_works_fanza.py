import os, json
import requests
from pathlib import Path

API_ID = os.getenv("DMM_API_ID")
AFF = os.getenv("DMM_AFFILIATE_ID")

OUT = Path(__file__).resolve().parent / "data" / "works.json"

def pick_hero_image(item: dict) -> str:
    img = item.get("imageURL")
    if isinstance(img, dict):
        return img.get("large") or img.get("list") or img.get("small") or ""
    return ""

def extract_tags(item: dict) -> list[str]:
    tags = []
    info = item.get("iteminfo") or {}

    for g in (info.get("genre") or []):
        name = g.get("name")
        if name:
            tags.append(name)

    for a in (info.get("actress") or []):
        name = a.get("name")
        if name:
            tags.append(name)

    return tags[:12]

def main():
    if not API_ID or not AFF:
        raise SystemExit("環境変数 DMM_API_ID / DMM_AFFILIATE_ID を設定してください")

    url = "https://api.dmm.com/affiliate/v3/ItemList"
    params = {
        "api_id": API_ID,
        "affiliate_id": AFF,
        "site": "FANZA",
        "service": "digital",
        "floor": "videoa",   # 素人: videoc / アニメ: anime に変更OK
        "hits": 20,
        "offset": 1,
        "sort": "date",
        "output": "json",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data.get("result", {}).get("items", [])

    works = []
    for it in items:
        work_id = it.get("content_id") or it.get("product_id") or ""
        if not work_id:
            continue

        works.append({
            "id": work_id,
            "title": it.get("title", ""),
            "description": it.get("title", ""),
            "release_date": it.get("date", ""),
            "tags": extract_tags(it),
            "official_url": it.get("affiliateURL") or it.get("URL") or "",
            "hero_image": pick_hero_image(it),
        })

    payload = {"site_name": "Review Catalog", "works": works}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK:", OUT, "works:", len(works))
    if works:
        print("sample hero_image:", works[0].get("hero_image"))

if __name__ == "__main__":
    main()
