"""Generate the ready-to-upload Pages directory on remote CI only."""
import argparse
from pathlib import Path

from address_to_html import ROOT
from full_page_to_html import export_page


def prepare_pages(output_dir, config=ROOT / 'address.json'):
    target = Path(output_dir)
    page = export_page(config, target)
    page.rename(target / 'index.html')
    # Explicit 404 disables Pages' implicit SPA fallback for unknown paths.
    (target / '404.html').write_text(
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<title>页面不存在</title><h1>页面不存在</h1><a href="/">返回退货截图编辑页</a></html>\n',
        encoding='utf-8')
    (target / '_redirects').write_text('/return-page.html / 302\n', encoding='utf-8')
    for path in target.iterdir():
        if path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError(f'{path.name} 超过 Cloudflare Pages 的单文件 25 MiB 限制。')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='在远端生成 Cloudflare Pages 部署目录。')
    parser.add_argument('--output-dir', type=Path, default=Path('pages-site'))
    args = parser.parse_args()
    print(prepare_pages(args.output_dir))
