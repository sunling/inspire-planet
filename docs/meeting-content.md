# 会议转写：手动下载与归档

转写下载只在手动运行 GitHub Actions 时执行，已移除全部定时触发。下载成功后直接提交到公开仓库的 `main`，不创建 PR；运行前须确认该场转写可公开。

## 1. 手动下载最新会议

1. 打开 [Transcript download](https://github.com/sunling/inspire-planet/actions/workflows/meeting-content.yml)。
2. 点击 **Run workflow**，选择 `main` 并运行，无需填写参数。
3. 查看运行日志和 `main` 提交记录。最新会议已归档时正常跳过，不回退下载更早场次。

工作流需要有效的 `TENCENT_MEETING_TOKEN` Secret、`contents: write` 和 `pull-requests: read` 权限。原先的 `CONTENT_AUTOMATION_ENABLED` 变量不再使用，可以删除。

## 2. 下载结果与失败处理

期次可确认时写入 `events/`；期次不明时写入公开的 `incoming/meetings/`，待人工确认。不会生成文章、纪要或金句。

录制列表完整分页且同时匹配 `meeting_id` 和 `sub_meeting_id`，确认该场录制存在。优先读取该场会议元数据中明确标为“转写”的文件；文字转写 ID 可以与原生音视频 ID 不同，不要求两份列表相等。没有明确转写候选时才尝试该场原生文件。候选与其他场次归属冲突时停止；忽略空转写，选择完整正文最长的一份，并列且内容不同、文件重复、分页不完整或超出上限时停止。

转写未生成时稍后手动重试；凭据失效、权限不足或实例不明确时由维护者核对，不猜期数、不跨期取文件。

### 已归档会议也能做只读实测

打开 [Content CI](https://github.com/sunling/inspire-planet/actions/workflows/content-ci.yml)，点 **Run workflow**，在 `check_date` 填北京时间会议日期（EP42 为 `2026-10-24`）。测试分支尚未合入时选择 `codex/manual-transcript-check`，合入后选择 `main`。

`ep40-readonly` 是沿用的内部 job ID，实际读取日期以 `check_date` 为准。该步骤强制重新读取远程完整转写，不因已归档而跳过；随后与该日期唯一归档比较发言人、时间及忽略空白后的正文，日志仅显示段落数量与是否一致。内容不同会提示另行核对，不覆盖归档；读取失败则测试失败。全文只存 runner 临时缓存并始终清理；没有发布步骤，权限仅为读取。

## 3. 历史会议转写：查找或按日期补录

打开 [历史会议转写 · 查找与补录](https://github.com/sunling/inspire-planet/actions/workflows/meeting-history.yml)，点 **Run workflow**，在 **Use workflow from** 选择 `main`。

- **查找未归档会议**：操作选择 `查找未归档会议`（默认），日期留空，运行后在日志查看未归档会议的真实日期。此操作只扫描，不下载全文、不写入 main。
- **按日期补录**：操作选择 `按日期补录`，填写会议日期 `YYYY-MM-DD`（例如 `2026-09-26`），再选择**该日期所属的时区**：默认 `Asia/Shanghai`（北京时间），也可选择 `America/Los_Angeles`（美西时间）或 `UTC`。运行后如唯一匹配对应会议，会尝试将转写直接提交到 `main`。
- **提交后检查**：检查 `main` 上新增的转写、日期、来源、期次和公开范围；该工作流不创建 PR。

会议日期严格按**你选定的时区**解释，不会同时用多个时区猜测。同一当地日期有多场项目会议、没有匹配，或数据有歧义时，流程会停止，不会自动选择错误场次。

历史录制可能受 API 可用期限与旧录制归属限制；如失败请交由维护者核对。

## 4. 什么时候需要维护者？

如果手动运行持续无法下载、没有权限写入 main、匹配到错误会议或期次不明，请维护者检查仓库设置、凭据和工作流日志。**不要在 Issue、PR 或日志里粘贴 Token 或私人逐字稿。**

详细的会议实例匹配、去重、时间范围、授权门禁、旧记录边界、测试命令等见 [转写自动化技术维护说明](../scripts/meeting-content-technical.md)。

完成转写归档后，下一步是 [内容生成与审核](content-workflow.md)。

## 5. 回放视频与逐字稿一起准备

每期同时安排两份素材：带声音的回放视频与逐字稿。当前视频由用户从会议平台手动下载到被 Git 忽略的本地 `replays/`，转写按本文手动触发工作流下载；两者是独立操作，尚未实现一次运行同时获取。已有本期文件不重复下载，核对内容、日期和期数后再制作。

一份带声音的视频供播客和短视频切片共用，由本地工具读取音轨，无须另下载音频或预先分离音轨。完整优先级为播客制作、试听与发布，同时根据转写整理总结和金句；取得小宇宙单集链接后完成详情页，再生成公众号文章与视频切片，见 [内容制作说明](content-workflow.md)。

### 将来通过 Actions 暂存媒体的限制

当前脚本只下载转写，没有下载音视频，也没有上传媒体 artifact。腾讯会议的 `get_record_addresses` 支持获取录制下载地址，实际可用性取决于该场录制是否就绪和账号下载权限，需要单独接入并验证。

若以后经授权通过 Actions 暂存媒体，可用 `actions/upload-artifact` 的 `retention-days: 1` 设置一天保留期；这不限制下载时的峰值空间，也不删除用户已下载到本地的副本。媒体不提交 Git。公开仓库的 artifact 可被有仓库读取权限的登录用户下载，因此不能用一天保留期代替原声与肖像公开授权；私人录制优先直接下载到本地被忽略的 `replays/`。

大小应以实际文件或响应大小为准。仅作码率估算：两小时 64–128 kbps 音频约 58–115 MB；0.5–2 Mbps 视频约 450 MB–1.8 GB（十进制，不含额外开销）。一天保留不能避免当天占用超额。

参考：[腾讯会议 MCP 工具](https://meeting.tencent.com/support/topic/2233/index.html)、[artifact 保留期](https://github.com/actions/upload-artifact#retention-period)、[GitHub 存储额度](https://docs.github.com/en/billing/reference/product-usage-included)。
