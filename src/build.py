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

STYLE_CSS = """\
/* （ここはあなたの共通CSSそのまま） */
:root{
  --bg:#0b1220;
  --panel:#0f172a;
  --card:#0b1220;
  --paper:#0b1220;
  --text:#e5e7eb;
  --muted:#94a3b8;
  --line:rgba(255,255,255,.08);
  --accent:#60a5fa;
  --accent2:#a78bfa;
  --radius:16px;
  --shadow:0 14px 40px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{
  margin:0;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans JP",sans-serif;
  background:radial-gradient(1200px 500px at 30% 0%, #0b2a55 0%, transparent 60%),
             radial-gradient(1000px 500px at 80% 10%, #2a174a 0%, transparent 55%),
             var(--bg);
  color:var(--text);
}
a{color:inherit;text-decoration:none}
.container{max-width:1100px;margin:0 auto;padding:0 16px}
.header{
  position:sticky;top:0;z-index:10;
  background:linear-gradient(to bottom, rgba(15,23,42,.92), rgba(15,23,42,.6));
  backdrop-filter: blur(10px);
  border-bottom:1px solid var(--line);
}
.header-inner{display:flex;align-items:center;justify-content:space-between;padding:14px 0;gap:12px}
.brand{font-weight:800;letter-spacing:.2px}
.nav{display:flex;gap:10px;flex-wrap:wrap}
.nav a{
  padding:8px 10px;border-radius:999px;
  border:1px solid var(--line);
  color:var(--text);
  font-weight:700;font-size:13px;
  background:rgba(255,255,255,.04);
}
.nav a:hover{border-color:rgba(96,165,250,.5)}
.hero{padding:18px 0 12px}
.hero h1{margin:10px 0 6px;font-size:28px}
.hero p{margin:0;color:var(--muted);font-size:14px}
.grid{
  display:grid;
  grid-template-columns:repeat(3, minmax(0, 1fr));
  gap:14px;
  margin:14px 0 30px;
}
@media (max-width: 980px){ .grid{grid-template-columns:repeat(2,1fr)} }
@media (max-width: 640px){ .grid{grid-template-columns:1fr} }
.card{
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));
  border:1px solid var(--line);
  border-radius:var(--radius);
  overflow:hidden;
  box-shadow:var(--shadow);
}
.thumb{
  width:100%;
  aspect-ratio:16/9;
  object-fit:cover;
  display:block;
  background:#0a0f1c;
}
.pad{padding:12px}
.title{font-size:15px;font-weight:800;line-height:1.3;margin:0 0 6px}
.meta{color:var(--muted);font-size:12px;margin-bottom:8px}
.tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{
  font-size:11px;
  padding:5px 9px;
  border-radius:999px;
  border:1px solid var(--line);
  background:rgba(167,139,250,.10);
  color:#ddd6fe;
  white-space:nowrap;
}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.btn{
  display:inline-flex;align-items:center;justify-content:center;
  padding:10px 12px;border-radius:12px;
  border:1px solid rgba(96,165,250,.4);
  background:rgba(96,165,250,.15);
  color:#dbeafe;
  font-weight:800;font-size:13px;
}
.btn:hover{background:rgba(96,165,250,.25)}
.btn.secondary{
  border:1px solid var(--line);
  background:rgba(255,255,255,.04);
  color:var(--text);
}
.footer{color:var(--muted);text-align:center;padding:26px 0 34px;border-top:1px solid var(--line)}
.list{
  display:grid;gap:10px;margin:14px 0 30px;
}
.list .item{
  background:rgba(255,255,255,.04);
  border:1px solid var(--line);
  border-radius:14px;
  padding:14px;
}
.list .item a{font-weight:900}
.small{color:var(--muted);font-size:13px;margin-top:6px}
"""

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

  ensure_dir(OUT / "assets")
  ensure_dir(OUT / "works")
  ensure_dir(OUT / "actresses")
  ensure_dir(OUT / "genres")

  # ✅ 共通CSSを生成
  write_text(OUT / "assets" / "style.css", STYLE_CSS)

  env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
  )

  tpl_index = safe_template(env, TPL_INDEX)
  tpl_page = safe_template(env, TPL_PAGE)
  tpl_list = safe_template(env, TPL_LIST, fallback=TPL_INDEX)

  # --- CSSパス（相対パス）を場所ごとに指定 ---
  CSS_ROOT = "assets/style.css"          # docs/index.html から見たCSS
  CSS_1DOWN = "../assets/style.css"      # docs/actresses/index.html 等
  CSS_2DOWN = "../../assets/style.css"   # docs/works/<id>/index.html 等

  # 1) トップ
  write_text(
    OUT / "index.html",
    tpl_index.render(site_name=site_name, works=works, css_path=CSS_ROOT),
  )

  # 2) 作品個別
  for w in works:
    wid = w.get("id")
    if not wid:
      continue
    write_text(
      OUT / "works" / str(wid) / "index.html",
      tpl_page.render(site_name=site_name, w=w, css_path=CSS_2DOWN),
    )

  actresses, actresses_keys, genres, genres_keys = build_indexes_from_works(works)

  # 3) 女優一覧
  write_text(
    OUT / "actresses" / "index.html",
    tpl_list.render(
      site_name=site_name,
      page_title="女優一覧",
      page_description="女優別の一覧ページです。",
      items=[{"name": a, "href": f"./{slugify_simple(a)}/"} for a in actresses_keys],
      css_path=CSS_1DOWN,
    ),
  )

  # 4) 女優別（中身は作品一覧テンプレを再利用）
  for a in actresses_keys:
    write_text(
      OUT / "actresses" / slugify_simple(a) / "index.html",
      tpl_index.render(site_name=site_name, works=actresses[a], css_path=CSS_2DOWN),
    )

  # 5) ジャンル一覧
  write_text(
    OUT / "genres" / "index.html",
    tpl_list.render(
      site_name=site_name,
      page_title="ジャンル一覧",
      page_description="タグ（ジャンル）別の一覧ページです。",
      items=[{"name": g, "href": f"./{slugify_simple(g)}/"} for g in genres_keys],
      css_path=CSS_1DOWN,
    ),
  )

  # 6) ジャンル別
  for g in genres_keys:
    write_text(
      OUT / "genres" / slugify_simple(g) / "index.html",
      tpl_index.render(site_name=site_name, works=genres[g], css_path=CSS_2DOWN),
    )

  print("生成完了：docs/ に出力しました")

if __name__ == "__main__":
  main()
