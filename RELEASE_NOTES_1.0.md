# NeuroEphys AI 1.0.0 发行说明

发布日期：2026-08-17

这是 NeuroEphys AI 首个正式版，面向 64 位 Windows 10/11，并同时提供桌面 App 和
Python 包两种入口。内部 `neuroflow` 命名继续保留，以兼容既有项目和插件；新脚本应
优先使用公开的 `neuroephys` 包。

## 交付形式

- `NeuroEphysAI-Setup-1.0.0.exe`：无需管理员权限的当前用户安装程序，创建桌面和开始
  菜单快捷方式。
- `NeuroEphysAI-1.0.0-Windows-x64-portable.zip`：完整解压即可运行的便携 App。
- `neuroephys_ai-1.0.0-py3-none-any.whl`：Python 3.12 包。
- `neuroephys_ai-1.0.0.tar.gz`：Python 源码包。
- `SHA256SUMS.txt`：所有正式发行物的完整性校验值。

## v1.0 的产品化变化

- 统一 App、项目清单、导出 provenance 与 Python 包的 `1.0.0` 版本标识。
- 用户工作区与程序安装目录分离，默认写入 `Documents\NeuroEphysAI`，支持
  `NEUROEPHYS_HOME` 管理员覆盖。
- 新增稳定的 `neuroephys` 公共 Python API、按需导入、命令行环境检查、教学项目和
  离线自检入口。
- 将桌面界面、MountainSort5 和 Kilosort4 设计为 Python 可选组件，核心包不会因
  CUDA 或本机 C++ 编译环境缺失而无法安装。
- Windows App 采用 one-folder 结构，科学依赖可以检查，启动时不需要临时解包。
- 继续支持 11 阶段可恢复工作流、双语教程、Sorter 白名单探测、项目审计与受控 AI。

## 兼容性

- 既有 `neuroflow_project.json` 项目可继续打开。
- 内部 `neuroflow` Python 导入路径继续可用，但不作为新的稳定公共 API 文档入口。
- 核心 App 不强制包含数 GiB 的 CUDA/PyTorch 运行时；Kilosort4 可通过独立 GPU 组件
  或受管理的完整分析环境启用。

候选 Unit、统计、机器学习和 AI 输出均需研究者审核。本版的软件验证不能替代数据
授权、实验设计、预注册、统计假设检查或领域专家复核。
