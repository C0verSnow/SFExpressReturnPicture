# 收件信息解析调研

针对 issue #5，检索了 GitHub 上的同类项目：

- [smartParsePro V4](https://github.com/wzc570738205/smartParsePro)：SDK 使用 ISC 许可，支持离线识别姓名、电话和省市区，返回多个候选供用户选择；2026 年有提交和维护者回复。它使用行政区划数据和候选评分，短地址、同名区县可能有多个结果；其直辖市处理曾有[问题反馈](https://github.com/wzc570738205/smartParsePro/issues/34)，V4 已调整。SDK 无运行时第三方依赖，但自带较大的行政区划数据，需要留意页面体积和数据更新。
- [address-parse](https://github.com/akebe/address-parse)：MIT 许可，同样采用行政区划数据和候选结果；GitHub 星标较多，但最近提交为 2024 年，近期 issue 存在未回复的情况。已有[省直辖县识别问题](https://github.com/akebe/address-parse/issues/74)。它也提供浏览器包和行政区划数据。

可借鉴的思路是按行政区划父子关系识别省、市、区，将同名地区作为候选交给用户确认，直辖市输出两个同名层级，并保留人工修改。地址数据会变化，不能把匹配结果当作绝对正确；超长地址应提示用户检查，而不是截断。
