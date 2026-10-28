# issue #11 改动清单与基线

起点为 `origin/main` 的 `0db6de6`，执行分支为 `feature/issue-11-engineering-address`。旧工作区干净；旧功能分支独有的提交保留，没有覆盖。

## 地址修复顺序

先提交回归用例，在 GitHub Actions 复现新层级规则与旧实现的差异，再抽离纯逻辑。Howard 用例保留原地址，手机号使用脱敏测试值。依次检查三个可能原因：字符串去重把直辖市的两个层级合成一个；详细地址前缀清理过宽；三行排版对完整地址产生删减。以完整地址断言、歧义报错和三行拼接断言区分原因。

## 文件迁移

| 原位置 | 新位置或处理 |
| --- | --- |
| `workflow.py` 业务 | `src/sf_return/cli.py`，根文件保留 CLI 入口 |
| `address_to_html.py` 业务 | `src/sf_return/render/address_panel.py`，原入口保留 |
| `full_page_to_html.py` 业务 | `src/sf_return/render/full_page.py`，原入口保留 |
| `prepare_pages.py` 业务 | `src/sf_return/render/pages.py`，原入口保留 |
| `split_screenshot.py` 业务 | `src/sf_return/images/split.py`，原入口保留 |
| `templates/` | `src/sf_return/render/templates/` |
| 模板中的地址逻辑 | `src/sf_return/address/contact.js`，浏览器与纯逻辑测试共用 |
| `assets/regions/` | `src/sf_return/address/data/`，原数据和许可原样保留 |
| 各处拼接资源路径 | `src/sf_return/paths.py` 统一路径 |

字体仍在 `assets/fonts/`，源截图和默认 `address.json` 仍在根目录；测试、文档和 `pages/` 保持原职责。不增加前端构建工具或运行时依赖，不改照片绘制布局。

## CLI、测试与发布基线

`site` 生成完整 Pages 目录；`offline` 生成独立离线整页；`address` 生成旧地址区 HTML/SVG；`split` 切图；`verify` 在远端一次生成资源后运行 HTTP、离线、剪贴板、主题和像素检查。保留原参数、默认目录与防覆盖规则，详见开发说明。

原 CI 包括 Python 3.10/3.13 单元测试及切图、Chromium 的 `python workflow.py verify`，以及 `pages/` 与远端 `pages-site/` 逐文件比较。本次添加直接检查纯地址模块的 Node job，并继续保留全部浏览器检查。

提交的发布目录仍包含九个文件：`index.html`、`full-page.js`、`address-dialog.svg`、`NotoSansCJKsc-Regular.otf`、`OFL.txt`、`regions-LICENSE.txt`、`address.json`、`404.html`、`_redirects`。HTML 内嵌全部运行资源，支持离线；JS 发布文件组合地址模块和页面交互。不得删除发布所需字体或许可。

本地只阅读、编辑、做静态语法和差异检查；不生成网页、不运行项目测试、不构建或编译。全部运行验证与发布资源生成走现有 GitHub Actions。PR 未经人工 Review 批准不合并，issue 保持打开；没有真实部署时明确记录未部署。
