# 一键粘贴调研与实现（issue #7）

2026-10-27 在 GitHub 检索 Clipboard API 的开源实现；以下数字为查询时的快照。仅借鉴设计，自行实现事件处理，不复制第三方代码、不添加运行时依赖。

| 项目 | 维护、许可与问题 | 实现与依赖 | 选择 |
| --- | --- | --- | --- |
| [VueUse useClipboard](https://github.com/vueuse/vueuse/blob/e32dff3abacaf6aa531dbbbd617fb21b697b7104/packages/core/useClipboard/index.ts) | 22398 stars，MIT，仓库 2026-10-27 有推送；该模块 2026-09-02 有提交。[#5535](https://github.com/vueuse/vueuse/issues/5535#issuecomment-5002004650) 有成员回复，[#5613](https://github.com/vueuse/vueuse/pull/5613) 由 antfu 合并处理，证明问题仍有响应。历史 [#1639](https://github.com/vueuse/vueuse/issues/1639) 提醒 API 不可用时不能假定成功。 | 检测 API、调用异步读取、捕获失败；依赖 Vue、共享工具、权限与事件封装。旧式读取回退是当前选择的文字，不能当作系统剪贴板。 | 借鉴能力检测和失败处理，不引入 Vue。为兼容 Safari，不照搬权限预查询与选择文字回退。 |
| [clipboard.js](https://github.com/zenorocha/clipboard.js) | 34095 stars，MIT，2026-02-12 有维护提交；[#875](https://github.com/zenorocha/clipboard.js/issues/875) 提出 execCommand 弃用问题，但评论仅查到 stale 机器人，没有核实到人工响应。 | 事件委托、选择文本、复制/剪切；依赖 good-listener、select、tiny-emitter。 | 没有设备剪贴板读取能力，且人工响应不足以确认，不保留为采用候选。 |
| [clipboard-polyfill](https://github.com/lgarron/clipboard-polyfill) | 925 stars，最后推送 2025-11；本次仓库 API 未识别许可证。 | 兼容多种旧剪贴板接口；README 说明多数现代浏览器不再需要该库，旧读取兼容也有缺口。 | 未满足近期维护和明确许可的筛选要求，排除，不采用。 |

## 本项目做法

1. 点击“粘贴并解析”时直接调用 `navigator.clipboard.readText()`，调用前没有异步等待，保留用户操作所需的激活状态。不查询 `clipboard-read` 权限，以免未实现该权限查询的浏览器在真正读取前失败。
2. 读取成功且非空时，覆盖完整信息文本框，复用 `parsePastedContact()`、`parseContact()` 和 `splitAddress()`；超过 2000 字仍由原解析器拒绝，不截断。失败不改下方名字、电话和地址，空剪贴板也不清空原文本。
3. API 不支持、权限拒绝或其他读取异常时，显示手动粘贴提示并聚焦输入框；保留原 `input` 事件自动解析和手改。解析成功后仍需“确认修改”才更新照片和下载。
4. 等待授权时禁用重复点击。用请求序号忽略在手动编辑、确认、关闭或重开弹窗前发起的旧读取结果和旧错误，避免覆盖新内容。
5. 示例号码经用户确认使用 `18888888888`（11 位），不放宽手机号规则。

## 浏览器限制与依据

- [MDN readText](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/readText) 说明安全上下文要求、空文本及 `NotAllowedError` 等错误；本项目按能力检测与异常处理回退。
- [WebKit Async Clipboard API](https://webkit.org/blog/10855/async-clipboard-api/) 说明 Safari 用户操作与系统粘贴授权限制。系统确认可能额外要求用户交互，网页不能保证所有设备都无授权提示地一键读取。
- 离线页面不发网络请求；剪贴板能力取决于浏览器。远端 Chromium 检查真实 HTTP loopback 剪贴板及在线/离线模拟分支，也覆盖四类屏幕；不宣称已在实体 iPhone Safari 或安卓授权界面验证。
