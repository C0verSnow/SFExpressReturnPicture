# issue #11：工程整理与行政层级去重调研

调查日期：2026-10-28。通过 GitHub 仓库搜索重新查找 `smartParsePro`、`data_location user:mumuy`、`Chinese address parse stars:>100`，再读取候选的仓库信息、最新提交、许可证、SDK 文档和维护者回复。下面的活跃度是调查时快照，不代表以后不变。

## 候选比较

| 项目 | 维护与许可 | 实现和依赖 | 已知限制与本项目取舍 |
| --- | --- | --- | --- |
| [smartParsePro V4](https://github.com/wzc570738205/smartParsePro) | [仓库信息](https://api.github.com/repos/wzc570738205/smartParsePro) 为 1068 stars；[最近提交](https://github.com/wzc570738205/smartParsePro/commit/13e66da5418b0764732a1a318764654d422ee486) 为 2026-07-29；[SDK 许可证](https://github.com/wzc570738205/smartParsePro/blob/13e66da5418b0764732a1a318764654d422ee486/packages/sdk/LICENSE) 为 ISC。仓库 API 的顶层 license 为空，因此以 SDK 自带 LICENSE 和 package.json 为准。 | [SDK 文档](https://github.com/wzc570738205/smartParsePro/blob/13e66da5418b0764732a1a318764654d422ee486/packages/sdk/README.md) 和[核心源码](https://github.com/wzc570738205/smartParsePro/blob/13e66da5418b0764732a1a318764654d422ee486/packages/core/src/engine.cjs) 采用行政路径、别名索引和候选评分；独立保存省、市、区县与 detail。SDK 无运行时第三方依赖，[包声明](https://github.com/wzc570738205/smartParsePro/blob/13e66da5418b0764732a1a318764654d422ee486/packages/sdk/package.json) 要求 Node >=22，并提供 CommonJS、ESM、浏览器入口。 | 同名区县会产生多个候选；排名最高不等于已确认。参考其“先保留行政层级、再由调用方处理歧义”的设计；不引入完整 SDK、乡镇库或构建工具。维护者在[直辖市问题 #34](https://github.com/wzc570738205/smartParsePro/issues/34#issuecomment-5112128142) 于 2026-07-29 回复 V4 已调整输出。 |
| [mumuy/data_location](https://github.com/mumuy/data_location) | [仓库信息](https://api.github.com/repos/mumuy/data_location) 为 3205 stars；[最近提交](https://github.com/mumuy/data_location/commit/1756d559ede7161b5d5a8d062a466beeb31cb714) 为 2026-10-12；[LICENSE](https://github.com/mumuy/data_location/blob/1756d559ede7161b5d5a8d062a466beeb31cb714/LICENSE) 为 MIT。 | [数据说明](https://github.com/mumuy/data_location/blob/1756d559ede7161b5d5a8d062a466beeb31cb714/README.md) 用六位编码区分省、市、县级关系。本项目直接读取已固定的 JSON，不需要运行时库或在线请求。 | 乡镇数据不能保证及时有效，行政管理区和正式行政区需区分。[维护者在 #88 的回复](https://github.com/mumuy/data_location/issues/88#issuecomment-6050603373) 说明部分开发区旧文件不再维护；2026-10-09 的[后续回复](https://github.com/mumuy/data_location/issues/88#issuecomment-6075670802) 也解释了农场与法定行政区的差异。继续使用现有固定数据，不猜测镇街，不把“投资区”等一律当成正式区县。 |
| [akebe/address-parse](https://github.com/akebe/address-parse) | [仓库信息](https://api.github.com/repos/akebe/address-parse) 为 464 stars、MIT，最后 push 为 2024-04-23；[默认分支最近提交](https://github.com/akebe/address-parse/commit/bf3e5c4cf5a13c039dc8d76fe31bc0386cf5fc5a) 的提交日期为 2021-12-30。 | 候选省市区解析方向相关，但本次没有引入其实现。 | 近期维护不足，排除，不作为本次实现依据。push 时间不能当成默认分支最新代码提交时间。 |

## 地址规则如何落地

[smartParsePro 的直辖市说明](https://github.com/wzc570738205/smartParsePro/blob/13e66da5418b0764732a1a318764654d422ee486/packages/sdk/README.md#直辖市) 区分了行政层级和显示文字：北京的 province.name 和 city.name 可以同时是“北京市”，city.sourceName 仍记录原数据中的“市辖区”。一个文字区间只作为一份显式匹配证据，其他层级可由已经确定的父子路径补全。这个设计符合 [issue #11](https://github.com/C0verSnow/SFExpressReturnPicture/issues/11) 的新规则，不能再用字符串集合把相同名称的两个行政层级合为一个。

本项目据此自行实现以下约束，不复制外部解析器代码：

1. 先识别唯一可信的省、市、区县路径，保持三个字段，再拼出完整规范化地址。京津沪渝各有同名的省级和市级两份文字；普通省份保持常规省市区。
2. 仅清理详细地址开头与这条已识别路径重复的行政前缀，以及有明确重复证据的相同镇街前缀。道路、学校、小区、楼栋中的同名词不是全局替换对象。不能证明是重复时保留信息或提示人工核对。
3. 歧义、区县缺失或市级数据缺失时不随意选第一条、不凭空补市。页面保留原编辑内容，允许用户补充或手改。
4. 完整规范化地址先确定，再按字体宽度排三行；三行拼接必须等于规范化地址。沿用现有规则：完整正文放不下时才尝试省略配对括号附注，并明确提示；不得截掉正文来凑行数。

Howard 样例的号码在回归夹具中脱敏，地址期望固定为：

```text
北京市北京市通州区宋庄镇宋庄南路北京工商大学嘉华学院
```

## 工程目录如何落地

[PyPA 官方 src layout 说明](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) 将可导入业务包放到 `src/`，并说明 CLI 从源码树运行时需要明确处理导入路径。本项目采用按职责分开的轻量目录，把兼容启动脚本留在根目录；不新增发布 Python 包或本地构建的要求。smartParsePro 的[项目目录](https://github.com/wzc570738205/smartParsePro/blob/13e66da5418b0764732a1a318764654d422ee486/packages/sdk/README.md#项目结构) 同样将解析核心、数据、测试、示例和发布产物分开，支持本次“源码与生成文件分开”的选择；本项目规模更小，不照搬其 workspaces/server 层次。

地址纯逻辑可独立接收区划数据和文字测量方法，浏览器 UI 只负责读写字段、反馈错误和确认下载。模板、地区数据与业务 Python 归入 `src/sf_return/`；字体、样例照片保持源资源，`tests/`、`docs/` 保持原职责，`pages/` 继续是必须提交的静态发布快照。具体迁移映射、入口参数与产物交付方式见开发文档。

本次没有替换区划数据库版本，没有复制外部代码，也没有新增运行时依赖。原有 data_location MIT 许可随 JSON 迁移，继续内嵌到离线 HTML 并复制到 Pages 发布目录。所有构建、页面生成与项目测试交给已有远端 GitHub Actions，本地只进行代码阅读、编辑和静态检查。
