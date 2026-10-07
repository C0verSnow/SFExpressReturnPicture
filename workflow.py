"""One entry point for screenshot assets and remote verification."""
import argparse
import subprocess
import sys
from pathlib import Path

from address_to_html import ROOT, export_address
from full_page_to_html import export_page
from prepare_pages import prepare_pages
from split_screenshot import split_screenshot


def run_check(script):
    subprocess.run([sys.executable, str(ROOT / 'tests' / script)], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description='统一处理截图、离线网页和 Pages；验证只在远端 CI 运行。')
    parser.add_argument('action', choices=('site', 'offline', 'address', 'split', 'verify'))
    parser.add_argument('--config', type=Path, default=ROOT / 'address.json')
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--image', type=Path, default=ROOT / '2026-10-06 11.08.30.jpg')
    parser.add_argument('--top', type=int)
    parser.add_argument('--bottom', type=int)
    args = parser.parse_args()
    defaults = {'site': 'pages-site', 'offline': 'offline-return-page',
                'address': 'offline-address', 'split': 'output'}
    try:
        if args.action == 'verify':
            if args.output_dir or args.top is not None or args.bottom is not None:
                raise ValueError('verify 使用固定目录，请不要传输出目录或切图边界。')
            # Generate once, then exercise HTTP and offline flows on the same assets.
            prepare_pages(ROOT / 'pages-site', args.config)
            export_page(args.config, ROOT / 'offline-return-page')
            split_screenshot(args.image, ROOT / 'output')
            export_address(ROOT / 'tests/original-address.json', ROOT / 'offline-address')
            for script in ('browser_pages.py', 'browser_full_page.py', 'browser_address.py'):
                run_check(script)
        else:
            target = args.output_dir or ROOT / defaults[args.action]
            if args.action == 'site':
                print(prepare_pages(target, args.config))
            elif args.action == 'offline':
                print(export_page(args.config, target))
            elif args.action == 'address':
                print(export_address(args.config, target))
            else:
                print(split_screenshot(args.image, target, args.top, args.bottom))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'处理失败：{exc}\n')


if __name__ == '__main__':
    main()
