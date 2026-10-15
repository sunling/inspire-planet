# 腾讯会议逐字稿 → 公开 Draft PR

- 先打通逐字稿拉取：Actions 只读取腾讯会议，写入本期 `transcript.txt` 和 `events/README.md` 索引。
- 不调用模型，不需要模型 API Key，不生成纪要、金句、文章、图片或发布包；没有内容生成 workflow。
- 后续整理可在 ChatGPT/Codex 中单独发起，继续使用同一 `content/YYYYMMDD-epXX` 分支；本自动化不会覆盖人工内容，不自动合并或发布。
- **Draft PR 不是私密空间**：原始转写、姓名和上下文会公开在分支上。启用 `draft` 前确认参与者授权、隐私与公开范围；保密会议不要使用此路线。

## 首次设置

1. 先 review 工具 PR 与无密钥 **Content CI**。生产入口必须先存在于默认分支，手动运行也只允许默认分支。**PR26 尚未合并时不能 dispatch 这个新 workflow**；本文不代表获准合并。
2. 在腾讯会议 [AI Skill 页面](https://meeting.tencent.com/ai-skill/)本人登录取得个人 MCP Token；不是 `tmeet` OAuth access/refresh token。
3. GitHub 仓库 Settings → Secrets and variables → Actions → **Secrets** → New repository secret，名称 `TENCENT_MEETING_TOKEN`。Token 只在 GitHub Secrets 输入，不发到聊天、Issue、PR、workflow 输入或日志；不要交给协作者代填。
4. 同页 **Variables** 可设置 `CONTENT_MEETING_SUBJECT`（完整精确标题）或 `CONTENT_MEETING_ID`。手动输入可覆盖对应变量；两种过滤条件同时设置时必须同时匹配。不要从历史文案或 `current.md` 猜会议号。
5. 仅创建公开 `draft` PR 时才需 Settings → Actions → General 中允许 **Allow GitHub Actions to create and approve pull requests**；这不是自动批准授权，本实现不批准 PR。目前此开关未开启，维护者按需设置；组织策略锁定时找管理员。`connectivity` / `fetch-check` 不需要开启它。

工作流显式申请 `contents: write` / `pull-requests: write`；不需要 PAT。checkout 不持久化凭据，Tencent Secret 只给读取步骤，GitHub Token 只给远端检查和提交步骤，不上传转写 artifacts。

## 按顺序检查

Actions → **Transcript draft** → Run workflow → 选择默认分支：

- `validate`（默认）：明确填写 `date` / `episode`；只验证已提交的本地转写，无服务调用、无写入。已有公开 EP40 可用 `2026-10-10` / `40`。
- `connectivity`：日期、期数可空。只调用 `tools/list` 验证鉴权与三个只读工具的参数 schema，不读取会议。成功不代表逐字稿接口已联调。
- `fetch-check`：明确填写日期、期数及精确标题或 ID（过滤器也可来自变量）。建议先用公开 EP40 的 `2026-10-10` / `40`，标题/ID 用本人确认的真实值。**即使已有本地转写也强制访问远程 MCP**，实际走会议、录制和完整转写分页；只缓存到 `.git/meeting-content-fetch-check.txt`，不替换已提交的 EP40，不提交、不推送、不创建 PR。日志只报发言块数，不打印正文、姓名或响应。
- `draft`：确认一个尚无逐字稿的新目标，明确日期、期数及过滤器；先幂等检查，再远程拉取、写入逐字稿与索引、校验、创建公开 Draft PR，最后回读状态与文件范围。

首次顺序：无密钥 CI / `validate` → 设置腾讯 Secret → `connectivity` → EP40 `fetch-check` → 确认新一期公开范围后 `draft`。不要把合成测试通过当成真实拉取通过。

## 每日排程：默认关闭

- 只有 Variable `CONTENT_AUTOMATION_ENABLED` 精确等于 `true` 才启用每日 **08:20 UTC** 的 `draft`；未设置或其他值均不执行。
- 必须显式设置 `CONTENT_EVENT_DATE=YYYY-MM-DD`（会议 UTC 日期）、`CONTENT_EPISODE=1–999` 及精确过滤器；每期确认后人工更新。手动任务需自行填写日期、期数，不借用排程目标。
- 每日只重试同一目标；不会任选账号最新会议，不会自动发现下一期、推进期数或按周推算日期。真实联调通过后再考虑开启。

## 幂等与失败恢复

- `prepare` 要求默认分支、干净工作区；目标 `transcript.txt` 已存在、远端同名分支已存在、或同 head/base 的任意状态 PR 已存在，均跳过。**不以 `summary.json` / `quote-cards.json` / 本期 README 判断是否拉取过**。
- 日期与期数固定目录 `events/{year}/{YYYYMMDD}-epXX` 和分支 `content/{YYYYMMDD}-epXX`，未来可由 Codex 在原分支追加整理稿；rerun 不重写、不重开已关闭 PR。
- 创建新计划先清除旧草稿缓存；检查用缓存与草稿缓存分开。生产顺序固定 `prepare → fetch → write → check-content → publish`。
- 原始转写用独占创建，已有文件绝不覆盖。仅提交本期 `transcript.txt` 与总索引，保留已有索引其他栏目；不创建空 README 或 JSON。
- 提交前复查基线 HEAD、检出分支、远端分支、所有改动与暂存区白名单。不 force push；推送后核对远端 SHA，创建 PR 后回读 Draft 状态、head/base 与精确文件范围。
- 分支已推送但建 PR 因权限失败时，重跑安全跳过。维护者检查已有分支，开启所需权限后从 GitHub compare 页面或 `gh pr create --draft --base main --head content/YYYYMMDD-epXX` 补 PR，不删分支重跑。
- 无匹配或多场匹配、schema 变化、缺少分页完成标志、循环/空续页、超过 200 页或 20000 段、超过 300000 字符或 HTTP 响应 8 MiB，均停止，不截断冒充全文。只在候选转写明确为空（含 30002）时尝试下一候选，不把分页/鉴权失败降级为短稿。
- 401 检查 Token/个人账号，403 检查权限；结构不兼容时核对官方 schema 后补测试，不猜字段或调用相似工具。原始服务错误与 CLI 输出隐藏；不要开启 `set -x`、`ACTIONS_STEP_DEBUG` 或打印响应。

## 本地校验与真实边界

```bash
python3 -m unittest discover -s scripts -p 'test_meeting_content.py' -v
python3 scripts/check-content.py
CONTENT_DATE=2026-10-10 CONTENT_EPISODE=40 python3 scripts/meeting_content.py validate
```

- 标准库实现，不安装或执行远程 Skill 包。`publish` 额外要求 `CONTENT_PUBLISH_ALLOWED=true` 与 `GITHUB_ACTIONS=true`，本地维护不要设置这两个发布开关。
- 只允许 `get_user_ended_meetings`、`get_records_list`、`get_transcripts_details`。固定 HTTPS endpoint 与请求头来自[腾讯官方 MCP 说明](https://meeting.tencent.com/support/topic/2233/index.html)及此前只读核对的官方 `@tencent-adm/tencent-meeting-mcp` 包；`X-Skill-Version` 固定为包内 config 的 `v1.0.15`，不声称最新版本。
- 参数以运行时官方 `tools/list` 为准；字段名、类型、必填参数不兼容即停止。列表目前只接受 `meeting_info_list` / `records` 加 `has_more`，转写接受 `minutes.paragraphs` 加 `more`。真实返回结构仍需维护者用 Token 联调；不兼容时安全停止。
- **目前未配置 Tencent Secret，真实鉴权和逐字稿读取尚未完成**；没有把未认证 401 或本地格式校验当作联调成功。
- 测试中的 MCP 与 GitHub PR 响应均明确为合成数据，不是真实会议或线上结果。独立集成测试实际执行临时本地 Git/bare 仓库的提交、推送与 SHA 回读，不写 GitHub、不把测试内容放进本仓库 events。本地通过不等于远程 CI 已通过。
