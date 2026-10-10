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
  README.md            本期索引与发布面板（仓库内，不单独发公众号）
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

每期根目录放来源、稿件和索引，`assets/` 放必要原图、公众号封面配置与成品。小红书与视频号按平台分别编排图文脚本、选择主题、审阅并渲染整套图卡（含首图）。图卡、预览、临时 HTML 和 ZIP 统一输出到仓库外，同批输出按 `xhs/{slug}/`、`sph/{slug}/` 分目录保存，两平台分别交付图片。每期只保存实际存在的文件，不补空稿。历史资料保留原表达；原始转写可能包含识别错误，不能把它当作经过核实的事实或建议。历史文案中的会议时间和入口只代表当时状态。

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

1. 用 `scripts/pull-transcript.py` 拉取，或手动下载转写稿，保存为本期 `transcript.txt`。
2. 生成全部内容（公众号、小红书／视频号图文脚本、金句卡片 JSON），也可只生成指定渠道或单个交付物。
3. 根据已生成的内容，在本期 `assets/cover-configs.md` 汇总公众号封面脚本与完整配置；小红书／视频号封面内容与主题留在各自图文脚本中；只生成金句 JSON 时无需新建封面配置。
4. 用户确认图文脚本和封面脚本后，再渲染文字卡与封面；确认前交付可审阅的稿件和配置。

生成内容与真实发布分开；只有明确要求发布时才操作外部平台。
