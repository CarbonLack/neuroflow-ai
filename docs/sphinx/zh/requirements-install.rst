系统要求与安装
==============

硬件需求由准备运行的任务决定。打开项目、检查图表和导入已处理 spike 时间所需资源
较少；长时间高密度记录的 sorting 会消耗更多内存、磁盘和计算资源。

实用起步配置
------------

* 正式 App 面向 64 位 Windows 10/11，不要求用户安装 Python 或 Conda。
* 短教学数据建议 16 GB 内存；常规多通道工作建议 32 GB 或更高。
* 磁盘需同时容纳原始记录、标准缓存、sorter 原生输出和导出结果。
* Kilosort4 需要受支持的 NVIDIA GPU。CPU sorter 通过环境探测后也可选择。

安装 Windows App
----------------

推荐从 GitHub **Releases** 或比赛交付目录下载
``NeuroEphysAI-Setup-1.0.0.exe``。安装程序只安装到当前用户目录，不要求管理员权限，
并创建桌面和开始菜单快捷方式。卸载程序不会删除
``Documents\NeuroEphysAI`` 中的项目数据。

便携版 ``NeuroEphysAI-1.0.0-Windows-x64-portable.zip`` 无需安装。完整解压后启动
``NeuroEphysAI\NeuroEphysAI.exe``，不能只复制单独的 EXE。one-folder 结构让科学
计算依赖可以检查，启动时也无需反复解压。

安装版与便携版都在本机运行数据导入、质控、已有 sorting 导入、Unit 人工复核、
行为、统计、机器学习、Elephant、图表、AI 控制和教程。Kilosort4 所需 CUDA PyTorch
运行库有数 GiB，因此作为独立 GPU 组件管理，不在核心 App 中重复打包。Sorter 页面
显示实际状态，不会用其他 sorter 冒充 Kilosort。

首次打开后进入 **Sorter 管理**。该页面显示实际检测到的后端、版本、硬件要求、
适用探针和可运行状态。只有通过环境探测的后端才标记为可运行。

Python 包
-----------

正式 Python 发行物支持 64 位 Python 3.12。新建独立环境并安装 wheel：

.. code-block:: powershell

   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install neuroephys_ai-1.0.0-py3-none-any.whl
   .\.venv\Scripts\neuroephys.exe info

.. code-block:: python

   from pathlib import Path
   import neuroephys as ne

   project = ne.create_simulated_project(Path("example_project"))
   qc = ne.run_raw_qc(project)

``desktop``、``mountainsort`` 和 ``kilosort`` 是可选 extra。后两者分别需要兼容的
C++ 构建环境或 NVIDIA GPU/CUDA 环境，普通核心包安装不会被这些条件阻塞。

源码开发环境
------------

.. code-block:: powershell

   git clone https://github.com/CarbonLack/neuroflow-ai.git
   cd neuroflow-ai
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
   .\.venv\Scripts\python.exe app.py

处理自己的记录前先运行测试：

.. code-block:: powershell

   .\.venv\Scripts\python.exe -m pytest -q

Sorter 运行环境
---------------

Kilosort4 使用已安装的 Python/CUDA 环境。MountainSort5 和若干 SpikeInterface
sorter 可使用 CPU。NeuroEphys AI 记录用户选择的后端，并分别保留原生输出目录。
某个后端失败后会保留失败状态和真实日志，不会静默替换为其他 sorter。

开发者可用 ``scripts\build_release.ps1`` 构建便携 App、Python 包、安装程序和校验值；
``scripts\build_windows.ps1`` 保留给受管理的本机完整 GPU 构建。

.. warning::

   v1.0 正式支持范围是 64 位 Windows 10/11 与 Python 3.12。macOS、Linux 和其他
   Python 版本尚未列入本版正式兼容范围。
