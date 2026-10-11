# Floating IPS / Flips v198

官方Windows构建：[Sir-Walrus/Flips v198](https://github.com/Sir-Walrus/Flips/releases/tag/v198)。原作者Alcaro及贡献者，GNU GPL v3或更高版本，原许可见COPYING及COPYING.gpl3。

本目录flips.exe取自该官方发布包，已用它实际应用本项目IPS和BPS，两种输出都与0.1目标逐字节一致。本机早期制作补丁的Flips来源版本标记不完整；本公开发行明确使用官方v198，没有重新命名旧程序来冒充版本。

Flips-v198-source.zip基于官方tag源码commit359d414，程序源码、libdivsufsort、许可及构建脚本未改。只移除了profile目录两个Firefox浏览器二进制基准档，避免在工具源码包中镜像其他程序。文件清单及原始档哈希见SOURCE_MANIFEST.json。

普通构建可用上游Makefile，Windows环境需要MinGW/G++、GNU Make和windres。例如在源码根目录运行`make TARGET=windows CPPFLAGS=-DFLIPS_COMMIT_COUNT=198`。上游make-windows.sh的PGO优化步骤另外使用Firefox10/17基准档；如需复现该优化步骤，从[完整官方源码tag](https://github.com/Sir-Walrus/Flips/tree/v198/profile)取得它们。原始完整源码档地址及校验值也保留在清单中。

这个程序属于第三方工具，不属于本项目原创。除以上省略的独立基准二进制，本项目未修改源码或官方Windows程序。
