# NeuroEphys AI 公开仓库与文档部署状态

最后检查日期：2026-07-29

## 公开范围

- GitHub 仓库：`https://github.com/CarbonLack/neuroflow-ai`
- GitLab 仓库：`https://gitlab.com/CarbonLack/neuroflow-ai`
- GitHub 操作手册：`https://carbonlack.github.io/neuroflow-ai/`
- 已发布的独立操作手册：`https://carbonlack.github.io/neuroephys-ai-docs/`
- GitLab 操作手册目标地址：`https://carbonlack.gitlab.io/neuroflow-ai/`

GitHub 和 GitLab 仓库均设置为公开。公开仓库只包含程序源代码、公开教程、测试和脱敏演示资源。王淑霏真实数据、原始文件路径、私有运行项目和大体积派生文件不进入公开仓库。

## GitHub Pages

GitHub Pages 使用 `.github/workflows/pages.yml` 发布 `docs/site`。仓库的 Pages 来源已经设置为 **GitHub Actions**，与工作流声明保持一致。

此前失败现象：

- `actions/configure-pages` 返回 `Resource not accessible by integration`。

原因：

- 仓库 Pages 来源仍是旧的“Deploy from a branch”，而提交中的工作流按 GitHub Actions Pages 方式发布。

处理：

- 在仓库 `Settings > Pages > Build and deployment` 中把 Source 改为 `GitHub Actions`。
- 保留最小权限：`contents: read`、`pages: write`、`id-token: write`。
- 通过后续提交重新触发发布。

## GitLab Pages

GitLab Pages 使用 `.gitlab-ci.yml` 把 `docs/site` 复制到 `public`，并使用当前 GitLab Pages 语法 `pages: true` 声明发布作业。

此前失败现象：

- Pipeline 创建后立即失败。
- 页面显示 `0 jobs`。
- GitLab 显示提示：`Before you can run pipelines, we need to verify your account.`

原因：

- GitLab.com 在创建 Runner 作业前要求账户所有者完成身份验证。该拦截发生在作业启动前，与 NeuroEphys AI 分析代码无关。
- 原配置同时使用了已弃用的旧式 `pages` 作业名，现已升级。

处理：

- 作业改名为 `deploy-pages`。
- 增加 `pages: true`。
- 每次 `main` 分支提交均可触发发布，避免首次验证后还要制造额外文档改动。
- 账户所有者完成 GitLab 身份验证后，重新运行最新 Pipeline 即可。

## 上传边界

以下内容上传到两个公开仓库：

- 源代码和测试；
- GitHub/GitLab Pages 配置；
- 中英文公开操作手册；
- 公开方法来源与开源归属说明；
- 脱敏产品截图；
- 可复现构建配置。

以下内容保留在本机：

- 未公开真实电生理和行为数据；
- 含本机原始路径的验证项目；
- 真实数据派生的大体积缓存和 sorting 输出；
- 约 4.7 GiB 的 Windows 解压式应用目录。

本地应用可依据仓库中的 `NeuroEphysAI.spec` 和依赖锁定信息重复构建。大体积安装产物应通过正式 Release、对象存储或比赛指定渠道发布，不能直接塞入普通 Git 历史。
