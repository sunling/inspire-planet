# 会议转写：自动下载与人工归档

启发星球的会议转写由 GitHub Actions **定时尝试下载，并直接提交到公开仓库的 `main` 分支**；不创建 PR。日常不需要填写日期、期数或手动运行。运行成功后转写、实例信息和索引立即公开；流程不会生成文章、金句或图卡。

## 1. 日常自动下载

- **计划时间**：北京时间每周六 **10:07、10:17、10:27、11:07** 各尝试一次；11:07 为会议延长或转写处理延迟提供兜底。GitHub 定时任务仍可能延迟。
- **运行条件**：默认分支上的工作流、有效的 `TENCENT_MEETING_TOKEN`，以及 GitHub Actions 的 `contents: write`（直接提交）和 `pull-requests: read`（检查现有草稿以免重复）权限。定时运行还要求仓库变量 `CONTENT_AUTOMATION_ENABLED=true`；在默认分支手动运行不受这个定时开关限制，仍须先确认转写可公开。
- **查看结果**：[Transcript download](https://github.com/sunling/inspire-planet/actions/workflows/meeting-content.yml) → 查看最新运行和 `main` 提交记录。新转写写入 `events/` 或 `incoming/meetings/`。定时任务仅考虑**北京时间当周六开始且已结束**的会议；新会议尚未结束时不会自动选择上周未归档的稿件。已归档的会议会跳过，不重复提交。
- **期次核对**：核对会议日期和期次。期次不确定时，转写会写入 `incoming/meetings/` 等待后续整理。由于文件直接进入公开 `main`，运行工作流前需确认转写可公开；本流程没有 PR 审核门槛。

> **写入权限**：工作流需要 `contents: write` 才能直接提交到 `main`，以及 `pull-requests: read` 用于检查现有草稿；不需要创建 PR 的权限或仓库设置。

## 2. 必要时手动运行

如果该周没有自动执行，或转写尚未生成：

1. 打开 [Transcript download](https://github.com/sunling/inspire-planet/actions/workflows/meeting-content.yml)。
2. 点击 **Run workflow**，选择 `main` 并运行；**无需填写任何参数**。
3. 查看运行日志与 `main` 提交记录。若最新会议已经归档，正常结果是跳过。

若工作流失败，先查看报错：常见原因包括转写未就绪、凭据失效、main 写入权限不足、会议期次无法确认等；不要自行猜测期数或手动上传未获授权的转写。

## 3. 历史会议转写：查找或按日期补录

打开 [历史会议转写 · 查找与补录](https://github.com/sunling/inspire-planet/actions/workflows/meeting-history.yml)，点 **Run workflow**，在 **Use workflow from** 选择 `main`。

- **查找未归档会议**：操作选择 `查找未归档会议`（默认），日期留空，运行后在日志查看未归档会议的真实日期。此操作只扫描，不下载全文、不写入 main。
- **按日期补录**：操作选择 `按日期补录`，填写会议日期 `YYYY-MM-DD`（例如 `2026-09-26`），再选择**该日期所属的时区**：默认 `Asia/Shanghai`（北京时间），也可选择 `America/Los_Angeles`（美西时间）或 `UTC`。运行后如唯一匹配对应会议，会尝试将转写直接提交到 `main`。
- **提交后检查**：检查 `main` 上新增的转写、日期、来源、期次和公开范围；该工作流不创建 PR。

会议日期严格按**你选定的时区**解释，不会同时用多个时区猜测。同一当地日期有多场项目会议、没有匹配，或数据有歧义时，流程会停止，不会自动选择错误场次。

历史录制可能受 API 可用期限与旧录制归属限制；如失败请交由维护者核对。

## 4. 什么时候需要维护者？

如果定时任务没有触发、持续无法下载、没有权限写入 main、匹配到错误会议或期次不明，请维护者检查仓库设置、凭据和工作流日志。**不要在 Issue、PR 或日志里粘贴 Token 或私人逐字稿。**

详细的会议实例匹配、去重、时间范围、授权门禁、旧记录边界、测试命令等见 [转写自动化技术维护说明](../scripts/meeting-content-technical.md)。

完成转写归档后，下一步是 [内容生成与审核](content-workflow.md)。
