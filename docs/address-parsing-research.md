# 收件信息解析调研与实现

## issue #11 规则更新（2026-10-28）

本次以省级、市级、区县级三个结构化层级各一份为准。直辖市省级与市级同名也分别保留，例如 `北京市北京市通州区`；下文旧调研中关于展示层级的结论已同步修正。详见 [本次 GitHub 核对与取舍](issue-11-research.md) 和 [开发说明](development.md)。

## issue #9 补充调研（2026-10-27）

本次重新在 GitHub 检索 `smartParsePro`、`mumuy/data_location` 及中国地址解析项目，并读取仓库状态、SDK 包声明及维护者 Issue 回复：smartParsePro 为 1068 stars，最近推送 2026-07-29，SDK 声明 ISC；data_location 为 3205 stars，最近推送 2026-10-12，MIT。两者下表中的 Issue 都有维护者处理记录。继续参考前者的行政区划候选匹配、后者的编码父子关系，沿用已固定的数据，不引入 SDK 或乡镇数据库，也不复制源码。

- smartParsePro 的省、市字段是不同数据层级；issue #11 明确要求两层都保留，不能用字符串去重合成一个市名。
- data_location 提醒开发区、投资区可能是行政管理区，不能把它们按正式镇级数据猜测或补全。重复处理限定在地址开头已确认的行政路径与完全相同的镇/街道前缀，不在整段文字内全局删除“北京”“南山”等词，保留学校、道路、楼栋名。
- 用户明确选择：先尝试完整三行，仅放不下时再移除配对括号中的说明。混用半角左括号和全角右括号也视为一对；不成对的括号保留。删除应告知用户并仍须核对，不用截断正文来凑三行。

深色兼容参考 [Chrome Auto Dark Theme 官方说明](https://developer.chrome.com/blog/auto-dark-theme#how_to_opt_out_of_auto_dark_theme) 和 [Chromium only 关键字说明](https://groups.google.com/a/chromium.org/g/blink-dev/c/Et7c6cWND3Q/m/LqK1JhavDQAJ)：`light` 表示支持浅色，`only light` 才禁止自动强制变色；meta 可从首次绘制前声明。系统深色与 Chrome 自动深色是两条不同检查路径。远端回归同时比较预览画布截图与导出 PNG，以及连续修改时未编辑的区域。实体安卓浏览器/厂商强制深色仍需人工复核，不能用桌面模拟声称已覆盖所有设备。

2026-10-27 为 C0verSnow issue #5 在 GitHub 检索了同类项目，比较如下。仅采用仍在维护、许可证明确的来源；不复制解析器代码。

| 候选 | 活跃度与许可 | 实现、依赖与已知问题 | 本次选择 |
| --- | --- | --- | --- |
| [smartParsePro V4](https://github.com/wzc570738205/smartParsePro) | 1068 stars，2026-07 有提交；[SDK package.json](https://github.com/wzc570738205/smartParsePro/blob/main/packages/sdk/package.json) 声明 ISC | 离线行政区划树、别名、候选评分；SDK 无运行时第三方依赖，完整 SDK/数据较大。只写“鼓楼区”可能对应多个城市；[直辖市问题 #34](https://github.com/wzc570738205/smartParsePro/issues/34) 在 2026-07 有维护者回复，V4 输出完整层级。 | 借鉴父子关系匹配、同名地区不默认选第一条、直辖市重复省市层级的设计，不引入 SDK 或构建工具。 |
| [mumuy/data_location](https://github.com/mumuy/data_location) | 3205 stars，2026-10 有提交；MIT；[issue #88](https://github.com/mumuy/data_location/issues/88) 有维护者处理 | 六位行政区划编码可推导省市区父子关系，JSON 不需运行时依赖；乡镇数据可能滞后，行政管理区与正式行政区不同。 | 固定版本内嵌省市区数据，不使用乡镇推断，不请求在线服务。 |
| [akebe/address-parse](https://github.com/akebe/address-parse) | 464 stars，MIT，最后推送为 2024-04（默认分支最近提交实为 2021-12，见本次核对） | 按省、市、区解析和候选排序；提供浏览器包与数据；README 提醒不完整地址的第一条结果可能不正确，[省直辖县识别问题 #74](https://github.com/akebe/address-parse/issues/74)。 | 维护不够近期，排除。 |
| [ldwonday/zh-address-parse](https://github.com/ldwonday/zh-address-parse) | 830 stars，MIT，最后提交为 2023-10 | 正则或树查找，支持自定义行政区划；开发使用 webpack；README 所列行政数据较旧。 | 维护不够近期，排除。 |

## 本次实现

- `src/sf_return/address/data/list.json` 原样来自 [mumuy/data_location 固定提交 1756d559ede7161b5d5a8d062a466beeb31cb714](https://github.com/mumuy/data_location/tree/1756d559ede7161b5d5a8d062a466beeb31cb714)，保留原 MIT `LICENSE`。生成页面内嵌 JSON 和许可，发布目录另带 `regions-LICENSE.txt`，单独保存 HTML 也保留许可。
- 解析代码由本项目自行实现：先提取标签、唯一手机号和姓名，再依照省市区编码匹配合法路径。支持常见省市区简称；区县简称须有独立分隔边界或位于输入结尾，避免把南山大道猜成南山区。只有唯一最佳路径才补全省市。issue #11 起，省级、市级、区县级分别保留；直辖市同名的省、市不合并。重复清理仅消费开头已确认的完整行政路径、明确重复的祖先字段链，以及重复路径前后完全相同的镇/街道；孤立同名区县词保留供核对；保留正文中的地名，不猜测缺失的乡镇。
- 解析时去掉地址里的空白、逗号和分号等分隔符；手机号去掉 `+86`、空格和连字符。支持标签任意顺序，以及无标签的“姓名 手机号 地址”和“地址 手机号 姓名”。其他排列、座机和多个手机号请手动填写。
- 不支持自动猜测缺少市级数据的省直辖县、没有区县的地址、同名地区歧义。数据未收录或过时也会影响结果；提示用户补充信息或手改，不用不存在的市级占位词凑数。
- 粘贴后自动解析，另保留重试按钮；结果只填入编辑框，核对确认后才下载。失败保留原编辑内容。三行按内嵌字体实际宽度寻找两个分割点，每行非空；issue #9 起，完整地址放不下时从后往前逐个去掉配对圆括号附注，并告知用户删去了哪些说明。仍放不下就报错，不截断正文。
- 原始截图仅供离屏画布读取，CSS 从页面加载起就隐藏它。初始化只在完整 PNG 准备好后展示画布，失败显示提示；编辑、下载和恢复原信息都继续显示同一个画布。远端检查延迟首次解码、监测每帧原图可见性，并覆盖错误重试、初始化失败和原图恢复。

- 远端严格像素检查发现，解析测量后重新绘制相同电话时 Chromium 会出现数字边缘抗锯齿差异。因此后续照片从当前画布开始，只替换本次修改字段；恢复默认值使用首次画布对应像素，恢复原图值使用原图对应像素。首次画布只保留一张，不随编辑次数增长缓存。
