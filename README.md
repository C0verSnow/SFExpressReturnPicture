# SFExpressReturnPicture

## 部署到 Cloudflare Pages（C0verSnow 仓库 issue #1）

`pages/` 是可直接发布的完整静态网站目录。首页 `index.html` 就是整张退货截图编辑页，点击灰色地址区修改名字、电话和地址，确认后下载 PNG。它包含 HTML、JS、SVG、完整中文字体、字体许可和初始地址配置，不需要服务器接口。

在 Cloudflare 的 **Workers & Pages → Create application → Pages → Import an existing Git repository** 选择本仓库。先把本次 PR 合并到 `main`，然后使用以下设置：

| 设置 | 填写内容 |
| --- | --- |
| Framework preset | None |
| Production branch | `main` |
| Root directory | 留空（仓库根目录） |
| Build command | `exit 0` |
| Build output directory | `pages` |

保存并部署后，直接打开 Cloudflare 给出的 `https://项目名.pages.dev/`。首页无需补文件名；旧的 `/return-page.html` 路径通过 `_redirects` 回到首页。`404.html` 让不存在的路径显示错误页，避免被当成单页应用首页。详细设置见 [Cloudflare 静态 HTML 指南](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/)。也可以把 `pages/` 的全部内容直接上传到 Pages；上传时确保 `index.html` 在发布目录的第一层。

