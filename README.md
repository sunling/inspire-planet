# 启发星球 · Inspire Planet

这里保存启发星球共同创作的会议资料、金句、分享文章与发布材料，以及整理这些内容的 AI skills。

启发星球是一个持续分享真实生活、问题、尝试和变化的共同学习空间。内容来自参与者的分享与讨论，保留发言归属，不把共同成果归为某一个人的个人知识库。

## 浏览内容

- [按期浏览会议资料](events/README.md)
- [当前活动信息](current.md)：只有经过确认的信息才用于新的邀请与发布文案。
- [AI 工作流](.agents/skills/)：分享文章、金句卡片、发布材料、小红书/视频号图文和封面。
- [迁移说明](MIGRATION.md)

## 文件结构

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt       会议原始转写
  index.md             本期索引（仓库内，不单独发公众号）
  gzh-{slug}.md        公众号分享文章（一位分享者一篇）
  xhs-{slug}.md        小红书图文（一位分享者一篇）
  sph-{slug}.md        视频号图文（一位分享者一篇）
  quote-notes.md       历史金句与语境笔记
  quote-cards.json     金句卡片数据
  promo.md             发布材料（标题、摘要、排期）与封面配置
  covers/              会议及社交平台封面
.agents/skills/          生成上述内容的工作流
scripts/                 拉取逐字稿、渲染卡片图等辅助脚本
```

文件名规则：**渠道缩写-分享者英文 slug**（`gzh-liying.md` / `xhs-liying.md` / `sph-liying.md`）。一期选了谁、哪个渠道有内容，看文件名就知道。历史期沿用旧的 `recap.md` / `xiaohongshu.md`，不追溯改名。

每期只保存实际存在的文件，不补空稿。历史资料保留原表达；原始转写可能包含识别错误，不能把它当作经过核实的事实或建议。历史文案中的会议时间和入口只代表当时状态。

孙玲的个人分享稿、演示文稿、个人文章、个人配图，以及一对一对话实验继续保留在私人仓库 `sunling-os`。这里不依赖私人仓库才能浏览会议成果。

## 参与整理

所有人都可以浏览本仓库，有 GitHub 账号即可通过 Issue 提出更正，或 Fork 后提交 Pull Request。直接写入权限由维护者另行授予。

更正时请说明期数、文件和原始依据；保留分享者署名，不把不同人的话拼成一句。公开新增材料前检查参与者同意范围、个人隐私及凭据。不要上传私人报名表、未获准公开的一对一材料或密钥。

仓库公开不代表对所有内容授予任意再利用许可；引用、改编或转载时应尊重作者署名及授权。

## 使用 AI skills

在本仓库根目录打开支持项目 skills 的 AI 工具，先读取 [AGENTS.md](AGENTS.md)。例如：

- “下载本期逐字稿” → `inspireplanet-transcript`
- “整理某期会议的完整发布包” → `inspireplanet`
- “整理会议纪要 / 写分享文章” → `inspireplanet-recap`
- “提炼金句卡片” → `inspireplanet-cards`
- “生成公众号文案” → `inspireplanet-promo`
- “生成小红书图文” → `inspireplanet-xhs`
- “生成视频号内容” → `inspireplanet-sph`
- “生成会议封面” → `inspireplanet-cover`

生成内容与真实发布分开；只有明确要求发布时才操作外部平台。
