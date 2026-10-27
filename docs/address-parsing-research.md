# 收件信息解析调研与实现

2026-10-27 为 C0verSnow issue #5 在 GitHub 检索了同类项目，比较如下。仅采用仍在维护、许可证明确的来源；不复制解析器代码。

| 候选 | 活跃度与许可 | 实现、依赖与已知问题 | 本次选择 |
| --- | --- | --- | --- |
| [smartParsePro V4](https://github.com/wzc570738205/smartParsePro) | 1068 stars，2026-07 有提交；[SDK package.json](https://github.com/wzc570738205/smartParsePro/blob/main/packages/sdk/package.json) 声明 ISC | 离线行政区划树、别名、候选评分；SDK 无运行时第三方依赖，完整 SDK/数据较大。只写“鼓楼区”可能对应多个城市；[直辖市问题 #34](https://github.com/wzc570738205/smartParsePro/issues/34) 在 2026-07 有维护者回复，V4 输出完整层级。 | 借鉴父子关系匹配、同名地区不默认选第一条、直辖市重复省市层级的设计，不引入 SDK 或构建工具。 |
| [mumuy/data_location](https://github.com/mumuy/data_location) | 3205 stars，2026-10 有提交；MIT；[issue #88](https://github.com/mumuy/data_location/issues/88) 有维护者处理 | 六位行政区划编码可推导省市区父子关系，JSON 不需运行时依赖；乡镇数据可能滞后，行政管理区与正式行政区不同。 | 固定版本内嵌省市区数据，不使用乡镇推断，不请求在线服务。 |
| [akebe/address-parse](https://github.com/akebe/address-parse) | 464 stars，MIT，最后提交为 2024-04 | 按省、市、区解析和候选排序；提供浏览器包与数据；README 提醒不完整地址的第一条结果可能不正确，[省直辖县识别问题 #74](https://github.com/akebe/address-parse/issues/74)。 | 维护不够近期，排除。 |
| [ldwonday/zh-address-parse](https://github.com/ldwonday/zh-address-parse) | 830 stars，MIT，最后提交为 2023-10 | 正则或树查找，支持自定义行政区划；开发使用 webpack；README 所列行政数据较旧。 | 维护不够近期，排除。 |

## 本次实现

- `assets/regions/list.json` 原样来自 [mumuy/data_location 固定提交 1756d559ede7161b5d5a8d062a466beeb31cb714](https://github.com/mumuy/data_location/tree/1756d559ede7161b5d5a8d062a466beeb31cb714)，保留原 MIT `LICENSE`。生成页面内嵌 JSON 和许可，发布目录另带 `regions-LICENSE.txt`，单独保存 HTML 也保留许可。
- 解析代码由本项目自行实现：先提取标签、唯一手机号和姓名，再依照省市区编码匹配合法路径。支持常见省市区简称；只有唯一最佳路径才补全省市。四个直辖市的省、市都输出完整市名。区县后的文字不再推断或去重，避免误删真实街道、学校或楼栋名称。
- 解析时去掉地址里的空白、逗号和分号等分隔符；手机号去掉 `+86`、空格和连字符。支持标签任意顺序，以及无标签的“姓名 手机号 地址”和“地址 手机号 姓名”。其他排列、座机和多个手机号请手动填写。
- 不支持自动猜测缺少市级数据的省直辖县、没有区县的地址、同名地区歧义。数据未收录或过时也会影响结果；提示用户补充信息或手改，不用不存在的市级占位词凑数。
- 粘贴后自动解析，另保留重试按钮；结果只填入编辑框，核对确认后才下载。失败保留原编辑内容。三行按内嵌字体实际宽度寻找两个分割点，每行非空；容纳不下就报错，绝不截断或省略地址。
- 原始截图仅供离屏画布读取，CSS 从页面加载起就隐藏它。初始化只在完整 PNG 准备好后展示画布，失败显示提示；编辑、下载和恢复原信息都继续显示同一个画布。远端检查延迟首次解码、监测每帧原图可见性，并覆盖错误重试、初始化失败和原图恢复。