HTML 已内嵌底图、字体和交互，可以单独下载使用；旁边的 JS、SVG、字体及许可一并保留，方便查看和维护。单个发布文件必须不超过 [Pages 的 25 MiB 限制](https://developers.cloudflare.com/pages/platform/limits/)，远端生成时会检查。

修改截图、模板或初始配置后，部署文件也需要更新：GitHub Actions 使用 `python workflow.py verify` 一次生成 Pages 和离线资源，再统一检查。下载 `cloudflare-pages-site` 附件，将附件内容替换到 `pages/` 并提交。不要在本地运行生成或验证。CI 会重新生成并逐文件比较，避免发布旧版本。首次更新可先移走旧的 `pages/`，取回远端新附件后再提交；最终 PR 必须包含新目录并通过一致性检查。`browser-previews` 附件包含四类屏幕预览、弹窗和实际下载的 PNG。
Cloudflare 账号的连接和首次部署需要在你的 Cloudflare 后台完成。CI 使用 HTTP 静态站验证发布目录，不代表已经发布到真实的 `pages.dev` 域名。部署成功后可打开根网址，修改一次地址，确认浏览器下载了完整照片。

把已经保存好的退货长截图，按商家地址的浅灰色区块切成 3 张 PNG：

1. `01_top.png`：灰色区上方。
2. `02_address.png`：灰色区本身（保留截图原宽度）。
3. `03_bottom.png`：灰色区下方。

三张图之间没有重叠，也不丢行；按顺序拼回后就是原截图。输入 JPEG 时，PNG 保存的是 JPEG 解码后的像素，不会恢复 JPEG 已丢失的细节。

## 使用方法

需要 Python 3.10 或更新版本。在允许运行脚本的环境安装依赖，然后运行：

```sh
python -m pip install -r requirements.txt
python workflow.py split --output-dir output
```

脚本会打印识别到的上下边界和三张图片路径。图片只在执行环境中处理，不上传截图；已有同名输出会报错，请换一个输出目录。

## 手动指定边界

自动识别针对示例截图中的浅灰色、较宽的地址区块，通过颜色判断，不做文字识别。其他页面中的灰色卡片也可能被识别；它不能保证灰色块一定是商家地址。识别失败、存在多个候选区块、或自动边界不符合预期时，用图片工具查看像素坐标，再指定：

```sh
python workflow.py split --image screenshot.png --top 1600 --bottom 2100 --output-dir result
```

以上坐标只是用法示例。坐标从图片顶部的第 0 行开始：`top` 是灰色区第一行，`bottom` 是灰色区结束后的第一行，必须满足 `0 < top < bottom < 图片高度`。上下边界必须同时填写。带 EXIF 方向信息的图片先转正，坐标以转正后的图片为准。

## 地址区转为可编辑离线网页（issue #3）

完成切图后，以 `output/02_address.png` 为对照，运行：

```sh
python workflow.py address --config address.json --output-dir offline-address
```

这个脚本只用 Python 标准库，生成 `address.html`、`address.svg`、`address.json` 和字体许可 `OFL.txt`。双击 HTML 即可离线打开，点击商家、电话、三行地址直接修改。点击“保存修改后的网页”下载包含当前文字的新 HTML，关闭页面前请保存；下次打开下载的 HTML 还可以继续编辑。“导出地址配置”保存 JSON，再把它传给脚本即可重新生成 HTML 和 SVG。“复制”复制当前的商家、电话和完整地址；浏览器不允许自动复制时，页面会提示手动复制。

HTML 和 SVG 都内嵌完整中文字体，无需联网、安装字体或启动服务器。SVG 是生成时的静态文字版本；网页修改后需要导出配置并重新生成才能更新 SVG。字体来源和许可见 [assets/fonts/README.md](assets/fonts/README.md)。字体未裁剪，所以生成文件较大（每个约 22 MB），能显示后续修改的中文。

这次复刻针对仓库提供的 **1182 × 469 像素** 地址图：保留画布大小、灰色卡片位置、圆角、文字位置和三行排版。它不是 OCR 工具，不会自动读取任意 `02_address.png`；内容来自 `address.json`。换截图时需人工修改配置及脚本中的布局坐标。为保持原图尺寸，窄屏使用横向滚动，不自动缩放；很长的文字可能重叠或超出画布，请手工按原来的三行分段。

原截图没有提供原始字体，使用开源 Noto Sans CJK SC 复刻，字形和抗锯齿会有差别，不能保证逐像素相同。远端会产出上下对照图（上：原图，下：网页）、差异图和误差数据供查看。

## 远端验证

本仓库不做本地构建、编译验证或本地测试运行。GitHub Actions 在 push、PR 和手动触发时，使用 Python 3.10、3.13 运行测试，并用仓库示例图产出 3 张 PNG。工作流页面的 `sample-pngs-python-*` 附件可下载查看。

测试覆盖自动识别、多个灰色区块、没有灰色区块、手动边界、无效输入、避免覆盖，以及把三张输出拼回后逐像素比较。真实截图测试还会检查地址区块的位置，避免只验证“能输出文件”。

新增远端 Chromium 检查：断网通过 `file://` 打开网页和 SVG、嵌入字体加载、画布尺寸、五个可编辑字段、修改文字、导出 JSON、保存网页后重新打开并继续编辑、没有外部请求或脚本错误。`browser-previews` 附件包含可直接打开的网页、SVG、原图对照和差异图。截图误差检查只作为明显偏移的拦截，不能证明字形逐像素相同。

## 收件信息编辑与四类屏幕适配（C0verSnow issue #3）

统一入口为 `workflow.py`，原来的脚本作为内部模块和兼容入口保留。以下命令在允许执行的远端环境使用，本仓库不运行本地生成或验证：

```sh
python workflow.py site       # 生成 pages-site/index.html，供 Pages 发布
python workflow.py offline    # 生成 offline-return-page/return-page.html
python workflow.py split      # 切出三张 PNG 到 output/
python workflow.py address    # 生成单独的地址区网页到 offline-address/
python workflow.py verify     # 远端生成资源并检查在线、离线和四类屏幕
```

支持 `--config 配置.json` 和 `--output-dir 新目录`；切图支持 `--image`、`--top` 和 `--bottom`。请在仓库根目录使用这些命令，已有生成目录会拒绝覆盖。`verify` 使用固定目录，供 GitHub Actions 使用。工作流只有 Python 3.10、3.13 单元检查和一次浏览器检查，浏览器依赖只安装一次。

默认收件信息是「张三」「18888888888」，地址按三行显示：

```text
广东省
深圳市
南山区人才公园
```

打开 Pages 首页或双击离线 HTML，点击灰色收件区内的「修改信息」按钮，填写名字、电话和三行地址。每行地址都必须填写，过长文字会提示缩短。确认后更新预览，并自动下载 `return-page-edited.png`。取消或 Esc 放弃本次输入。底部仅保留「保存修改后的照片」按钮，可以再次下载当前照片；提示为「点击按钮即可修改信息，注意地址要写满三行」。网页保存和配置导出按钮、页面上的字体许可均已移除，字体许可证仍保存在 `OFL.txt` 和内嵌字体元数据中。

修改只在当前页面内保留，刷新或重开会回到配置中的默认信息。若需更改默认信息，修改 `address.json` 后通过远端生成新页面。照片下载到浏览器默认目录，不能覆盖原照片。原截图上的业务按钮仅是图片。

先参考设备的移动标记和触摸特征，再按当前窗口宽度分类，缩放窗口会重新判断：

| 平台 | 推荐设计画布 | 页面适配 |
| --- | --- | --- |
| Desktop | 1920 × 1080 | 大窗口，居中预览 |
| Laptop | 1440 × 900 | 紧凑的居中预览 |
| Tablet | 768 × 1024 | 触摸设备或中等宽度，放大预览 |
| Mobile | 390 × 844 | 窄窗口，预览占满可用宽度 |

平台识别属于浏览器特征推断；宽度小于 600 使用手机布局，小于 1024 使用平板布局，普通电脑窗口小于 1600 使用笔记本布局。触摸或移动设备在宽度小于 1400 时优先平板布局。画布是布局参考，不会强制修改屏幕或照片尺寸。预览等比例缩放，无横向滚动；页面可纵向滚动，保存按钮随页面底部显示，弹窗适配屏幕与安全区域。

下载照片始终保持 **1182 × 2560**，只覆盖名字、电话和地址的原文字矩形。底部按钮和「修改信息」标记不会进入 PNG。原图转换为 sRGB；使用内嵌 Noto Sans CJK SC，原字体未知，新文字字形可能有差别。把信息恢复为原截图里的值时，对应区域恢复原像素。模板坐标只适用于仓库样例。

远端检查涵盖 HTTP 首页和资源、离线编辑和下载、四类推荐画布与窗口缩放、三行必填及文字长度、取消和键盘操作、照片编码失败后重试、各字段变化边界、原图恢复、预览画布与下载照片像素一致、不同设备像素比例下载一致及无外部请求。旧地址区网页继续独立检查，使用 `tests/original-address.json` 与原截图对照。
