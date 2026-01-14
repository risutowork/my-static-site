from pathlib import Path
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape

# src/ が基準
ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = ROOT / "templates"
DATA_PATH = ROOT / "data" / "page.json"
OUT_PATH = ROOT.parent / "docs" / "index.html"

def main():
    # 1) データ読み込み
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # 2) Jinja2環境（templatesフォルダを見る）
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # 3) テンプレ読み込み → レンダリング
    template = env.get_template("page.html")
    html = template.render(**data)

    # 4) 書き出し
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")

    print(f"OK: {OUT_PATH}")

if __name__ == "__main__":
    main()
