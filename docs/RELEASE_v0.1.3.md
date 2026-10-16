# v0.1.3 · 排版与战后成长提示修复测试版

适用于日文Bokuno Proto1.123，对应内部v292，包含v291和v292的本轮修复：

- 首批调整311条排版：261条对白和50条固定说明，改善姓名、短语拆行及说明换行。
- 修复“弓体术”串字，恢复“弓・铳提升了！”；弓和铳保留原版共用成长类别。
- 金钱改为“获得了4奥拉姆”等中文语序，包含金额上限分支；“技之力／术之力”统一为“技力／术力”。
- 继承此前物品／奥义提示语序、字体右侧缺笔画与正文底部对齐、已确认名称和菜单修复。

20组原生显示对照、117项取址／长度、7项既有提示回归、13组正常操作保护对照及五份真实场景档载入通过。IPS/BPS完整补丁链与v292目标逐字节相同。剩余3271条默认第三版排版改动未纳入；住宿数字前导留白继续跟进。自然战斗完整结算及全剧情仍需实玩验收。

**本汉化补丁禁止用于商业用途。转载、分享或二次发布必须注明本项目名称、维护者 akiaki0502SH 及[原始发布地址](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project)，并保留本声明与原有致谢。** Flips等第三方工具沿用原许可证。详见[使用与转载声明](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/NOTICE.md#汉化补丁使用与转载声明)。

安装：日文RS3 v1.1无头ROM → 作者Bokuno Proto1.123 IPS → 本版中文BPS或IPS，二选一，推荐BPS。从日文Bokuno底片重新应用本版补丁。原有存档请先备份；旧即时档可能保留旧文字缓存，重开菜单或重新触发提示后判断。

- `bokuno_cn_v0.1.3_windows.zip`：补丁、官方Flips v198、许可证、对应源码及说明。
- `bokuno_cn_v0.1.3_patch.zip`：纯补丁与说明。
- `bokuno_cn_v0.1.3_tools.zip`：可运行辅助工具、48份Python实现参考及Lua/PowerShell检查入口，不是完整独立构建套件。
- `Flips-v198-windows.zip`、`Flips-v198-source.zip`：第三方工具和对应源码。
- `SHA256SUMS`：发行附件校验。

发行包不包含ROM、私人存档或独立字体。汉化输出CRC32为9EA2DE41，SHA256为26CBE0971C02D2908B486FF40E8616D4E70CB950ADAC8DEEB4632E3F311EAB7F。

v0.1、v0.1.1及v0.1.2的标签和附件保留。少数长名称的一格两字仍受栏位限制。[安装指南](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/INSTALL.md) · [已知限制](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/KNOWN_ISSUES.md) · [问题反馈](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/issues/new/choose)

工具逐文件SHA256对应工具ZIP中的原始字节；Git可能规范文本换行，补丁及程序二进制不变。
