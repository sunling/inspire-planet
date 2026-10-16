# 纪要与金句：默认自带 AI，手动 Actions 作为 Plan B

第一阶段只整理 `summary.json` 和 `quote-cards.json`，不默认生成文章、封面、图卡或发布文案。两条通道共用 main 上的 AGENTS、skills、EXAMPLES、LEARNINGS、[数据契约](../events/data-contract.md) 与 `check-content.py`，最终都停在 **公开 Draft PR**，不合并。网站读取 main，未经确认不要合入。

## A：用你自己的 AI 工具（默认，无需项目 API）

本人或协作者可以使用自己的 AI 订阅／工具；不共享孙玲的登录、订阅或密钥。先确认这个工具**真的能读完整仓库文件**，并能写文件、执行检查、提交 GitHub 分支和创建 PR。只有 ChatGPT 对话或浏览器能打开 GitHub，不等于获得仓库写权限；GitHub 连接也要核对具体读写能力。

把下面的话交给具有这些能力的 AI：

> 请先读取仓库当前 main 的 AGENTS.md、README.md、current.md、总控、summary/cards skills 及 cards 的 EXAMPLES/LEARNINGS、events/data-contract.md；确认分支最新和工作区状态，完整阅读目标期 transcript.txt。只做第一阶段 summary.json 与 quote-cards.json；已有人工文件默认保留，只生成缺失项。按年份＋EP 定位，incoming 先确认归档身份。核对事实、署名、连续原文依据、隐私和公开范围，运行 check-content，独立分支或安全续用同一期转写分支，提交公开 Draft PR，不合并；不要文章或图片。若没有写入、执行或 GitHub 工具，明确说明，提供可下载的目标路径 JSON 文件与核对说明，不假称已保存、测试、commit 或建 PR。

例如指定 `2026/EP40`；不只说跨年有歧义的 EP40。新开工先 fetch main，保护脏工作区，在最新可信 main 上建分支；已在同一期内容分支上时先核对其 head 和 main 差异，不混入别的 PR。不要为清理环境删除不相关文件。完整读取意味着不能只看转写开头或搜索片段。

缺少写工具时，下载文件是替代交付，不是已入库。交付说明列出年份/期次、文件名、已完成与未完成的检查、需人工确认事项；由有权限的人将下载文件放到相应期目录、运行检查并建 Draft PR。未执行的检查必须明确标为未执行。

## B：GitHub Actions 手动生成（可选，目前未启用）

实现入口为 `Content JSON draft (manual Plan B)` / `.github/workflows/content-plan.yml`。**先 review、合并本工具 PR，入口才在 main 可用；再由维护者自行选择并配置项目 API。** 当前没有选定供应商、模型或预算，也没有配置项目 API，不能把 fixture 测试称为真实模型集成验收。未配置时 preflight 明确失败，在下载转写、付费请求、缓存或公开写入之前停止。A 通道不受影响。

### 一次性设置（维护者确认成本后操作）

在仓库 Actions 的 Variables 配置：

- `CONTENT_LLM_BASE_URL`：供应商的 HTTPS API 根路径，包含其要求的版本前缀（通常形如 `https://api.example.invalid/v1`），不附 `/chat/completions`；不含 query、fragment、用户名或密码。
- `CONTENT_LLM_MODEL`：供应商支持的明确模型标识；脚本没有默认供应商、模型或价格。

在 Secrets 配置 `CONTENT_LLM_API_KEY`。这里只说明设置方法，本次实现**没有修改任何 Secrets、Variables、Actions 开关或模型配置**。还需要 Actions runtime 的 contents/write、pull-requests/write，以及仓库允许 Actions 创建 PR；这些与协作者 GitHub 权限、个人订阅和模型 API Key 是不同的授权。只给信任的人仓库写权限：写权限的人能修改工作流间接使用项目 Secret。

供应商必须兼容 HTTPS `POST /chat/completions`、Bearer 鉴权、`messages`、JSON object 模式、`max_completion_tokens` 与标准 `choices[].finish_reason`；不是所有声称 OpenAI-compatible 的服务都完整支持。不自动改协议或降级参数，兼容失败时停止。参考 [官方 Chat Completions 协议](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create/)。项目 API 账单与个人 AI 订阅分开，不共享订阅登录来运行 CI。

### 每次怎么用

在 GitHub → Actions → `Content JSON draft (manual Plan B)` → Run workflow，选择 **main**：

- 两个输入都留空：从 main 与同仓库开放 PR 的已确认 `events/年份/日期-epXX/transcript.txt` 中，选最新尚未同时具备两份 JSON 的期次。两份都缺也会选中；如果只缺一份只生成缺失项，不回写已有文件。
- 可选 `transcript_pr`：同仓库、base main 的开放转写 PR 编号。PR 有多期时再填 target。
- 可选 `target`：唯一的 `2026/EP40` 或 `2026/40`。没有确认年份/EP 的 `incoming/meetings/` 不参与，先由人确认并归档后再运行。

