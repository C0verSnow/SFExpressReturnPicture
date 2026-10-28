# issue #11 远端验证记录

## 修复前

[578a488 回归运行](https://github.com/C0verSnow/SFExpressReturnPicture/actions/runs/40640724727) 首先加入新规则测试，没有先改实现。Node 19 组中 8 组失败，Howard 的 actual 少一份“北京市”，expected 为 `北京市北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院`；浏览器真实粘贴链路也复现。Python 3.10/3.13 的既有测试通过。

## 修复后功能

[4d70026 push](https://github.com/C0verSnow/SFExpressReturnPicture/actions/runs/40642027019) 与 [PR 运行](https://github.com/C0verSnow/SFExpressReturnPicture/actions/runs/40642033701) 的以下功能检查全部通过：

- 34 组直接调用浏览器同一纯模块的地址回归，覆盖 Howard 精确输出、京津沪渝、普通省份、补全、歧义、孤立区名/镇名学校和道路、明确重复字段、三行不截正文及括号提示。
- Python 3.10/3.13 单元测试、切图和源码迁移/旧入口检查。
- `python workflow.py verify`：HTTP 资源、离线整页和旧地址区、剪贴板、四类屏幕、键盘/取消/失败重试、初始图防闪现、主题和照片像素。
- 各设备使用同样的解析/编辑步骤、独立 Chromium 进程，下载 PNG 字节完全相同；每个平台固定字段、1182×2560 尺寸、下载与预览全部 RGBA 像素严格相等。原逐字段边界、重复保存和恢复原图检查全部保留。

这两轮 workflow 仅因提交的 `pages/` 仍是旧快照而总体失败，没有跳过或放宽发布比较。已从该轮 `cloudflare-pages-site` artifact 取回全部九个发布文件，ZIP SHA-256 为 `f5162448d0d1665a699454f6c17d2084f8ff8cc0e898492694bcf8907fc68483`。文件名集合核对完整，发布 JS 与纯模块加页面交互源码完全相同。发布提交 `c9b0787` 的 [push CI](https://github.com/C0verSnow/SFExpressReturnPicture/actions/runs/40642366025) 和 [PR CI](https://github.com/C0verSnow/SFExpressReturnPicture/actions/runs/40642371842) 均已全部通过，包含发布目录逐文件一致性。最后仅补本验收记录和任务清单，功能与发布文件不再变化；最新状态也在 [PR #12](https://github.com/C0verSnow/SFExpressReturnPicture/pull/12) 更新。

## 浏览器比较的处理

7c1fddf 的跨设备照片比较失败时，两边操作历史不同：一边经过大量解析、恢复和逐字段编辑，另一边只进行一次编辑。静态对比远端两张 1182×2560 图片，2467 个差异像素仅在电话矩形 `(575,1728)-(860,1765)`，姓名、地址及其他底图完全相同，与此前已记录的 Chromium 字体栅格缓存现象一致。测试改为相同行为历史及独立进程后严格比较通过；没有添加像素容差，也没有修改生产绘图样式或坐标。已查看远端解析弹窗，布局正常。

## 本地与交付边界

本地只做代码阅读、Python AST 静态语法、差异/文件校验，以及远端产物的静态图片比较；没有编译、构建、生成网页或运行项目测试。本机无 Node，JS 执行完全由远端 Node 22 和 Chromium 检查。

GitHub 上已检索并比较同类功能，来源与限制见 [本次调研](issue-11-research.md)，自行实现且没有复制外部解析器代码。执行过程记录在根 `tasklist.md`，每条本次记录带 Unix Timestamp。

PR 等人工 Review，issue #11 在合并验收前保持打开；未自动合并、未关闭 issue。Cloudflare 实际发布状态为 **未部署**；真实 iPhone/安卓系统权限没有做实体机验证，CI Chromium 不能替代这些检查。
