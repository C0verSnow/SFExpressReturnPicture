"""Recreate the supplied address panel as editable, offline HTML and SVG."""

import argparse
import base64
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_address(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("地址配置必须是 JSON 对象。")
    for key in ("merchant", "phone"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key} 必须是非空文字。")
    lines = data.get("lines")
    if (not isinstance(lines, list) or len(lines) != 3
            or any(not isinstance(line, str) or not line.strip() for line in lines)):
        raise ValueError("lines 必须是三行非空地址文字。")
    if any("\n" in value or "\r" in value for value in
           [data["merchant"], data["phone"], *lines]):
        raise ValueError("每个字段只写一行，请用 lines 分开三行地址。")
    return data


def export_address(config, output_dir):
    data = load_address(config)
    target = Path(output_dir)
    if target.exists():
        raise ValueError("输出目录已经存在，请换一个目录，避免覆盖。")
    font = base64.b64encode(
        (ROOT / "assets/fonts/NotoSansCJKsc-Regular.otf").read_bytes()
    ).decode("ascii")
    license_text = (ROOT / "assets/fonts/OFL.txt").read_text(encoding="utf-8")
    escaped = {key: html.escape(data[key]) for key in ("merchant", "phone")}
    lines = [html.escape(line) for line in data["lines"]]
    style = f"""@font-face {{font-family:Address;src:url(data:font/otf;base64,{font}) format('opentype');font-weight:400;}}
* {{box-sizing:border-box;}}
body {{margin:0;background:white;font-family:Address,sans-serif;}}
#panel {{position:relative;width:1182px;height:469px;background:white;overflow:hidden;}}
#card {{position:absolute;left:82px;top:0;width:1018px;height:469px;border-radius:16px;background:#f6f6f6;}}
.field, #copy {{position:absolute;margin:0;padding:0;border:0;font:400 48px/70px Address,sans-serif;white-space:pre;letter-spacing:-.5px;}}
.field {{outline:none;}}
.field:focus {{outline:1px dashed #3589d6;}}
#label {{left:132px;top:72px;color:#191919;}}
#merchant {{left:368px;top:72px;color:#191919;}}
#phone {{left:570px;top:72px;color:#191919;}}
#copy {{left:954px;top:72px;color:#3589d6;background:transparent;cursor:pointer;}}
.address {{left:132px;color:#5d5d5d;}}
#line0 {{top:166px;}} #line1 {{top:242px;}} #line2 {{top:318px;}}
#tools {{padding:16px;font:16px/1.6 sans-serif;}}
#tools button {{margin-right:12px;}}
@media print {{#tools {{display:none;}} .field:focus {{outline:none;}}}}
"""
    fields = f"""<div id="card"></div>
<div id="label" class="field">商家地址：</div>
<div id="merchant" class="field" contenteditable="plaintext-only" role="textbox" aria-label="商家">{escaped['merchant']}</div>
<div id="phone" class="field" contenteditable="plaintext-only" role="textbox" aria-label="电话">{escaped['phone']}</div>
<button id="copy" type="button" aria-label="复制商家地址">复制</button>
""" + "\n".join(
        f'<div id="line{i}" class="field address" contenteditable="plaintext-only" role="textbox" aria-label="地址第{i+1}行">{line}</div>'
        for i, line in enumerate(lines)
    )
    script = (ROOT / "templates/address.js").read_text(encoding="utf-8")
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=1182">
<title>商家地址 · 离线编辑</title><style>{style}</style></head>
<body><main id="panel" aria-label="商家地址区块">{fields}</main>
<aside id="tools">点击文字即可修改；画布按原图 1182 × 469 像素显示。
<button id="save" type="button">保存修改后的网页</button>
<button id="save-json" type="button">导出地址配置</button>
<span id="status" role="status"></span></aside>
<details id="license"><summary>字体许可</summary><pre>{html.escape(license_text)}</pre></details>
<script>{script}</script></body></html>
"""
    svg_text = [
        (132, 128, "#191919", "商家地址："),
        (368, 128, "#191919", data["merchant"]),
        (570, 128, "#191919", data["phone"]),
        (954, 128, "#3589d6", "复制"),
        *[(132, 222 + i * 76, "#5d5d5d", line)
          for i, line in enumerate(data["lines"])],
    ]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1182" height="469" viewBox="0 0 1182 469">
<metadata>{html.escape(license_text)}</metadata>
<style>@font-face {{font-family:Address;src:url(data:font/otf;base64,{font}) format('opentype');}}
text {{font-family:Address,sans-serif;font-size:48px;letter-spacing:-.5px;white-space:pre;}}</style>
<rect width="1182" height="469" fill="white"/>
<rect x="82" width="1018" height="469" rx="16" fill="#f6f6f6"/>
''' + "\n".join(
        f'<text x="{x}" y="{y}" fill="{color}" xml:space="preserve">{html.escape(text)}</text>'
        for x, y, color, text in svg_text
    ) + "\n</svg>\n"
    target.mkdir(parents=True)
    (target / "address.html").write_text(page, encoding="utf-8")
    (target / "address.svg").write_text(svg, encoding="utf-8")
    (target / "address.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copyfile(ROOT / "assets/fonts/OFL.txt", target / "OFL.txt")
    return target / "address.html", target / "address.svg"


def main():
    parser = argparse.ArgumentParser(description="把样例商家地址复刻为可编辑的离线 HTML 和 SVG。")
    parser.add_argument("--config", type=Path, default=ROOT / "address.json")
    parser.add_argument("--output-dir", type=Path, default=Path("offline-address"))
    args = parser.parse_args()
    try:
        paths = export_address(args.config, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"生成失败：{exc}\n")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
