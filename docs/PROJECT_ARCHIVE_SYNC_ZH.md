# `codex_neuroephys_ai` 长期项目档案维护规则

`D:\PhD\AI大赛\codex_neuroephys_ai` 是 NeuroEphys AI 的长期项目档案和灾难恢复入口。
自 v1.3.1 后，它不再采用中文分类目录或目录链接，而是使用全英文目录、真实备份文件和
可审计的外部位置清单。

## 档案中实际保存什么

- `01_Source_Code/CURRENT_SOURCE_SNAPSHOT.zip`：当前 Git 提交的完整已跟踪源码快照；
- `01_Source_Code/FULL_GIT_HISTORY.bundle`：经过校验的完整 Git 历史、分支和标签；
- 当前版本发布说明、验收报告、用户文档、开发文档和交接资料的真实副本；
- 大型原始数据、分析项目、安装包和验证工作区的英文索引、路径与校验信息；
- `CURRENT_STATUS.txt`、`SYNC_MANIFEST.json` 和带 SHA-256 的文件清单。

档案内部不包含 junction、symbolic link 或 `.lnk` 快捷方式。因此，打开档案时看到的源码
快照、Git bundle、报告和说明都是真实文件，不会因为原目录消失而变成失效入口。

## 为什么大型数据不再次复制到 D 盘

D 盘空间有限，而原始电生理数据、处理项目、完整安装包和 GPU 运行环境可能占用数百 GB。
盲目复制不仅会耗尽磁盘，也会产生多个无法判断新旧的副本。因此，大型内容保留在权威位置，
由 `07_Backup_Manifests/EXTERNAL_LOCATIONS.csv` 统一记录。源码和 Git 历史体积较小且最关键，
所以会实际备份到档案中。

## 自动刷新

以下动作会运行 `scripts/update_project_archive.ps1`：

- Git commit；
- Git checkout；
- Git merge / pull；
- 正式版本构建完成。

新电脑克隆仓库后，执行一次：

```powershell
git config core.hooksPath .githooks
```

也可以随时手工刷新：

```powershell
.\scripts\update_project_archive.ps1
```

## 如何判断是否为最新

依次检查：

1. `CURRENT_STATUS.txt` 的版本、提交号和刷新时间；
2. `01_Source_Code/SOURCE_VERSION.txt` 的提交号；
3. `SYNC_MANIFEST.json` 的 `commit`；
4. `07_Backup_Manifests/SYNC_HISTORY.log` 的最后一行；
5. 当前仓库 `git rev-parse HEAD` 是否与上述提交号相同。

这套结构的目标是：不依赖聊天记录、不依赖快捷方式、不重复大型数据，仍能完整恢复源代码，
并能准确定位每一批数据、项目、发布包和验证证据。
