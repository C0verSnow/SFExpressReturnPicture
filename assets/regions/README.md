# 离线省市区数据

`list.json` 原样取自 [mumuy/data_location](https://github.com/mumuy/data_location/blob/1756d559ede7161b5d5a8d062a466beeb31cb714/list.json)，固定版本 `1756d559ede7161b5d5a8d062a466beeb31cb714`。原 MIT 许可保存在同目录 `LICENSE`，不要删除。

只读取六位编码里的省、市、区县关系，详细地址不依赖乡镇数据库。更新时一起检查上游许可和行政区划变化，通过远端 CI 验证后取回新的 `pages/`；不在本地生成或编译。

方案比较与限制见 [解析调研](../../docs/address-parsing-research.md)。
