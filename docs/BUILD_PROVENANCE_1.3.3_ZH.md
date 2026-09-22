# v1.3.3 本机封装来源记录

构建机：Windows 11，Python 3.12，NVIDIA RTX 3080。标准版与完整 GPU 版均在
`D:\PhD\AI大赛\codex_neuroephys_ai` 内构建，安装包由 Inno Setup 6.7.3 编译。

首次尝试从 PyTorch 官方 cu128 索引下载 `torch 2.11.0+cu128` 时，下载中断且
pip 校验 SHA256 不符；该下载产物**没有安装，也没有进入发布包**。随后从本项目
先前已验收的 v1.3.2 Full 便携版中复用完全同版本的 `torch` 程序目录，复制到
本项目管理的构建环境。复用前后 `torch_cuda.dll` SHA256 相同：

`d5ca93bdf3e246af9c962ec92554e5576dec03b665f9cbf1c664e653f76ddb50`

构建环境的 `torch.__version__` 为 `2.11.0+cu128`，本机实际返回
`torch.cuda.is_available() == True`，识别 NVIDIA GeForce RTX 3080。完整发行版
还须通过打包后 Kilosort4 自检；单靠文件存在或 CUDA 可见不能构成通过证据。

这种复用**只用于同一项目、同一版本的本机恢复构建**，不是推荐给用户的 PyTorch
安装方式。其他机器应安装官方相容的 CUDA/PyTorch wheel，或直接使用经验证的
Full 安装包。最终文件尺寸与哈希以发布目录的 `SHA256SUMS.txt` 为准。

机构 Harness 的 `dsh` 启动器在本机返回 NVM4306；AI 图像协议已通过模拟服务
测试，但没有声称实际机构模型完成了看图调用。此限制与 App 的 CPU/GPU 排序
自检相互独立。
