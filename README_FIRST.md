# NeuroEphys AI 1.1 — 首次使用 / First read

## Windows 普通用户

1. 推荐运行 `NeuroEphysAI-Setup-1.1.0.exe`，安装过程不需要管理员权限。
2. 安装完成后双击桌面或开始菜单中的 **NeuroEphys AI**。
3. 也可以使用便携 ZIP：完整解压后双击
   `NeuroEphysAI\NeuroEphysAI.exe`。必须保留 `_internal` 等同目录内容，不能只复制 EXE。
4. 程序、项目数据和原始记录彼此分离。默认工作区是
   `Documents\NeuroEphysAI`，卸载应用不会删除该工作区。
5. App 已包含 Python 与核心科学依赖，不要求另装 Python、Conda 或编译器。

首次启动可进入 **示例项目**，选择一套教学模拟，确认界面、图表和导出都能工作。
工作区默认同时显示左侧流程、中间分析和右侧 AI/帮助/日志；三栏可拖动调宽，左栏可
缩略为步骤编号。每个阶段第一次打开时会显示可关闭的新手引导。Sorter 管理页显示当前
电脑上每个后端的真实状态。核心发行版包含 CPU 分析链；Kilosort4 依赖兼容的 NVIDIA
GPU、驱动和独立 GPU 组件。缺少某个 sorter 不影响导入、质控、已有 sorting 结果、
统计、解码、出图和其他可用后端。

复制给另一台电脑时，请复制整个便携版文件夹或原始 ZIP，不要复制项目工作区中的私有
数据、凭据或未脱敏日志。

## Python 用户

NeuroEphys AI 同时发布 `neuroephys-ai` wheel 和源码包。正式验证环境为 64 位
Python 3.12：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install neuroephys_ai-1.1.0-py3-none-any.whl
.\.venv\Scripts\neuroephys.exe info
```

```python
from pathlib import Path
import neuroephys as ne

project = ne.create_simulated_project(Path("example_project"))
qc = ne.run_raw_qc(project)
print(ne.__version__, qc["quality_score"])
```

可选组件：`[desktop]` 提供 Python 启动的 GUI；`[mountainsort]` 提供 MountainSort5；
`[kilosort]` 提供 Kilosort4。后二者有本机编译器或 GPU/CUDA 兼容性要求。

## 科学与隐私边界

- 原始数据默认只读，派生数据写入项目目录。
- 在线 AI 只接收用户确认后的最小结构化摘要；API 密钥不写入项目。
- Unit、统计显著性、解码结果和 AI 建议必须由研究者审核，软件不会替代实验设计与
  生物学判断。
- 第三方组件来源见 `THIRD_PARTY_SOURCES.md`，项目权利说明见
  `PROJECT_RIGHTS_NOTICE_ZH.md`。

---

## English quick start

Run `NeuroEphysAI-Setup-1.1.0.exe`, then open **NeuroEphys AI** from the desktop
or Start menu. The installer is per-user and requires no administrator access.
For the portable edition, extract the complete ZIP and run
`NeuroEphysAI\NeuroEphysAI.exe`; do not copy the EXE by itself. Python and the
core scientific runtime are bundled. User projects remain in
`Documents\NeuroEphysAI` and are not removed when the application is uninstalled.

Python 3.12 users can install the wheel and run `neuroephys info`. Optional
extras are `[desktop]`, `[mountainsort]`, and `[kilosort]`. Review all candidate
units, statistical results, decoding results, and AI suggestions scientifically.
