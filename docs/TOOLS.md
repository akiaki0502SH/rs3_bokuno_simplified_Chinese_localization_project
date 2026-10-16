# 工具与实现参考

[返回主页](../README.md) · [下载工具源码包](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/download/v0.1.3/bokuno_cn_v0.1.3_tools.zip)

## 可直接使用的辅助工具

`tools/verify_rom.py`：使用Python标准库识别RS3原版、日文Bokuno和中文0.1、0.1.1、0.1.2及0.1.3版本，输出大小、CRC32和SHA256，不改文件。

```text
python tools/verify_rom.py your_rom.sfc
```

`tools/patch_tool.py`：通过外部Flips应用或创建本版汉化补丁，先检查底片／目标，不覆盖既有输出，完成后验证输出SHA256。

```text
python tools/patch_tool.py apply --flips third_party/Flips/flips.exe --patch patches/v0.1.3/bokuno_cn_v0.1.3_Proto1.123.bps --input bokuno_jp.sfc --output bokuno_cn.sfc
```

`tools/inspect_ips.py`：只读取IPS记录边界和长度，不需要ROM。

```text
python tools/inspect_ips.py patches/v0.1.3/bokuno_cn_v0.1.3_Proto1.123.ips
```

## 汉化开发参考快照

tools/reference包含编码、字形与显示处理、名称／说明接入、原生菜单修订、谢拉哈措辞覆写、全套中文单字无损定位、正文基线及战后提示语序处理、首批排版与战后成长提示处理及Snes9x有限回归工具。和韩文作者的公开参考资料类似，这是一组实现参考快照，**不是完整翻译数据或独立运行的全工程构建套件**。

这些脚本保留原工程目录、输入哈希与有界写入检查，部分路径和源输入是当时工作环境的配置。需要相应冻结JSON、字体和合法ROM才能运行，未把这些私有输入放进本仓库。库依赖通常为Python 3.10+、Pillow、NumPy；模拟器核心请自行取得。不要把未改配置的参考脚本当作普通玩家安装步骤。

可运行的辅助工具只需要Python标准库；玩家直接使用Flips即可，不需要安装Python。

## Flips

[官方Windows工具](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/download/v0.1.3/Flips-v198-windows.zip) · [对应源码](https://github.com/akiaki0502SH/rs3_bokuno_simplified_Chinese_localization_project/releases/download/v0.1.3/Flips-v198-source.zip) · [原作者项目](https://github.com/Sir-Walrus/Flips)

保留GPL许可与原作者署名。上游源码、构建方式及省略的非源码基准数据说明见[第三方Flips说明](../third_party/Flips/README.md)。
