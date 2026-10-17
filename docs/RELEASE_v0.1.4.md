# v0.1.4 · 学院流程与标题序文修复测试版

适用于日文Bokuno Proto1.123，对应内部v296，包含v293—v296更新。

- **修复罗亚努学院术士对话白屏、跳场景的汉化故障。** 重定位后的中文对白超出旧文本识别范围，部分中文字节被解释成事件指令；本版同步范围，恢复选人、选术系与取消流程。
- 汉化标题动画四屏序文，采用维护者确认稿，保留省略号并去除行尾逗号、句号。
- 对白数字0—9统一大小、字底和居中定位；去掉住宿报价金额前多余空格，原收费计算保持。
- 继承首批311条排版、战后弓／铳标签、金钱语序、技力／术力以及此前字形和名称修复。

学院六名角色、六类术系入口、明确取消及重新交谈已实测，13组既有正常操作保护对照通过。11,877个活动影子文本入口静态全覆盖，其中157个先前超出识别范围；这不是逐个游玩157个场景。两种补丁完整链输出与v296逐字节一致。全剧情、自然战斗与其余3271条排版候选继续验收。

**建议旧版用户更新。** 从日文Bokuno Proto1.123底片重新应用本版BPS或IPS（二选一，推荐BPS），保留自己的原文件与存档。此完整汉化补丁不能直接叠加到旧汉化或个人修改ROM。若即时档是在异常跳场景之后保存，请回到触发前存档；重开旧窗口可刷新文字缓存。

**本汉化补丁禁止用于商业用途。转载、分享或二次发布必须注明本项目名称、维护者 akiaki0502SH 及[原始发布地址](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project)，并保留本声明与原有致谢。** Flips等第三方工具沿用原许可证。详见[使用与转载声明](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/NOTICE.md#汉化补丁使用与转载声明)。

安装顺序：日文RS3 v1.1无头ROM → 作者Bokuno Proto1.123 IPS → 本版中文BPS或IPS。

- `bokuno_cn_v0.1.4_windows.zip`：补丁、官方Flips v198、许可证、对应源码和说明。
- `bokuno_cn_v0.1.4_patch.zip`：纯补丁和说明。
- `bokuno_cn_v0.1.4_tools.zip`：可运行辅助工具和实现参考，仍不是完整独立构建套件。
- `Flips-v198-windows.zip`、`Flips-v198-source.zip`：第三方工具和对应源码。
- `SHA256SUMS`：附件校验。

发行包不含ROM、私人存档、个人修改ROM或独立字体。汉化输出CRC32为70DB3E30，SHA256为520BA0D0368B362FDEC1F5CCD2DA07A3A9243DB3E4521671D2233786A74B2462。

旧版本标签和附件保留。[安装指南](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/INSTALL.md) · [已知限制](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/blob/main/docs/KNOWN_ISSUES.md) · [反馈问题](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/issues/new/choose)

感谢原作、Bokuno改造版作者与贡献者，以及[韩文化项目](https://github.com/beck4679-alt/bokuno-rs3-ko)公开的本地化实现资料。

工具逐文件SHA256对应工具ZIP里的原始字节；Git可能规范文本换行。
