# 腾讯会议 → JSON → 公开 Draft PR（第一版）

只处理 `transcript.txt`、`summary.json`、`quote-cards.json`、本期 `README.md`（导航与折叠溯源）、`events/README.md` 索引。不生成图片、文章或发布包，不改站点，不自动合并。

**Draft PR 不是私密空间。** 这个方案会把未经人工审阅的转写、姓名、上下文和 JSON 推到公开分支。维护者已选择公开草稿路线，但启用前仍应确认参与者同意这一级公开范围；不要用于含凭据、保密会议或不允许公开的资料。模型供应商也会接收完整转写，请检查其数据政策。合并到 `main` 后网站会读取正式 JSON，合并前必须人工审核。

## 首次设置

1. 先 review 工具分支与 **Content CI**；合并工具后，生产自动化只从默认分支执行。手动运行时也必须选择默认分支；不能通过 feature branch 运行带密钥的任务。
2. 仓库 Settings → Actions → General：允许 Actions；Workflow permissions 中允许 **Allow GitHub Actions to create and approve pull requests**。这个开关目前尚未开启，创建 PR 前需要维护者手动启用；本实现不会修改仓库设置，也不会批准 PR。组织策略若锁定该项，需要管理员处理。工作流显式申请 `contents: write`、`pull-requests: write`，不需要 PAT，不把模型/Tencent Token 给 GitHub CLI。
3. 在 Settings → Secrets and variables → Actions 设置下表。秘密只放 **Secrets**，不要粘贴到 Issue、PR、聊天、输入框或日志。生产不安装、不执行远程 Skill 包代码，Python 标准库即可。

| 类型 | 名称 | 含义 |
|---|---|---|
| Secret | `TENCENT_MEETING_TOKEN` | 在腾讯会议 AI Skill 页面本人登录后取得；不是 `tmeet` OAuth access/refresh token。只给读取转写/连接检测步骤 |
| Secret | `CONTENT_LLM_API_KEY` | 模型供应商密钥；只给生成步骤 |
| Variable | `CONTENT_LLM_BASE_URL` | 用户指定的 OpenAI-compatible **HTTPS API 根地址**，例如供应商提供的 `/v1` 根路径；脚本追加 `/chat/completions`。不允许 URL 用户名/密码、query、fragment，不跟随重定向 |
| Variable | `CONTENT_LLM_MODEL` | 供应商实际支持的模型 ID；没有默认模型。须支持 chat completions、JSON object 输出和完整输入上下文 |
| Variable | `CONTENT_MEETING_SUBJECT` | **精确**匹配完整会议标题；不是模糊词或正则 |
| Variable | `CONTENT_MEETING_ID` | 可代替标题；同时设置时两个条件都必须匹配。周期会议还须用 UTC 日期区分场次 |
| Variable | `CONTENT_EVENT_DATE` | 排程目标会议 **UTC 日期** `YYYY-MM-DD` |
| Variable | `CONTENT_EPISODE` | 该目标期的期数 `1`–`999` |
| Variable | `CONTENT_AUTOMATION_ENABLED` | 只有精确的 `true` 开启 schedule；未设置/其他值均关闭。手动检查不受此开关限制 |

**不要根据 `current.md` 或历史周次推测时间、期数或固定会议号。** 第一版排程采用显式目标日期和期数：每次确认新一期后更新两个变量。周六 06:20 UTC 首次尝试、每天 08:20 UTC 重试同一目标；不会按“账号任意最新会议”推断下一期。未更新目标时只会幂等跳过已有草稿，不会自动推进期数。这是保守的一期一目标实现，不是自动发现所有未来活动。

不要把 Token 放到 workflow/job 全局 env。checkout 不持久化 GitHub 凭据；GitHub Token 只给远端检查和 Draft PR 步骤；腾讯和模型密钥不在同一步。生产任务没有 `pull_request` / `pull_request_target` 触发器。独立 CI 可从 feature push 和 PR 运行，不读取 secrets。

## 手动验证与启用顺序

Actions → **Meeting content draft** → Run workflow，选择默认分支。

