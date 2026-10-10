# 启发星球 · Inspire Planet

这里保存启发星球共同创作的会议资料、金句、分享文章与发布材料，以及整理这些内容的 AI skills。

启发星球是一个持续分享真实生活、问题、尝试和变化的共同学习空间。内容来自参与者的分享与讨论，保留发言归属，不把共同成果归为某一个人的个人知识库。

## 浏览内容

- [按期浏览会议资料](events/README.md)
- [当前活动信息](current.md)：只有经过确认的信息才用于新的邀请与发布文案。
- [AI 工作流](.agents/skills/)：公众号文章、金句卡片、小红书/视频号图文和封面。

## 文件结构

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt       会议原始转写
  README.md            本期导航、制作流程与发布备注（仓库内，不单独发公众号）
  gzh-{slug}.md        公众号分享文章（一位分享者一篇；末尾附标题与摘要）
  xhs-{slug}.md        小红书图文（一位分享者一篇）
  sph-{slug}.md        视频号图文（一位分享者一篇）
  quote-notes.md       历史金句与语境笔记
  quote-cards.json     金句卡片数据
  assets/             只保存必要原图、配置与公众号封面
    cover-configs.md   公众号横版封面的配置与设计信息
    recap-cover-{slug}.jpg  公众号封面成品
.agents/skills/          生成上述内容的工作流
scripts/                 拉取逐字稿等辅助脚本；scripts/covers/ 用 HTML 模板生成渠道封面；scripts/text-cards/ 把图集脚本或分页 Markdown 渲染为卡片图（多主题）
```

文件名规则：**渠道缩写-分享者英文 slug**（`gzh-liying.md` / `xhs-liying.md` / `sph-liying.md`）。一期选了谁、哪个渠道有内容，看文件名就知道。历史期沿用旧的 `recap.md` / `xiaohongshu.md` / `promo.md` 和 PNG 封面，不追溯改名或转换。

每期根目录放来源、稿件和索引，`assets/` 放必要原图、公众号封面配置与成品。小红书与视频号按平台分别编排图文脚本、选择主题、审阅并渲染整套图卡（含首图）。渲染成品统一使用仓库旁固定目录 `inspire-planet-publish/{YYYYMMDD}-epXX/ready/`，按 `gzh/`、`xhs/{slug}/`、`sph/{slug}/` 分目录交付；固定预览、ZIP 和旧版历史也在仓库外，规则与命令见 [固定发布目录](scripts/publish.md)。每期只保存实际存在的文件，不补空稿。历史资料保留原表达；原始转写可能包含识别错误，不能把它当作经过核实的事实或建议。历史文案中的会议时间和入口只代表当时状态。

## 参与整理

所有人都可以浏览本仓库，有 GitHub 账号即可通过 Issue 提出更正，或 Fork 后提交 Pull Request。直接写入权限由维护者另行授予。

更正时请说明期数、文件和原始依据；保留分享者署名，不把不同人的话拼成一句。公开新增材料前检查参与者同意范围、个人隐私及凭据。不要上传私人报名表、未获准公开的一对一材料或密钥。

仓库公开不代表对所有内容授予任意再利用许可；引用、改编或转载时应尊重作者署名及授权。

## 使用 AI skills

在本仓库根目录打开支持项目 skills 的 AI 工具，先读取 [AGENTS.md](AGENTS.md)。例如：

- “下载本期逐字稿” → `inspireplanet-transcript`
- “整理某期会议的完整发布包” → `inspireplanet`
- “写公众号文章 / 起标题 / 写摘要” → `inspireplanet-gzh`
- “提炼金句卡片” → `inspireplanet-cards`
- “生成小红书图文” → `inspireplanet-xhs`
- “生成视频号内容” → `inspireplanet-sph`
- 公众号封面 → `inspireplanet-gzh`，从 [3 种布局 × 5 套配色](scripts/covers/README.md) 中独立选择；小红书／视频号封面 → 与内页一起由 [图卡渲染器](scripts/text-cards/README.md) 生成，使用脚本中选定的主题与字体。

工作流：

1. **下载转写稿（暂由孙玲完成）**：手动下载或通过已授权的 CLI 调用 `scripts/pull-transcript.py`，原样保存为本期 `transcript.txt`；已有转写无需重复下载。
2. **生成发布包**：生成公众号、小红书、视频号、金句 JSON 与公众号封面配置，也可只生成指定交付物；同时更新本期 `README.md`。
3. **确认配置并生成公众号封面**：在本期 README 提供 `assets/cover-configs.md` 的链接、对应渲染命令与 prompt；确认后出图。
4. **确认脚本并生成小红书／视频号图卡**：在本期 README 提供各篇图文脚本链接、按渠道分别渲染的命令与 prompt；确认后一次生成各自首图和内页。
5. **发布**：当事人确认具体稿件与公开范围后发布，发布日期和平台链接可记入本期 README 的发布备注。

每期 `README.md` 是操作入口，只保留“五步制作流程 → 稿件导航 → 发布备注”；不记录发布包生成进度、审稿或渲染状态，不维护进度面板。命令使用本期真实路径，详细会议与编辑核对记录按需折叠，不重复罗列稿件链接或出图历史。

生成内容与真实发布分开；只有明确要求发布时才操作外部平台。
