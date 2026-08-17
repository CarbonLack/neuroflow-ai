# NeuroEphys AI 1.0 正式版验收记录

验收日期：2026-08-17  
验收平台：Windows 11 x64，Python 3.12.10  
产品版本：1.0.0

## 结论

NeuroEphys AI 1.0 的 Windows 安装版、Windows 便携版、Python wheel 和 Python
源码包均已从同一份 `release/v1.0.0` 源码构建并通过发布验收。普通 App 用户不需要
安装 Python；Python 用户可在独立虚拟环境中通过 `neuroephys` 公共 API 和命令行入口
调用核心能力。

## 自动化与文档

- 完整测试集：79 项通过。
- 中英文 Sphinx 手册：以 warnings-as-errors 模式构建通过。
- wheel 与源码包：`twine check` 通过。
- 发布物使用 SHA-256 校验清单固定。

## Windows 成品验收

最终便携版 EXE 已通过以下成品内置测试：

- 真实 Qt 主窗口创建、显示、事件循环、版本标题、双页面、内置手册和品牌资源；
- AI 最小结构化摘要、安全字段与人工确认边界；测试未发起网络请求；
- SVG、PDF、PNG 三种图形导出；
- MountainSort5 0.5.9：7 个 unit、610 个 spike，统一
  `neuroflow.sorting.v1` 结果格式；
- SpykingCircus2：6 个 unit、679 个 spike；
- Tridesclous2：7 个 unit、645 个 spike；
- Simple：6 个 unit、480 个 spike；
- Lupin：7 个 unit、649 个 spike；
- 四种内置 sorter 的横向比较结果可生成。

最终安装程序已在隔离目录完成静默安装。安装后的 EXE 再次通过窗口启动、AI 和三种图形
格式导出测试；卸载程序返回成功，并完整移除应用安装目录。用户项目工作区位于应用目录
之外，设计上不随卸载删除。

## Python 包验收

最终 wheel 已在不含 PySide6、Kilosort、MountainSort5 的独立 Python 3.12 虚拟环境中
重新安装并通过：

- `pip check` 无依赖冲突；
- `python -m neuroephys info` 正确报告 1.0.0；
- `import neuroephys as ne`、模拟项目创建和原始信号 QC 成功；
- 核心 wheel 不会强制安装桌面界面、GPU sorter 或 MountainSort；这些能力通过可选依赖
  按用户需要安装。

## 已知部署边界

- 正式支持 Windows 10/11 x64；Python 包正式验证版本为 CPython 3.12 x64。
- 核心 App 与核心 Python 包可在 CPU 环境运行。
- Kilosort4 属于可选 GPU 组件，需要兼容的 NVIDIA GPU、驱动、CUDA/PyTorch 组合，
  不包含在通用核心 App 中，也不会被其他 sorter 静默替代。
- Unit、显著性、解码和 AI 建议仍需研究者进行科学审核。
