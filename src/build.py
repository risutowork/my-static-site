from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TEMPLATES = SRC / "templates"
DATA_DIR = SRC / "data"
OUT = ROOT / "docs"

WORKS_JSON = DATA_DIR / "works.json"

TPL_INDEX = "index.html"
TPL_PAGE = "page.html"
TPL_LIST = "list_works.html"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSONが見つかりません: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def safe_template(env: Environment, name: str, fallback: str | None = None):
    try:
        return env.get_template(name)
    except Exception:
        if fallback:
            return env.get_template(fallback)
        raise


def slugify_simple(s: str) -> str:
    s = (s or "").strip()
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        s = s.replace(ch, "_")
    s = s.replace(" ", "_")
    return s or "unknown"


def build_indexes_from_works(works: List[Dict[str, Any]]):
    actresses: Dict[str, List[Dict[str, Any]]] = {}
    genres: Dict[str, List[Dict[str, Any]]] = {}

    for w in works:
        for a in (w.get("actresses") or []):
            actresses.setdefault(a, []).append(w)

        for g in (w.get("tags") or []):
            genres.setdefault(g, []).append(w)

    return actresses, sorted(actresses.keys()), genres, sorted(genres.keys())


def main():
    data = load_json(WORKS_JSON)
    site_name = data.get("site_name", "Catalog")
    works: List[Dict[str, Any]] = data.get("works", [])

    ensure_dir(OUT / "works")
    ensure_dir(OUT / "actresses")
    ensure_dir(OUT / "genres")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    tpl_index = safe_template(env, TPL_INDEX)
    tpl_page = safe_template(env, TPL_PAGE)
    tpl_list = safe_template(env, TPL_LIST, fallback=TPL_INDEX)

    # =============================
    # CSS相対パス
    # =============================
    CSS_ROOT = "assets/style.css"
    CSS_1DOWN = "../assets/style.css"
    CSS_2DOWN = "../../assets/style.css"

    # =============================
    # 1) トップページ
    # =============================
    write_text(
        OUT / "index.html",
        tpl_index.render(
            site_name=site_name,
            works=works,
            css_path=CSS_ROOT,
            home_href="./",
            actresses_href="actresses/",
            genres_href="genres/",
            works_prefix="works/",
        ),
    )

    # =============================
    # 2) 作品個別ページ
    # =============================
    for w in works:
        wid = w.get("id")
        if not wid:
            continue

        write_text(
            OUT / "works" / str(wid) / "index.html",
            tpl_page.render(
                site_name=site_name,
                w=w,
                css_path=CSS_2DOWN,
                home_href="../../",
                actresses_href="../../actresses/",
                genres_href="../../genres/",
                works_prefix="../../works/",
            ),
        )

    actresses, actresses_keys, genres, genres_keys = build_indexes_from_works(works)

    # =============================
    # 3) 女優一覧ページ
    # =============================
    write_text(
        OUT / "actresses" / "index.html",
        tpl_list.render(
            site_name=site_name,
            page_title="女優一覧",
            page_description="女優別の一覧ページです。",
            items=[{"name": a, "href": f"./{slugify_simple(a)}/"} for a in actresses_keys],
            css_path=CSS_1DOWN,
            home_href="../",
            actresses_href="./",
            genres_href="../genres/",
            works_prefix="../works/",
        ),
    )

    # =============================
    # 4) 女優個別ページ
    # =============================
    for a in actresses_keys:
        write_text(
            OUT / "actresses" / slugify_simple(a) / "index.html",
            tpl_index.render(
                site_name=site_name,
                works=actresses[a],
                css_path=CSS_2DOWN,
                home_href="../../",
                actresses_href="../",
                genres_href="../../genres/",
                works_prefix="../../works/",
            ),
        )

    # =============================
    # 5) ジャンル一覧ページ
    # =============================
    write_text(
        OUT / "genres" / "index.html",
        tpl_list.render(
            site_name=site_name,
            page_title="ジャンル一覧",
            page_description="タグ（ジャンル）別の一覧ページです。",
            items=[{"name": g, "href": f"./{slugify_simple(g)}/"} for g in genres_keys],
            css_path=CSS_1DOWN,
            home_href="../",
            actresses_href="../actresses/",
            genres_href="./",
            works_prefix="../works/",
        ),
    )

    # =============================
    # 6) ジャンル個別ページ
    # =============================
    for g in genres_keys:
        write_text(
            OUT / "genres" / slugify_simple(g) / "index.html",
            tpl_index.render(
                site_name=site_name,
                works=genres[g],
                css_path=CSS_2DOWN,
                home_href="../../",
                actresses_href="../../actresses/",
                genres_href="../",
                works_prefix="../../works/",
            ),
        )

    print("生成完了：docs/ に出力しました")


if __name__ == "__main__":
    main()
