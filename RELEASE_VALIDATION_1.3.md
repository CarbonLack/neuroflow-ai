# NeuroEphys AI v1.3 验收记录

## v1.3.0 多 Session／多动物 Study

验收范围：

- 合成的四 Session、两动物项目：可建立/保存/重新打开 Study；
- 不同 Session 使用不同 Unit 数量，确认 trial 特征不包含跨 Session Unit ID；
- 线性 SVM 按动物整组留出、置换、置信区间、混淆矩阵和英文图导出；
- 一只动物、三个 Session 时自动按 Session 留出，并明确不做动物层级推断；
- Logistic、线性/RBF SVM、收缩 LDA 和随机森林均使用注册参数；
- 条件 A/B 必须不同且为所有纳入 Session 共有；
- Python API、CLI、App 窄窗口、后台计算、AI 工具 schema 和脱敏 Study 摘要回归；
- 完整源码测试、文档构建和发布包自检结果在发布提交与 GitHub Actions 中保留。

本机源码验收：2026-09-17，`165 passed`；中英文 Sphinx 文档以 warning-as-error 模式
构建通过。pytest 结束时 Windows 临时目录清理出现既有的权限提示，但测试进程返回 0，
不影响 165 项结果。

Full 安装包验收：安装包在 D 盘空间不足后改到明确的 E 盘发布归档目录构建，未移动项目
源码或实验数据。`NeuroEphysAI-Setup-1.3.0-Full.exe` 为 2,086,977,353 字节，SHA256 为
`f2f49be7966e7a67f67b8ad622c3c06ed0088e73e1807ea41783a871a3632f8e`。安装到独立 E 盘
验收目录后，文件版本与产品版本均为 1.3.0；打包后启动、AI 安全桥、SVG/PDF/PNG 图导出、
MountainSort5、内置 sorter 集合和 Kilosort4 六项自检全部返回 0。

科学边界：这些自动测试验证软件实现和防泄漏约束，不代表任意实验设计都满足统计功效，
也不把模拟解码分数当成真实生物学结论。跨 Session 细胞匹配尚未提供；默认明确不匹配。