| mode | 其他输入 | 实际行为 |
|---|---|---|
| `validate`（默认） | `source=local`，明确 date/episode | 免费校验目标期已经提交的转写，零服务调用、零生成、零提交。可用已有 2026-10-10 / 40 验证格式，不会覆盖该期 |
| `connectivity` | date/episode 可空 | 只调用 Tencent `tools/list`，校验鉴权与需要的只读参数 schema；不读取会议，不调用模型，不提交。成功不等于转写适配已实测 |
| `generate-check` | 明确 date/episode，local 或 mcp | 检查远端幂等 → 取完整转写 → **一次付费模型调用** → 严格溯源/格式检查 → check-content。只在临时 runner 生成，不推送、不创建 PR，不上传转写 artifacts，runner 结束后文件销毁 |
| `draft` | 明确 date/episode，local 或 mcp | 相同步骤后创建公开 Draft PR，并回读确认 Draft 状态、分支、文件范围。无图、无合并、无社交发布 |

`local` 只使用目标目录已存在的 `transcript.txt`，无需 Tencent Token。`mcp` 没有本地转写时按当天 UTC 时间窗口列出已结束会议，叠加上述精确过滤条件，**必须唯一匹配**；0 或多场均停止。已有目标期转写保持原文，不润色、不覆盖。

第一次真实运行建议：无密钥 CI → `validate` → 设置腾讯 Secret → `connectivity` → 明确一个没有现成 JSON/README 的新目标 → 设置模型供应商并用 `generate-check` 验证（会收费）→ 检查日志通过后 `draft`。`generate-check` 不保留结果，随后 `draft` 会重新调用模型；不想支付两次可直接用公开 `draft` 人工审阅。只有完成真实验证后再把 `CONTENT_AUTOMATION_ENABLED` 设为 `true`。

本地维护可运行以下无网络命令：

```bash
python3 -m unittest discover -s scripts -p 'test_meeting_content.py' -v
python3 scripts/check-content.py
CONTENT_SOURCE=local CONTENT_DATE=2026-10-10 CONTENT_EPISODE=40 python3 scripts/meeting_content.py validate
```

脚本的 `publish` 还要求显式 `CONTENT_PUBLISH_ALLOWED=true` 与 `GITHUB_ACTIONS=true`，日常本地不会意外推送。生产阶段固定按 `prepare → fetch → generate → check-content → publish` 顺序执行；临时计划与转写缓存放 `.git/`，不会被提交或上传。

## 幂等、失败与恢复

- 分支固定为 `content/{YYYYMMDD}-epXX`，事件目录由 **UTC 日期＋年份＋期数**确定，跨年不会只按 EP 关联。
- 准备阶段先确认当前分支就是默认分支、工作区干净，再检查远端分支及该 head/base 的全部状态 PR。远端有草稿分支、已有 PR（包括已关闭）、或者目标期已有 `summary.json`、`quote-cards.json`、`README.md` 任一文件，均跳过，不调用模型、不覆盖人工稿。
- 调用模型前再次检查远端分支和目标内容。所有排程/手动运行共用 concurrency 锁，且不取消运行中的生成，避免同时收费。同一个开放 PR 的 rerun 不会重复生成或重复收费。
- 推送前再确认基线 HEAD、检出分支、所有变更和暂存区；仅允许本期上述 4 个文件与总索引。Git push 不使用 force。创建 PR 后回读状态和文件范围，**不会把“命令返回 0”直接当作成功**。
- 若分支已推送、创建 PR 因仓库开关/权限失败，重跑会安全跳过并避免再付模型费。维护者检查远端已有分支内容，开启上述 PR 开关后，用 GitHub compare 页面或 `gh pr create --draft --base main --head content/YYYYMMDD-epXX` 手动补 PR；不要删分支后盲目重新生成。
- 已关闭 PR 不自动重开，人工修订请在原分支进行。第一版不支持覆盖/刷新已有稿件。
- 模型调用不自动重试。中途失败且尚无远端分支时，后续重新运行可能再次收费；这是可重跑，不是跨崩溃的计费 exactly-once 保证。
- 遇到未支持的 schema/响应结构、缺少分页完成标志、循环/空续页、超过 200 页/20000 段、转写超过 300000 字符、HTTP 响应超过 8 MiB、模型 `finish_reason` 非 `stop`，均停止，绝不截断后当全文。最长候选为空或明确 30002 空内容时才尝试下一个；中途分页失败、鉴权失败不降级为短稿。
- 每个输出非空内容字段都需要有效原文摘录与段落编号；未知发言人、无效 JSON、错期次、无依据摘录、金句原文或归属不符均拒绝。第一版金句只允许同一发言块逐字摘录（可规范空白标点），比人工编辑 skill 更保守。证据存在不代表模型的语义总结必然正确；事实、隐私与同意范围仍必须人工审阅。
- HTTP/CLI 原始错误、响应正文、转写和密钥不进入日志；只有静态诊断和数字状态码。排障时不要开启 `set -x`、`ACTIONS_STEP_DEBUG` 或公开打印服务响应。401 先检查 Token/个人账号，403 检查权限；schema 不支持时核对官方 `tools/list` 后修改适配并补测试，不猜工具或字段。

