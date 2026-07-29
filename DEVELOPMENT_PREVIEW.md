# NeuroEphys AI development preview

## Download package and full analysis environment

The GitHub Windows archive is the portable core preview. It contains the
desktop application, data import, quality control, existing-sorting import,
Unit curation, behavior alignment, statistics, machine learning, Elephant,
figure editing, AI controls, and the bilingual manual. CPU-oriented sorters
remain available when their packaged dependencies pass the environment check.

Kilosort4 requires a large CUDA-enabled PyTorch runtime. To keep the public
download practical, that runtime is installed through the managed full
analysis environment instead of being duplicated inside the core archive. The
Sorter page reports the installed state and never substitutes another sorter.
The repository build script `scripts/build_windows.ps1` creates the full local
GPU package; `scripts/build_windows_lite.ps1` creates the downloadable core
preview.

The public preview is built from `requirements-core.txt`. Source users who
need the complete local sorter stack use `requirements.txt` and verify GPU,
driver, CUDA, and PyTorch compatibility before sorting.

## Current purpose

This build is distributed for workflow demonstration, compatibility testing,
scientific review, and user feedback. It is an evolving prototype.

## What a tester may do

- Create a local project and run the supplied teaching simulations.
- Import supported recordings or existing sorting results.
- Inspect deterministic analysis, curation, statistics, decoding, figures, and
  provenance.
- Configure an optional AI provider after reviewing the outbound data preview.
- Report reproducible problems through GitHub Issues.

## Important limits

- Candidate units require manual review.
- Real-data validation covers specific recordings and computer environments; it
  is not a universal device or operating-system certification.
- AI output is advisory and cannot establish a scientific conclusion.
- The application does not restore low-frequency information removed during
  acquisition.
- Back up original data and projects independently.

## Data and redistribution

The public repository and release do not include private laboratory recordings,
personal information, API credentials, or local validation paths. Public test
datasets retain their original terms and identifiers. Third-party components
retain their own licenses; see `THIRD_PARTY_SOURCES.md`.

This preview is provided for evaluation and research testing. Contact the
development team before redistributing a modified bundle or using the product
commercially.

---

# NeuroEphys AI 开发预览版说明

## 当前用途

本版本用于工作流展示、兼容性测试、科学审阅和用户反馈，仍在持续开发。

## 测试者可以完成

- 新建本地项目并运行随附教学模拟；
- 导入已支持的记录或已有 sorting 结果；
- 检查确定性分析、人工复核、统计、解码、图表和溯源记录；
- 查看发送字段后配置可选 AI Provider；
- 通过 GitHub Issues 提交可复现问题。

## 重要限制

- 候选 Unit 仍需人工检查；
- 真实数据验证只覆盖明确记录和计算环境；
- AI 输出仅供辅助判断；
- 采集时被滤除的低频信息无法恢复；
- 原始数据和项目仍需独立备份。

公开仓库和发布包不含实验室私有记录、个人信息、API 密钥和本地验证路径。公开数据
保留原始使用条款和编号，第三方组件保留各自许可证，详见
`THIRD_PARTY_SOURCES.md`。
