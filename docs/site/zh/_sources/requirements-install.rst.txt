系统要求与安装
==============

硬件需求由准备运行的任务决定。打开项目、检查图表和导入已处理 spike 时间所需资源
较少；长时间高密度记录的 sorting 会消耗更多内存、磁盘和计算资源。

实用起步配置
------------

* 当前打包开发预览版面向 Windows 10/11。
* 短教学数据建议 16 GB 内存；常规多通道工作建议 32 GB 或更高。
* 磁盘需同时容纳原始记录、标准缓存、sorter 原生输出和导出结果。
* Kilosort4 需要受支持的 NVIDIA GPU。CPU sorter 通过环境探测后也可选择。

下载开发预览版
--------------

从 GitHub 的 **Releases** 页面下载最新预发布压缩包，解压到可写的本地文件夹，然后
启动 ``NeuroEphysAI.exe``。当前采用 one-folder 形式，科学计算依赖可以直接检查，
启动时也无需反复解压。

公开压缩包是便携核心预览版。数据导入、质控、已有 sorting 导入、Unit 人工复核、
行为、统计、机器学习、Elephant、图表、AI 控制和教程均在本机运行。Kilosort4 所需
的 CUDA PyTorch 运行库有数 GiB，因此由仓库的完整分析环境提供，不在核心压缩包中
重复打包。Sorter 页面显示实际状态，不会用其他 sorter 冒充 Kilosort。

首次打开后进入 **Sorter 管理**。该页面显示实际检测到的后端、版本、硬件要求、
适用探针和可运行状态。只有通过环境探测的后端才标记为可运行。

开发环境安装
------------

.. code-block:: powershell

   git clone https://github.com/CarbonLack/neuroflow-ai.git
   cd neuroflow-ai
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
   .\.venv312\Scripts\python.exe app.py

处理自己的记录前先运行测试：

.. code-block:: powershell

   .\.venv312\Scripts\python.exe -m pytest -q

Sorter 运行环境
---------------

Kilosort4 使用已安装的 Python/CUDA 环境。MountainSort5 和若干 SpikeInterface
sorter 可使用 CPU。NeuroEphys AI 记录用户选择的后端，并分别保留原生输出目录。
某个后端失败后会保留失败状态和真实日志，不会静默替换为其他 sorter。

开发者可用 ``scripts\build_windows.ps1`` 构建本机完整 GPU 包，用
``scripts\build_windows_lite.ps1`` 构建较小的公开核心预览包。

.. warning::

   打包预览版已经在开发工作站上运行。干净 Windows、macOS 和 Linux 机器的完整
   兼容矩阵仍在验证中。
