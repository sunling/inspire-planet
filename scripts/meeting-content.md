# 腾讯会议逐字稿 → 公开 Draft PR

## 日常：不填日期、EP 或过滤器

- Actions → **Transcript draft** → Run workflow → 选择 `main`。日常入口没有输入框；API 也不需要 EP。
- 一次配置在 [meeting-project.json](meeting-project.json)：精确标题 `启发星球，互相赋能`、90 天回看、已核对锚点 `2026-10-10 / EP40 / 13319006708380765410`。会议周期 ID 可变化，发现按精确标题，不锁死旧 ID。
- 首次只需已授权的 `TENCENT_MEETING_TOKEN` Secret；不需要模型、API Key 或外部内容服务。Token 不放变量、参数、聊天或日志。
- **当前 Actions 创建 PR 设置为 false**（2026-10-15 核对）。新会议的自动 Draft PR 会被仓库设置阻塞；无新会议的只读 skip 不需要该权限。本次不修改设置。
- 本工具 PR 尚需用户审核合并后，生产入口才会使用新代码；生产保持默认分支门禁，不从 feature 分支绕过。

## 发现、去重与期次

- 查询真实 UTC 时间区间 `[now−90 天, now]`，完整翻页（最多 200 页），再次排除窗口外／未来实例；仅精确匹配项目标题，按实际开始时间取最新，不取账号任意最新一场。
- 先读取远端 `main` 与**全部开放 PR**的固定 head SHA；按既有转写日期和持久实例信息去重。实例键为 `sha256(meeting_id, sub_meeting_id, UTC start_time)`，不是共享周期 ID。
- 最新场已入库／已有草稿时 clean skip，不回退抓更旧会议，不覆盖或重复读取正文。稳定内容分支也去重，包括推送成功但建 PR 失败的分支。
- 优先使用已核对日期映射（初始为 EP40）。只有完整列表包含唯一锚点、同年同周期、其后仅一场且恰好是连续下一次时，才递增为 EP41；7 天间隔仅为连续性保守门禁，不按周数推 EP，不看历史最大 EP。
- 漏期、多场、回补、跨年、周期切换或锚点不可见时不猜 EP，也不阻塞下载。后续超出已核对的一次递增范围先待确认，审核后更新配置锚点，不要求每次运行填写字段。

## 两种公开归档

- EP 可证明：`events/{year}/{YYYYMMDD}-epXX/transcript.txt`、`metadata.json` 与总索引。
- EP 不明：`incoming/meetings/{sha256-instance-key}/transcript.txt`、`metadata.json` 与待确认 `README.md`；不改活动索引，不生成网站 JSON。
- **两条路线都是用户已授权的公开、未经审核 Draft PR**，不是私密暂存。metadata 保留实例、UTC 日期与录制文件身份；确认期次时保留它，避免重抓。
- 提交仅允许本次固定路径；检查默认分支、HEAD、工作区、暂存区、远端同名分支。无 force push；推送后读回 SHA，建 PR 后读回 Draft 状态及精确文件清单。
- 不调用模型，不生成文章、纪要、卡片或图片；不合并、不发消息、不修改网站或社交平台。网站只读取审核后 `main` 的既有 JSON，本流水线不生成它们。

## 高级历史补录／检查

- 单独入口 **Historical transcript (advanced)**，仅手动运行，保留 `validate / connectivity / fetch-check / draft`；按需输入日期、期数和精确标题／ID。
- `validate` 只校验本地；`connectivity` 只校验鉴权/schema；`fetch-check` 即使本地已有稿也强制读远程全文，仅缓存 `.git/meeting-content-fetch-check.txt`；`draft` 才公开写入。
- 历史周期会议 guard 不变：会议／子会议限定后，原生录制集合必须与本次文件集合**完全一致**；不放宽为包含关系，不跨日期选择最长录制。2025 旧协议问题不在本次范围内。
- MCP 源适配合同不变：三个只读工具、运行时 schema、完整模式 `is_compact=false`、已观察的 HTTP/JSON 包装、列表完成标志、完整段落分页及上限。未知结构／分页缺失均安全停止，原始错误隐藏。

## 安全与排程

- Tencent Secret 只注入发现／读取步骤；GitHub Token 只用于归档去重及提交。无原始 payload、转写日志或 artifacts；缓存留在 runner `.git`，任务结束清理。
- 生产 `main` 门禁不变。每日 08:20 UTC 排程仍由 `CONTENT_AUTOMATION_ENABLED == true` 保护；变量未设置，**本次未启用排程**，不再使用固定日期／EP／过滤器变量。
- 创建 PR 开关、Actions job 权限与 Secret 是三项独立条件；只读成功不证明自动建 PR 权限可用。

## 验证

- 无密钥：`python3 -m unittest discover -s scripts -p 'test_meeting_content.py' -v`、`python3 -m unittest discover -s scripts -p 'test_latest_transcript.py' -v`、`python3 scripts/check-content.py`；可用时运行 actionlint。
- 已注册 `Content CI` 的 push／PR 仅跑无密钥测试。只有人工 dispatch 才给只读 job Secret，checkout **精确 dispatched `github.sha`**；feature 验证用 `gh workflow run content-ci.yml --ref feat/latest-transcript`，不绕过生产门禁。
- `latest-readonly` 执行零输入真实发现与主分支／开放 PR 去重，验证公开工作区不变，不下载正文、不提交、不建 PR。`ep40-readonly` 保留真实固定 EP40 全文检查与缓存清理。
- 先前 EP40 全文实际成功：Actions run `38785641587`，181 段；本次新增真实运行以 PR 检查和手动 run 为准。
- 合成测试覆盖无新会议／主分支及开放草稿去重、下一期证明、间隔／跨年待确认、完整下载一次及真实本地 Git/bare 推送；合成 GitHub 响应不冒充真实内容 PR。
- 若真实最新仍是已入库 EP40，正确验收结果是 skip；不能据此声称新场次自动内容 PR 已真实跑通。新场次建 PR 尚受上述仓库设置阻塞。
