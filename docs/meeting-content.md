# 会议转写：自动下载与人工归档

启发星球的会议转写由 GitHub Actions **定时尝试下载**，并在发现新会议时尝试创建待审核的 Draft PR。日常不需要填写日期、期数或手动运行。**Draft PR 需要人工确认后才能合并**，不会自动发布文章、金句或图卡。

## 1. 日常自动下载

- **计划时间**：北京时间每周六 **10:00、10:10、10:20** 各尝试一次，给腾讯会议生成转写留出时间；GitHub 定时任务可能延迟。
- **运行条件**：默认分支上的工作流、仓库变量 `CONTENT_AUTOMATION_ENABLED=true`、有效的 `TENCENT_MEETING_TOKEN`，以及允许 GitHub Actions 创建 Pull Request 的仓库设置。
- **查看结果**：[Transcript draft](https://github.com/sunling/inspire-planet/actions/workflows/meeting-content.yml) → 选择最新运行查看状态；发现新内容时到 [Pull requests](https://github.com/sunling/inspire-planet/pulls) 查找对应 Draft PR。已归档的会议会跳过，不重复开 PR。
- **人工审核**：核对会议日期、期次、转写内容和公开授权。期次不确定时，稿件可能暂放 `incoming/meetings/` 等待确认；审核无误再合并。

> **权限提醒**：2026-10-15 的检查记录显示，仓库中 Actions 创建 PR 的设置为关闭状态。**尚未确认已恢复**，因此即使定时下载步骤成功，也不能保证自动建 Draft PR。仓库维护者应检查 **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests**，并确认所需权限与变量已正确配置。不要把这一历史记录当作当前实时状态。

## 2. 必要时手动运行

如果该周没有自动执行，或转写尚未生成：

1. 打开 [Transcript draft](https://github.com/sunling/inspire-planet/actions/workflows/meeting-content.yml)。
2. 点击 **Run workflow**，选择 `main` 并运行；**无需填写任何参数**。
3. 查看运行日志和是否新建 Draft PR。若最新会议已经归档，正常结果是跳过。

若工作流失败，先查看报错：常见原因包括转写未就绪、凭据失效、自动建 PR 的权限关闭、会议期次无法确认等；不要自行猜测期数或手动上传未获授权的转写。

## 3. 历史会议转写：查找或按日期补录

打开 [历史会议转写 · 查找与补录](https://github.com/sunling/inspire-planet/actions/workflows/meeting-history.yml)，点 **Run workflow**，在 **Use workflow from** 选择 `main`。

- **查找未归档会议**：操作选择 `search`（默认），日期留空，运行后在日志查看未归档会议的真实日期。此操作只扫描，不下载全文、不创建 PR。
- **按日期补录**：操作选择 `by_date`，填写会议日期 `YYYY-MM-DD`（例如 `2026-09-26`），再选择**该日期所属的时区**：默认 `Asia/Shanghai`（北京时间），也可选择 `America/Los_Angeles`（美西时间）或 `UTC`。运行后如唯一匹配对应会议，会尝试生成 Draft PR。
- **人工审核**：到 **Pull requests** 检查日期、来源、期次和公开范围，再决定是否合并。

会议日期严格按**你选定的时区**解释，不会同时用多个时区猜测。同一当地日期有多场项目会议、没有匹配，或数据有歧义时，流程会停止，不会自动选择错误场次。

历史录制可能受 API 可用期限与旧录制归属限制；如失败请交由维护者核对。

## 4. 什么时候需要维护者？

如果定时任务没有触发、持续无法下载、没有权限创建 PR、匹配到错误会议或期次不明，请维护者检查仓库设置、凭据和工作流日志。**不要在 Issue、PR 或日志里粘贴 Token 或私人逐字稿。**

详细的会议实例匹配、去重、时间范围、授权门禁、旧记录边界、测试命令等见 [转写自动化技术维护说明](../scripts/meeting-content-technical.md)。

完成转写归档后，下一步是 [内容生成与审核](content-workflow.md)。