## MCP 来源、协议与尚未验证的部分

实际读取并交叉核对的来源：

- [腾讯官方 MCP 说明文档](https://meeting.tencent.com/support/topic/2233/index.html)：确认远程云端 MCP、Python 代理、`X-Tencent-Meeting-Token` / `X-Skill-Version` 请求头，以及 `get_user_ended_meetings`、`get_records_list`、`get_transcripts_details` 等工具名称；手册指出完整参数以 `tools/list` 为准。
- [腾讯 AI Skill 入口](https://meeting.tencent.com/ai-skill/) 及其页面 chunk：安装描述由登录后的 `find_personal_mcp_info` 提供；未登录请求返回 401，没有绕过登录或取得个人 Token。
- SkillHub 的 `@tencent-adm/tencent-meeting-mcp` 包：通过 `https://api.skillhub.cn/api/v1/download?slug=%40tencent-adm%2Ftencent-meeting-mcp` 下载并**只读解包**。读取 `config.json`、`scripts/mcp_proxy.py`、`references/api_references.md`：JSON-RPC 2.0 POST，固定请求 id；endpoint 为 `https://mcp.meeting.tencent.com/mcp/wemeet-open/v1`。包内 config 版本是 **v1.0.15**，registry `_meta.json` 是 1.0.16；请求头按真正的 config 取 v1.0.15，不假装已获取最新版本。官方示例说明列表使用 `page_token` / `next_page_token`、转写 `pid` 为字符串、`limit` 为数字。

本实现只允许上述 **三个只读工具**，不会调用预约/修改/取消、通讯录、权限申请、反馈提交或智能摘要工具。模型无工具调用权限，原始转写作为 `UNTRUSTED_TRANSCRIPT` 数据传入；内容中的指令不得覆盖仓库规则。生成时实际读取当前 AGENTS、current、数据约定、纪要/卡片 skills 和卡片示例/经验，不复制一套过期合同。

**没有凭据，未声称完成真实鉴权/转写/模型/公开 PR 集成。** 未认证 `tools/list` 实探是 HTTP 401。包中没有静态完整 schema，故运行时先从官方服务获取 schema，检查固定工具的字段名/类型与必填参数；不匹配就停止。返回数据适配器只接受明确的结构（列表 `meeting_info_list` / `records` + `has_more`，转写 `minutes.paragraphs` + `more`）；这条真实 MCP 响应路径还需要有 Token 的维护者联调。若当前服务使用其他返回结构，不会猜测、调用相似工具或把智能纪要冒充原话，而是保留人工现有转写入口并要求补充适配测试。

测试使用明确标注的合成文本、合成 MCP/model response；本地集成测试会在临时目录创建真实本地 Git/bare 仓库，实际执行 scoped commit/push 与 read-back，GitHub PR 接口由合成响应替代，不会写入 GitHub 或把合成数据提交到本仓库的 events。CI 是可执行入口，尚不能把本地通过说成 GitHub 上已通过；首次推送 workflow 还需要提交者具备 workflow 权限。
