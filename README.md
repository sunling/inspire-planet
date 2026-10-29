# 启发星球 · Inspire Planet

启发星球是一个持续分享真实生活、问题、尝试和变化的共同学习空间。

本仓库保存会议转写与编辑稿，并支持从本地回放制作短视频和播客。每位分享者保有自己的表达与署名；内容公开与发布均以参与者授权为前提。

## 一期内容，三种输出

| 输出 | 当前发布去向 | 交付物 | 制作入口 |
| --- | --- | --- | --- |
| 文字 | 公众号；知乎计划开通 | 一篇一个人一件事，正文、标题、备选标题和摘要保存在 `gzh-{slug}.md` | [文章 skill](.agents/skills/inspireplanet-gzh/SKILL.md) |
| 视频 | 视频号、小红书 | 原声切片、字幕、两平台标题与文案；独立封面按需制作 | [短视频 skill](.agents/skills/inspireplanet-clips/SKILL.md) |
| 音频 | 暂时以小宇宙为唯一发布去向 | 一期一集的轻剪播客、标题、简介与成品时间轴 | [播客 skill](.agents/skills/inspireplanet-podcast/SKILL.md) |

知乎开通后再明确适配与发布方式，当前不要求每篇另出知乎稿。小红书／视频号新增内容统一使用原声短视频，旧图文渲染脚本已清理，历史版本可从 Git 查阅。以上是渠道安排，不代表每期均已制作或发布；最新安排以 [current.md](current.md) 为准。

网站另按需使用 `summary.json` 展示单期回顾、`quote-cards.json` 展示金句卡片。会后群消息保存为 `group-message.md`，选一个具体片段、一个已核实回顾入口，见 [内容数据约定](events/data-contract.md)。

## 每期怎么做

1. **归档转写**：核对日期、期数和公开授权，按 [会议转写与归档](docs/meeting-content.md) 获取资料；已有转写不重复下载。
2. **按需制作**：文字从转写选故事；视频切片和播客共用一份手动下载、带声音的本地回放视频，无须另下音频。三条流程可独立进行，不必每期全部制作。
3. **审稿、审片或试听**：核对事实、归属、隐私、声音／肖像和具体公开范围；生成完成不等于可以发布。
4. **发布与留档**：用户发布，或明确授权后代为操作；记录实际平台链接，归档获准公开的最终文字。媒体与内部制作记录留在本地。

完整的输入、步骤、交付、存放位置和可用请求见 [内容制作流程](docs/content-workflow.md)。

## 文件放哪里

```text
events/             按期保存转写、文章、纪要与金句；获准公开的播客发布稿为 podcast.md
replays/            本地回放、剪辑单、字幕、发布草稿、审核记录和媒体，被 Git 忽略
docs/               转写归档与内容流程说明
.agents/skills/      内容 skills 与本地媒体工具
.github/workflows/   转写下载与内容校验
scripts/            转写归档和仓库内容校验工具
```

制作中的 `show-notes.md` 留在 `replays/`；标题、简介与成品时间轴确认可公开后，才整理成当期 `podcast.md` 长期归档。内部备注不随发布稿入库，音视频文件不提交 GitHub；Git 忽略的本地文件需要自行备份。

## 浏览与协作

- [按期浏览会议资料](events/README.md)：各期转写、文章、纪要与金句。
- [当前运营信息](current.md)：渠道安排、已确认官网与社群入口。
- [内容制作流程](docs/content-workflow.md)：每种输出从素材到发布的操作说明。
- [AI skills](.agents/skills/)：组合整理用 `inspireplanet`，单项任务走对应 skill。使用前请读 [AGENTS.md](AGENTS.md)。

欢迎通过 Issue 提出更正，或通过分支与 PR 参与协作。仓库公开不代表所有内容可以任意转载或改编；不要公开未获授权的个人信息、资料或凭据。修改后运行 `python3 scripts/check-content.py`。
