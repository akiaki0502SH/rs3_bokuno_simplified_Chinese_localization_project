# 《浪漫沙加3》Bokuno 简体中文汉化补丁

适用于《Romancing SaGa 3》改造版 **Bokuno Proto1.123** 的非官方简体中文补丁。

**v0.1.3 · 2026-10-17 · 排版与战后成长提示修复测试版**。当前审阅并授权的译文已接入，正在进行实际游玩查漏和验收。只分发汉化补丁与工具，**不提供ROM**。

**本汉化补丁禁止用于商业用途。转载、分享或二次发布必须注明本项目名称、维护者 akiaki0502SH 及原始发布地址，并保留本声明与原有致谢。** 详见[使用与转载声明](NOTICE.md#汉化补丁使用与转载声明)。

[下载0.1.3测试版](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/tag/v0.1.3) · [Bokuno原补丁下载](https://ux.getuploader.com/romancingsaga312/download/560) · [安装说明](docs/INSTALL.md) · [已知限制](docs/KNOWN_ISSUES.md) · [反馈问题](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/issues/new/choose)

## 开始使用

1. 自行准备日文《Romancing SaGa 3》**v1.1、无512字节头**的ROM。
2. 从[Bokuno原补丁下载页](https://ux.getuploader.com/romancingsaga312/download/560)取得发行包，解压后应用 `ぼくのProto1.123.ips`，得到日文Bokuno Proto1.123。
3. 用本项目提供的Flips应用简体中文补丁，**BPS和IPS任选一种**。

**日文RS3 v1.1 → Bokuno Proto1.123 → 简体中文补丁**。推荐BPS，它会检查日文Bokuno底片是否匹配。

[Windows整合包](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/download/v0.1.3/bokuno_cn_v0.1.3_windows.zip)含补丁、Flips和说明；已有打补丁工具可下载[纯补丁包](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/download/v0.1.3/bokuno_cn_v0.1.3_patch.zip)。两包都没有ROM。

## 本版内容

- 调整首批311条文本排版：261条对白和50条固定说明，改善短语、姓名拆行及说明换行。
- 修复战后“弓体术”串字，显示“弓・铳提升了！”；弓和铳继续使用原版共用成长类别。
- 金钱提示改为“获得了4奥拉姆”等中文语序，包含金额上限分支；“技之力／术之力”统一为“技力／术力”。
- 继承此前物品／奥义提示语序、字体右侧缺笔画与底部对齐修复，以及已确认名称和菜单修订。

20组原生显示对照、117项取址／长度检查、7项既有提示回归及13组正常操作对照通过。剩余排版继续按实际窗口逐步核对；自然战斗完整结算和全部剧情仍需实玩验收。

当前236条非空独立术名已接入，包含“黑猫”“玻璃之盾”和两条“魔道板解读”。这不表示全游戏所有自然场景已经验收，请帮助检查残留日文、错译、显示与流程问题。

## 下载与资料

|内容|入口|
|---|---|
|Bokuno原作者补丁（先应用）|[原补丁下载页](https://ux.getuploader.com/romancingsaga312/download/560)|
|安装、底片校验、存档说明|[安装指南](docs/INSTALL.md)|
|当前限制与测试范围|[已知限制](docs/KNOWN_ISSUES.md)、[测试建议](docs/TESTING.md)|
|0.1.3内容与变更|[版本记录](docs/CHANGELOG.md)|
|汉化开发工具与Flips源码|[工具说明](docs/TOOLS.md)|
|文件校验值|[SHA256SUMS](SHA256SUMS)、[版本清单](patches/v0.1.3/RELEASE_MANIFEST.json)|

## 反馈

请在[GitHub Issues](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/issues/new/choose)提供版本、模拟器、地点或界面、复现步骤及截图。请不要上传ROM；需要存档时先保留自己的备份，再按维护者说明提供。

## 致谢与说明

感谢原作和Bokuno改造版作者及参与者，也感谢[韩文化项目](https://github.com/beck4679-alt/bokuno-rs3-ko)公开的本地化实现资料。本项目参考了其事件、字库和构建校验思路，并从日文Bokuno底片制作简体中文差异补丁。介绍页结构也参考了该项目。

本项目的ROM分析、翻译整理、工具开发及文档制作使用了AI辅助；译稿由维护者审阅，游戏内验收仍在进行。原作权利归各权利人，第三方工具保留各自许可证。详见[致谢](docs/CREDITS.md)和[第三方说明](NOTICE.md)。
