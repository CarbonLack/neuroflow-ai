# NeuroEphys AI 公开仓库与文档部署状态

最后检查日期：2026-08-17

## 本轮发布范围

- GitHub 仓库：`https://github.com/CarbonLack/neuroflow-ai`
- 中文手册：`https://carbonlack.github.io/neuroflow-ai/zh/`
- English manual: `https://carbonlack.github.io/neuroflow-ai/en/`
- Windows 正式版 1.0：通过 GitHub Releases 发布安装版和便携版
- Python 正式版 1.0：提供 wheel 和源码包

本轮只更新 GitHub。GitLab 仓库和 GitLab Pages 暂不推送，待账户验证与发布流程单独处理。

## 公开内容

公开仓库包括：

- 源代码与自动化测试；
- GitHub Pages、Windows 正式版和 Python 包构建配置；
- 中英文操作手册；
- 开源依赖、方法文献与授权来源；
- 脱敏产品截图和教学模拟资源；
- 不含身份信息和本机路径的验证摘要。

以下内容保留在本机：

- 未公开的原始电生理和行为数据；
- 含本机原始路径的项目文件与运行日志；
- 真实数据产生的大体积缓存、波形和 sorting 输出；
- API 密钥和操作系统凭据；
- 仅供内部复核的派生结果。

## GitHub Pages

`.github/workflows/pages.yml` 会在 `main` 分支更新后执行：

1. 安装文档依赖；
2. 从 `docs/sphinx/en` 和 `docs/sphinx/zh` 构建双语 Sphinx 手册；
3. 将 `docs/site` 上传为 Pages artifact；
4. 发布到 GitHub Pages。

仓库的 `Settings > Pages > Build and deployment > Source` 应设置为 **GitHub Actions**。

## Windows 与 Python 正式版 1.0

`.github/workflows/release.yml` 构建公开核心版。Windows 发行物包括逐用户安装程序和完整便携 ZIP，均内置 Python 与核心科学运行环境；Python 发行物包括 `neuroephys-ai` wheel 和源码包。该版本包含桌面界面、数据导入、质控、sorting 结果导入、Unit curation、行为与事件分析、统计、机器学习、Elephant、出图和受控 AI 接口。

Kilosort/CUDA 运行环境体积较大，并受显卡、驱动和 PyTorch 版本约束，因此由独立的完整分析环境管理。公开核心版不会把缺失的 Kilosort 悄悄替换成其他 sorter。

## 数据与来源边界

任何真实数据进入公开材料前都必须完成：

1. 移除姓名、动物编号、原始文件名和本机路径；
2. 仅保留解释软件行为所需的汇总指标；
3. 标注数据授权状态与方法来源；
4. 人工复核截图、日志、报告和压缩包；
5. 扫描 API 密钥、访问令牌和凭据模式。

大体积安装包通过 GitHub Releases 或比赛指定渠道发布，不写入普通 Git 历史。发布前按 `RELEASE_VALIDATION_1.0.md` 完成安装、启动、核心流程、Python 包和卸载验收。
