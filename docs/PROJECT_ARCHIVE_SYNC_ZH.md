# `codex_neuroephys_ai` 项目总档案维护规则

`D:\PhD\AI大赛\codex_neuroephys_ai` 是 NeuroEphys AI 的长期总入口和灾难恢复索引，
不是一次性交接文件夹。

## 哪些内容会实时变化

其中的源码、发布、数据项目、验证结果和论文复现目录均使用 Windows 目录链接指向
权威位置。因此源目录新增文件或结果时，总档案入口会立即可见，不再复制数 GB 数据。

`01_源代码\neuroflow-ai` 也是指向权威 Git 仓库的目录链接，所以并不存在
“保障目录中另一份源码过期”的问题。

## 哪些内容需要刷新

版本号、Git 提交、测试数量、GitHub Release 和本次功能摘要属于“状态快照”，需要在
每次功能提交和正式发布后刷新。仓库提供：

```powershell
.\scripts\update_project_archive.ps1 `
  -ReleaseStatus "released" `
  -TestSummary "169 passed; bilingual docs passed"
```

当前开发电脑已启用仓库的 `.githooks`：Git 提交、切换或合并后自动更新
状态快照；`build_release.ps1` 打包成功后也会自动更新。在新电脑克隆后，
只需执行一次：

```powershell
git config core.hooksPath .githooks
```

如果新电脑不存在该 D 盘保障目录，同步脚本会安全跳过，不会阻断 Git 操作或发布构建。

脚本更新：

- `项目动态快照.txt`；
- `04_分析与验证\当前版本验收.md`；
- `06_文档与交接\当前版本变化.md`。

它不会复制、移动或删除实验数据，也不会更改现有项目路径。旧的带日期状态文件保留为
历史记录；日常查看应以 `项目动态快照.txt` 为准。
