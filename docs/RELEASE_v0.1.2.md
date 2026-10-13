# v0.1.2 · 战后提示与字体基线修复测试版

适用于日文Bokuno Proto1.123，对应内部v290，包含本轮两项修复：

- 战后提示按中文语序显示“习得招架的／奥义”和“获得了／野生药”；名称由游戏读取实际技能或物品，原掉落和习得处理保持。
- 修复王、形、阳等字偏高1像素。2673个中文单字核对，60个正文汉字统一底部位置，一、二恢复原字体设计位置；字号、笔画和横向位置保持，继承右侧缺笔画修复。

三份真实存档的字形底部逐像素一致，10组正常路线保护对照通过；战后提示已有7组有效原生显示检查。独立重建及完整补丁链符合当前目标。文本换行问题继续收集，留到最后集中修复；全游戏自然场景继续手测。

**本汉化补丁禁止用于商业用途。转载、分享或二次发布必须注明本项目名称、维护者 akiaki0502SH 及[原始发布地址](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project)，并保留本声明与原有致谢。** Flips等第三方工具沿用原许可证。详见[使用与转载声明](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/NOTICE.md#汉化补丁使用与转载声明)。

安装：日文RS3 v1.1无头ROM → 作者Bokuno Proto1.123 IPS → 本版中文BPS或IPS，二选一，推荐BPS。从日文Bokuno底片重新打本版补丁，原有存档可备份后继续复测。旧即时档中的文字画面可能缓存旧字图，关闭重开界面或正常切换角色即可刷新。

- `bokuno_cn_v0.1.2_windows.zip`：补丁、官方Flips v198、许可证、对应源码及说明。
- `bokuno_cn_v0.1.2_patch.zip`：纯补丁与说明。
- `bokuno_cn_v0.1.2_tools.zip`：可运行辅助工具、34份Python实现参考及Lua/PowerShell检查入口，不是完整独立构建套件。
- `Flips-v198-windows.zip`、`Flips-v198-source.zip`：第三方工具和对应源码，版本保持。
- `SHA256SUMS`：发行附件校验。

发行包不包含ROM、私人存档或独立字体。汉化输出CRC32为F086E805，SHA256为20B421AE2840FB23A40CC7A5B39692781190FE24FC8D1775E0045B7E8FA806F2。两种补丁链及公开辅助工具输出均与v290目标逐字节相同。

v0.1及v0.1.1的标签和附件保留。少数长名称的一格两字仍受栏位限制。[安装指南](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/INSTALL.md) · [已知限制](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/KNOWN_ISSUES.md) · [问题反馈](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/issues/new/choose)

工具逐文件SHA256对应工具ZIP中的原始字节；Git可能规范文本换行，补丁及程序二进制不变。
