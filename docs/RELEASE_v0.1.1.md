# v0.1.1 · 中文字体修复测试版

适用于日文Bokuno Proto1.123，对应内部v288，继承v0.1的译文与功能。

本版修复“吗、娜”等中文单字的右侧缺笔画及一像素错位。2673个中文单字全部核对，1719个无损移动到统一中线；原1620个右侧越界风险归零，笔画形状与字号保持。原生绘字检查中，旧“吗”缺4个墨点、“娜”缺7个，本版均完整显示。对白和设置页面的上下行同字逐像素匹配，六组正常路线及独立重建通过。

**本汉化补丁禁止用于商业用途。转载、分享或二次发布必须注明本项目名称、维护者 akiaki0502SH 及[原始发布地址](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project)，并保留本声明与原有致谢。** Flips等第三方工具沿用各自原许可证。详见[使用与转载声明](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/NOTICE.md#汉化补丁使用与转载声明)。

安装顺序：日文RS3 v1.1无头ROM → 作者Bokuno Proto1.123 IPS → 本汉化BPS或IPS。推荐BPS；从日文Bokuno底片重新应用本版补丁，不叠加在旧汉化ROM上。玩家原有存档可备份后继续复测，已打开的旧窗口请关闭再重开以刷新字图。

- `bokuno_cn_v0.1.1_windows.zip`：补丁、官方Flips v198、许可证、对应源码和安装说明。
- `bokuno_cn_v0.1.1_patch.zip`：纯补丁与说明。
- `bokuno_cn_v0.1.1_tools.zip`：可运行辅助工具及27份汉化实现参考源码，不是完整独立构建套件。
- `Flips-v198-windows.zip`、`Flips-v198-source.zip`：第三方工具和源码，与v0.1所附版本相同。
- `SHA256SUMS`：发行附件校验。

所有发行包均不包含ROM或私人存档。汉化输出CRC32为1E208499，SHA256为BCE976F8172B5D6F489E0311F44AB8CE2FE644CD14236813EE478DBE22F0D35C。两种补丁完整链输出都与v288目标逐字节一致，BPS拒绝错误底片的检查通过。

少数历史长名称的一格两字仍受栏位限制，全游戏自然场景继续验收。v0.1的标签和发行附件保留。[安装指南](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/INSTALL.md) · [已知限制](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/KNOWN_ISSUES.md) · [问题反馈](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/issues/new/choose)

工具逐文件SHA256对应工具ZIP里的原始字节；Git可能规范文本换行，补丁和程序二进制保持原字节。
