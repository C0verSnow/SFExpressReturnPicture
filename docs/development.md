# 开发与远端验证

本仓库只在远端 GitHub Actions 生成和验证资源。本地不构建、不编译、不跑项目测试或会生成网页的冒烟脚本；可以阅读代码、检查语法和差异。下列生成与测试命令供远端执行。

## 目录职责

```text
src/sf_return/
  cli.py                 五种工作流命令
  paths.py               仓库、模板、地区数据和源资源的路径
  address/
    contact.js           联系人提取、行政层级规范化、三行排版
    data/                固定版本地区数据、README 和原许可
  render/
    address_panel.py     旧地址区 HTML/SVG
    full_page.py         离线整张截图页面
    pages.py             Pages 首页、重定向和 404
    templates/           HTML 与页面交互 JS
  images/split.py         灰色区识别与无损切图
assets/fonts/             中文字体源文件和许可
address.json              默认收件信息
2026-10-06 11.08.30.jpg    模板源截图
tests/                    Python、Node 纯逻辑、Chromium 回归
docs/                     使用说明与研究
pages/                    已提交的完整静态发布快照
```

根目录 `workflow.py`、`address_to_html.py`、`full_page_to_html.py`、`prepare_pages.py`、`split_screenshot.py` 仅保留兼容启动与原函数导出。业务使用包内相对导入，不依赖当前工作目录来寻找模板、字体或地区数据；用户传入的相对输入输出路径仍相对于调用目录。没有新增 Python 包安装步骤或前端打包流程。

| 旧源码 | 现维护位置 |
| --- | --- |
| `workflow.py` | `src/sf_return/cli.py` |
| `address_to_html.py` | `src/sf_return/render/address_panel.py` |
| `full_page_to_html.py` | `src/sf_return/render/full_page.py` |
| `prepare_pages.py` | `src/sf_return/render/pages.py` |
| `split_screenshot.py` | `src/sf_return/images/split.py` |
| `templates/` | `src/sf_return/render/templates/` |
| 地址解析与排版函数 | `src/sf_return/address/contact.js` |
| `assets/regions/` | `src/sf_return/address/data/` |

## 命令与兼容性

Python 3.10+，运行依赖仍只有 `requirements.txt` 中的 Pillow；浏览器检查另装固定 Playwright，纯 JS 检查使用 Node 22 内置测试工具，不安装 npm 依赖。

| 命令 | 默认输出 | 行为与参数 |
| --- | --- | --- |
| `python workflow.py site` | `pages-site/` | 生成完整 Pages 目录；接受 `--config`、`--output-dir` |
| `python workflow.py offline` | `offline-return-page/` | 生成内嵌运行资源的 `return-page.html`；接受 `--config`、`--output-dir` |
| `python workflow.py address` | `offline-address/` | 旧地址区 HTML/SVG/JSON 与字体许可；接受 `--config`、`--output-dir` |
| `python workflow.py split` | `output/` | 默认仓库源图；接受 `--image`、`--output-dir`、成对的 `--top`/`--bottom` |
| `python workflow.py verify` | 固定验证目录 | 一次生成 site/offline/address/split 后运行浏览器回归；配置默认 `address.json`，源图默认仓库样例；拒绝自定义输出目录和切图边界 |

`--config` 默认仓库根 `address.json`，`--image` 默认仓库源图；参数仅供对应动作使用，保持旧入口行为。页面生成遇到已有目录报错；切图遇到已有同名 PNG 报错，避免覆盖。旧四个脚本的 `--help`、原参数和导出函数也保持兼容。

远端检查命令：`python -m unittest discover -s tests -v`、`node tests/address_core.cjs` 和 `python workflow.py verify`。`verify` 包含真实 HTTP、断网 file 页面、剪贴板异常回退、四种尺寸、深色模式、确认后下载、PNG 像素和旧地址区检查。纯逻辑测试直接调用页面使用的地址模块，断言完整规范化地址、幂等、缺失/歧义和三行拼接完整；照片字体的真实宽度由浏览器检查覆盖。

## 规则与人工核对

先识别合法省、市、区县关系，再生成完整三级地址，最后排成三行；直辖市省市同名也各留一份。Howard 输入 `北京 北京市 通州区 宋庄镇 北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院` 输出必须精确为 `北京市北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院`。普通省份示例 `广东 深圳 南山 科技园1号` 输出 `广东省深圳市南山区科技园1号`。

去重只处理能够确认的开头完整行政路径、有独立分隔边界的重复区县/镇街字段，以及跨完整重复路径的相同镇街，不能全局替换详细地址中的地名。连写的“宋庄镇宋庄镇中心小学”保留校名中的第二个镇名；不能仅凭前面省名重复就删校名中的区名。数据没有收录、缺少区县、同名区县歧义或省市冲突时提示补充或手动填写，不能随便取第一条。无法证明是行政重复的详细词保留供核对。区县简称只有明确独立成词时才采用，例如 `广东 深圳 南山 科技园1号`；`深圳市南山大道1号` 缺少可靠区县，不能猜成南山区。先尝试完整地址排版，只有配对括号附注在放不下时可逐条省略并告知；正文超长报错，原填写保留，解析不会直接下载照片。

## 发布资源与 CI

`pages/` 的九个文件必须随源码更新提交，包含完整字体、字体许可和地区许可。远端 `cloudflare-pages-site` artifact 对应同样九个文件；`full-page.js` 组合纯地址模块与页面交互，不额外增加网络请求。HTML 内嵌同一份脚本、底图、字体和地区数据，单独保存仍可离线。

其他产物（`pages-site/`、`offline-return-page/`、`offline-address/`、`sample-output/`、`output/`、`pages-check/`）不提交；CI artifact 交付切图、离线网页与浏览器证据。源字体、源截图、模板和固定地区数据要提交；凭据 `.env` 与缓存不提交。

操作顺序：同步 main 后建 feature 分支；先提交回归，再分阶段修复；push 后检查 Python 3.10/3.13、地址及浏览器 job；从通过功能检查的远端附件更新 `pages/`，保留许可和全部文件，重新 push 让逐文件一致性检查通过。不要先删发布资源来绕过比较。PR 应附最终运行与 artifact 链接，等人工 Review 后由维护者合并，合并发布验收前保持 issue 打开。

Cloudflare 仍发布根目录下的 `pages/`，构建命令 `exit 0`。GitHub CI 验证不等于真实部署；本次没有连接 Cloudflare 做发布，状态为“未部署”。回滚时应同时恢复源码和相应 `pages/`，无需迁移数据或秘密配置。
