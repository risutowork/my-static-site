from pathlib import Path
import json

# ここがフォルダの基準
ROOT = Path(__file__).resolve().parent  # src/
TEMPLATE_PATH = ROOT / "templates" / "page.html"
DATA_PATH = ROOT / "data" / "page.json"

# 出力先：リポジトリ直下の docs/index.html
OUT_PATH = ROOT.parent / "docs" / "index.html"


def render_template(template: str, data: dict) -> str:
    """
    超初心者向け：まずは簡易レンダラーでOK（Jinja2なし）
    - {{ key }} を data[key] で置換
    - {% for t in tags %} ... {% endfor %} の tags だけ対応
    """
    # 1) ループ（tags）部分だけ先に処理
    if "{% for t in tags %}" in template:
        start = template.index("{% for t in tags %}")
        end = template.index("{% endfor %}") + len("{% endfor %}")
        loop_block = template[start:end]

        inner_start = loop_block.index("%}") + 2
        inner_end = loop_block.index("{% endfor %}")
        inner = loop_block[inner_start:inner_end]

        tags_html = ""
        for t in data.get("tags", []):
            tags_html += inner.replace("{{ t }}", str(t))

        template = template.replace(loop_block, tags_html)

    # 2) {{ key }} の置換
    for k, v in data.items():
        template = template.replace("{{ " + k + " }}", str(v))

    return template


def main():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    html = render_template(template, data)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"OK: {OUT_PATH}")


if __name__ == "__main__":
    main()
