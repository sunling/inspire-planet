# 腾讯会议逐字稿 → 公开 Draft PR

- 先打通逐字稿拉取：Actions 只读取腾讯会议，写入本期 `transcript.txt` 和 `events/README.md` 索引。
- 不调用模型，不需要模型 API Key，不生成纪要、金句、文章、图片或发布包；没有内容生成 workflow。
- 后续整理可在 ChatGPT/Codex 中单独发起，继续使用同一 `content/YYYYMMDD-epXX` 分支；本自动化不会覆盖人工内容，不自动合并或发布。
- **Draft PR 不是私密空间**：原始转写、姓名和上下文会公开在分支上。启用 `draft` 前确认参与者授权、隐私与公开范围；保密会议不要使用此路线。

## 首次设置

1. 先 review 工具 PR 与无密钥 **Content CI**。生产入口 `Transcript draft` 必须存在于默认分支，手动运行也只允许默认分支。PR26 已合并；后续修复仍须独立 Draft PR，不能因联调通过自动合并。下述 Content CI 的固定 EP40 只读 dispatch 是单独的维护入口，不绕过生产默认分支保护。
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
- 参数以运行时官方 `tools/list` 为准；字段名、类型、必填参数不兼容即停止。三个工具都显式设置经 schema 验证的 `is_compact=false`：实测默认 compact 转写会删掉 `more`，不能据此判定全文。
- 实测工具结果为 `content[0].text` 中的 JSON，可含 `_meta` / `data`，其内或直接为 `{status_code, headers, body}`；`body` 是另一个 JSON 字符串。仅解已知包装、最多六层，每层检查业务码与上游 HTTP 状态；从不打印 body、headers 或原始错误。
- 已结束会议使用 `meeting_info_list + has_more`；录制分页使用原生 `record_meetings[].record_files[] + has_more`，不再假设顶层 `records`。用唯一 UTC 会议的 `meeting_id + sub_meeting_id` 精确限定本次，再核对 `(meeting_record_id, record_file_id)` 集合与该次 `records` 元数据完全一致，拒绝缺项、重复或跨期混入。实测 `records_total_count` 不等于本次 records 长度，不能据它判断本次完整性；缺少子会议身份或元数据覆盖不完整时停止，不猜测回退。此规则在 EP40 通过，但历史 EP50 已证明同一子会议可含其他日期录制；当前严格集合检查因此会拒绝部分历史目标，详见下方诊断记录。
- 候选仍按本次元数据的时长降序，仅在完整空稿或首屏明确 30002 时尝试下一份；转写必须有 `minutes.paragraphs + more`。原生段落时间为整数毫秒，按[腾讯转写详情说明](https://meeting.tencent.com/support/topic/797/index.html)转为 `HH:MM:SS`；保留 CLI 的字符串时间兼容。分页、上限和未知发言人检查不降级。
- 测试中的正文与 GitHub PR 响应仍为合成数据；新增回归仅复现已观察的结构，不保存真实响应。独立集成测试实际执行临时本地 Git/bare 仓库的提交、推送与 SHA 回读，不写 GitHub、不把测试内容放进本仓库 events。

## 固定 EP40 的显式只读维护检查

`Content CI` 的 push / pull_request `check` job 不接收任何 Secret。只有人工 `workflow_dispatch` 才运行 `ep40-readonly`：`contents: read`、checkout 精确 `github.sha`、不持久化 GitHub 凭据，仅拉取步骤接收 Tencent Secret。日期固定 `2026-10-10`、期数 `40`，ID 使用已确认的 EP40 过滤器；不开放任意工具或发布模式。

对已审阅、已推送的修复 ref，可由维护者执行：

```bash
gh workflow run content-ci.yml --ref fix/mcp-transcript-response
```

该 job 调用真实 `fetch-check`，验证 `git status --porcelain` 为空，始终删除 `.git/meeting-content-fetch-check.txt`，无 transcript artifact、提交、推送或内容 PR。结构探针已移除，正常维护入口不打印任何响应结构或值。生产 `meeting-content.yml` 的默认分支与排程开关保护未修改。

### 真实验证记录（2026-10-15）

- [38783795059：生产 connectivity 成功](https://github.com/sunling/inspire-planet/actions/runs/38783795059)：Actions Secret 鉴权与三个工具参数 schema 通过，单凭此不能证明转写可用。
- [38783877138：旧适配器 fetch-check 失败](https://github.com/sunling/inspire-planet/actions/runs/38783877138)：列表结构不支持，未发布或覆盖内容。
- [38784249250：安全结构诊断](https://github.com/sunling/inspire-planet/actions/runs/38784249250)识别 HTTP/JSON body 包装；[38784551270](https://github.com/sunling/inspire-planet/actions/runs/38784551270)确认 full 模式恢复 `more`；[38785307755](https://github.com/sunling/inspire-planet/actions/runs/38785307755)确认原生录制列表经子会议限定后与该次文件集合一致。仅结构、类型、计数及必要分页标志进入日志，没有原始响应或转写 artifact。
- [38785641587：真实 EP40 fetch-check 成功](https://github.com/sunling/inspire-planet/actions/runs/38785641587)，代码 `79dbd6bf98f4811a9986c1c28b26e54a17e19b66`：**181 段**，会议/录制/转写实际远程分页路径通过、公开文件未变化、runner-only 缓存清理成功；同次 19 项本地逻辑测试及 `check-content`（87 期、7 skills）通过。这个数字来自真实运行，不是预设断言。
- 本次未测试公开内容 Draft PR 的发布权限，不改 Actions 建 PR 设置，不启用排程，不合并修复 PR，也不覆盖已有 EP40。

### 2025 历史场次诊断与真实只读样本（2026-10-15）

- 可选维护输入 `historical_ep50=true` 仅在人工 dispatch 时运行固定 EP50（`2025-12-27`）结构诊断与原生产 `fetch-check`；不接受任意日期、工具或发布命令。与 EP40 一样检出 dispatched SHA、只读权限、无转写 artifact，最终检查公开文件未变并清理缓存。push/PR 的 `check` 不接收 Secret。
- [38787666668](https://github.com/sunling/inspire-planet/actions/runs/38787666668)，代码 `00c22a9f8b973b53af6d7d5d6df09493c913510b`：EP40 再次实际拉取成功（181 段）；EP50 诊断成功但 `fetch-check` **仍按安全门禁失败**。EP50 元数据 5 个文件，原生列表同 `meeting_id + sub_meeting_id` 下 6 个文件；双方无重复，元数据全包含于原生列表，原生多 1 个。双方当天文件数均为 3。不是分页未走完或重复数据；不能把整个 run 写成成功。
- 已授权本机 CLI 独立遍历该项目的 4 页录制（30+30+30+10），确认同一子会议下混入其他日期文件，额外文件来自其他日期；所以仅靠 meeting/sub-meeting ID 不足以确定历史场次归属。生产适配器保持原样，不把相等改为包含、不忽略额外文件、不跳过检查。
- 一次性只读 CLI 探针同时限定唯一已结束会议日期、项目身份、子会议身份及两接口文件时间戳当天，**先核对当天 `(meeting_record_id, record_file_id)` 集合完全相等且无重复**，再按最长转写候选读取全部分页，直到 `more=false`，保留生产段落/姓名/上限检查。探针属于保守人工取样，不是已通过的通用历史归属算法；不能推广为跨午夜会议处理方案。
- 实际取回 EP50（`2025-12-27`）197 段、32785 字符、末段 `01:54:38`；EP48（`2025-12-13`）206 段、32247 字符、末段 `01:46:47`。仅在私人 scratch 保存并回读验证完整文件；未写入 events、未上传正文或 artifact。EP49（`2025-12-20`）保守当天筛选只有云录制，没有当天起始的文字转写，因此本探针未取回；不据此宣称转写不存在，因为跨午夜转写需另行证明归属。
- 下一步须为文件时间区间与场次归属建立合成 RED→GREEN 回归，再做真实 MCP 全文验收。不要删除或放宽原有安全门禁来获取绿色结果。样本可供已授权的本地审核，公开内容仍每期独立 Draft PR，不合并、不启用排程、不更改 Actions 仓库权限。

手动复现固定历史诊断：

```bash
gh workflow run content-ci.yml --ref fix/historical-record-occurrence -f historical_ep50=true
```