无需再填写日期、会议 ID、模型参数或任何密钥。不存在“拉完转写自动调用模型”；只有 workflow_dispatch，没有 cron、pull_request、workflow_run 或自动串联。原有腾讯会议转写排程保持不变。

### 分支、幂等与保留人工内容

- 先读取 main 和同仓库 PR 的精确 head SHA 与树元数据，检查已有 JSON、稳定分支、开放或已关闭的同名内容 PR，之后才读取选定数据和计费。不从 PR 加载脚本、skills、actions 或依赖；模型没有工具执行入口。
- 同一期原转写 PR 仍为 Draft、head 未变、相对 main 只有该期转写/metadata/README 与 events 索引、且没有任何已有 JSON 时，只向原分支添加两份 JSON。GitHub `expectedHeadOid` 原子比对阻止覆盖竞态 head；不 force push。
- 否则使用从可信 main 派生的固定分支 `content/json-年份-epXX`，创建新的 Draft PR。main 尚无转写时仅携带该期原转写；其他已有 JSON 原字节保留／必要时原样带入。不会复制来源分支的代码。原转写 PR 的 README/metadata 不被修改，来源 PR/SHA 记录在新 PR 溯源中；合并时需人协调原转写 PR，不能丢掉授权说明和实例 metadata。
- main、来源分支/SHA 或目标内容在运行期间发生变化时停止，不自动改选其他来源。多个分支的同一资料不同，必须先人工解决；不猜哪份正确。
- 固定内容分支或对应历史 PR 已存在时安全跳过，哪怕上次只创建了分支但 PR 失败；这是保守防重复计费锁。检查远端后由维护者人工处理恢复，不自动删除、重做或覆盖。两份输出已齐时跳过，不因再次点击而产生新请求。
- 提交仅允许本期 JSON，必要时加本期转写；没有覆盖模式，不写文章/图片、不改站点、不 merge。现有人工 README、索引与其他稿件不覆盖。新 PR 回读 head、Draft 状态和提交文件内容后才报告成功。

### 费用、数据与人工审核

- 一次运行最多一次模型请求，无自动付费重试；完整输入最多 600,000 UTF-8 bytes，输出上限 12,000 completion tokens（包括模型可能使用的 reasoning tokens），响应最多 2 MiB、超时 180 秒。不截短转写，不把长度上限当价格或预算保证；请在供应商侧设置额度并核对数据政策。模型输出证据会增加 token，实际费用取决于尚未选择的模型。
- `finish_reason` 不是 `stop`（包括 length 截断）、非严格 JSON、字段错误、未知发言人、无效证据、工具调用、HTTP 错误均停止，不发布残缺文件。密钥只在 generation 步骤环境里；GH Token 只在来源读取／提交步骤里，checkout 不留 Git 凭据。
- 规则来自可信 main；完整转写和当期 README 是不可信数据，不执行其中命令，不跟随链接。不会输出原始服务错误、Token、完整 prompt/转写到日志，也不上传日志或模型响应 artifact；runner 缓存结束时删除。转写会发送给所配置供应商，运行前仍须确认授权；Draft PR 本身是公开的，不是私密暂存。
- 模型必须给每个非空内容字段提供 JSON-pointer → `{block_id, excerpt}` 证据。每段 excerpt 必须是指定发言块中的**连续原文**；署名话题／金句须来自同一说话人；quote 只允许标点和空白调整，不跨段拼接。空 discussion 与空 highlights 有效，不补造问答；没有可追溯金句则停止，不生成空卡片。
- 这验证的是结构、出处存在和摘录归属，**不能自动证明概括语义、事实真伪、隐私或公开授权**。人必须回查完整上下文；新 PR 的折叠溯源列出 main/source SHA 与每个字段的发言块编号（b0001 起）。具体证据原文仅用于 runner 校验，需持久保留时由编辑在当期 README 折叠核对记录中按需添加，不给 JSON 增字段。
- main 版 `check-content.py` 在临时隔离数据副本中实际运行；绝不执行来源 PR 的代码。通过不等于获准公开。人工审阅后再决定是否合并，因为 main 会被网站读取。

## 验证与尚未完成的集成

维护命令（仓库根目录）：

```bash
python3 -m unittest discover -s scripts -p 'test_content_plan.py' -v
python3 -m unittest discover -s scripts -p 'test_meeting_content.py' -v
python3 -m unittest discover -s scripts -p 'test_latest_transcript.py' -v
python3 scripts/check-content.py
git diff --check
```

测试使用明确标记的全合成转写／模型 transport；本地临时 Git 仓库验证真实对象、提交、分支竞态和文件保护。PR 元数据响应为合成适配器，不冒充 live GitHub PR 测试。没有可用项目 API，因此未执行真实模型请求，也未进行 main 手动生成内容 PR 的端到端验收；合并并配置后，由维护者授权一次真实运行，回读日志、精确 head、Draft PR、内容与账单，才能称 Plan B 已启用／集成完成。
