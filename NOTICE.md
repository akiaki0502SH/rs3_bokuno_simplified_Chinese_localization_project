# 第三方与许可说明

本仓库分发非官方汉化差异补丁和工具，不提供原版或改造版ROM、私人存档、模拟器核心、商业字体文件或API凭据。原作及第三方内容的权利归各权利人。

## Floating IPS

原作者Alcaro及其贡献者。公开整合包使用官方v198 Windows构建，GNU General Public License v3或更高版本。原COPYING、COPYING.gpl3及对应构建源码一同提供，不能将该程序认领为本项目原创。

源码中libdivsufsort保留其原许可文件。源码包没有改变Flips源代码，只省略独立Firefox浏览器二进制基准数据；普通Makefile构建可直接使用。需要上游PGO优化构建的训练数据时，请从标明的官方tag取得，详见third_party/Flips/README.md。

## 本项目参考工具

tools/reference是本工程当前相关工具的参考快照，保留所需本地Python模块。它没有完整翻译数据、字体本体或冻结构建输入，不能据此声称能独立重建全部汉化ROM。原创工具暂未额外指定统一开源许可证，第三方许可仍分别适用。
