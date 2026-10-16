# 安装指南

[返回主页](../README.md) · [下载0.1.3](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/tag/v0.1.3)

## 准备

|文件|要求|
|---|---|
|日文RS3原版ROM|v1.1，无512字节头，4,194,304字节；自行准备|
|Bokuno作者补丁|`ぼくのProto1.123.ips`；从原作者发行包取得|
|本项目汉化补丁|0.1.3的BPS或IPS，任选一种|
|Flips|Windows整合包已附；也可使用自己的Flips|

[Bokuno原作者发行入口](https://ux.getuploader.com/romancingsaga312/download/560)。本仓库不镜像原Bokuno补丁或ROM。

## 使用Flips

1. 解压Windows整合包，打开 `Flips/flips.exe`，点击 **Apply Patch**。
2. 选择 `ぼくのProto1.123.ips`，再选择日文RS3 v1.1原版ROM，另存为日文Bokuno。
3. 再点 **Apply Patch**，选择 `patches/bokuno_cn_v0.1.3_Proto1.123.bps`，再选择上一步的日文Bokuno，另存为汉化版。
4. 用支持该改造版的SNES模拟器打开汉化输出。当前工程主要用Snes9x 1.63进行玩家场景检查，开发时也使用Mesen作受控显示观察。

已有Flips的玩家只需解压纯补丁包。IPS版同样可用，但IPS本身不验证底片；请核对下面的校验值。不要把两种汉化格式连续打在一起，也不要把汉化补丁直接打在RS3原版上。

## 输入与输出校验

|阶段|大小|CRC32|
|---|---|---|
|日文RS3 v1.1，无头|4,194,304|6C50C2CF|
|日文Bokuno Proto1.123|8,388,608|7E165025|
|简体中文0.1.3输出|8,388,608|9EA2DE41|

SHA256：

```text
RS3 v1.1
3EFA91F18CC6CD012BC213FF421813C113DF51E62F68180CC54C782F21616897

日文Bokuno Proto1.123
4793E1422295B8C13BA81B070B941288D36BE339FF20F914652CE63CC06F2DA0

简体中文0.1.3
26CBE0971C02D2908B486FF40E8616D4E70CB950ADAC8DEEB4632E3F311EAB7F
```

带头原版通常为4,194,816字节。本版已验证的是无头原版链；请先使用能识别SNES拷贝器头的工具处理，再确认校验值。扩展名`.smc`／`.sfc`不能证明版本。BPS提示底片不匹配时，先核对是否用错版本、跳过Bokuno步骤、选了旧汉化版，或应用过其他附加补丁。

## 存档

先备份自己的SRAM和即时档。模拟器通常按ROM文件名前缀匹配存档，输出改名后需为存档副本使用相应前缀。旧即时档可能保留旧文字画面缓存，关闭再重开相关菜单可刷新；不要仅靠旧缓存判断补丁失效。

原版RS3与改造版的存档兼容性不在本版验证范围。首次测试建议新开游戏。已有本工程测试版存档可在备份后继续检查，记录任何异常。

本版汉化底片固定为日文Proto1.123，其他Bokuno版本和附加补丁组合尚未验证。
