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
  assets/              会议及社交平台封面
.agents/skills/          生成上述内容的工作流
scripts/                 拉取逐字稿等辅助脚本；scripts/covers/ 用 HTML 模板生成渠道封面；scripts/text-cards/ 把图集脚本或分页 Markdown 渲染为卡片图（多主题）
```

文件名规则：**渠道缩写-分享者英文 slug**（`gzh-liying.md` / `xhs-liying.md` / `sph-liying.md`）。一期选了谁、哪个渠道有内容，看文件名就知道。历史期沿用旧的 `recap.md` / `xiaohongshu.md` / `promo.md` 和 PNG 封面，不追溯改名或转换。

每期只保存实际存在的文件，不补空稿。历史资料保留原表达；原始转写可能包含识别错误，不能把它当作经过核实的事实或建议。历史文案中的会议时间和入口只代表当时状态。

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
- 封面随渠道走：公众号横版 → `inspireplanet-gzh`；小红书竖版 → `inspireplanet-xhs`。默认 [HTML 纸张拼贴模板](scripts/covers/README.md)，可扩展主题和接入真实照片。

生成内容与真实发布分开；只有明确要求发布时才操作外部平台。
