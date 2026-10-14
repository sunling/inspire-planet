# 网站与周刊的内容数据约定

内容在本仓库按期维护，网站 `sunling/inspireplanet.cc` 负责读取、展示与卡片导出，不另行手工维护同一份正式内容。

## 文件与身份

- `events/{year}/{YYYYMMDD}-epXX/summary.json`：网站单期详情页的结构化分享纪要。
- 同目录 `quote-cards.json`：金句卡片与启发星球周刊的数据。
- 期次用“年份＋期数”定位，例如 `2026/40`；JSON 中保留兼容的 `episode: "EP40"`，年份从目录取得。不能只靠 `EP40` 跨年关联数据。
- `summary.json` 的 `date` 使用目录日期，格式为 `YYYY-MM-DD`。不根据历史归档日期推断或纠正真实活动日期；发现错误须有依据并单独更正。

## 字段

JSON 使用 UTF-8。金句文件是数组，每项只含非空字符串 `name`、`title`、`quote`、`detail`、`episode`。`detail` 是读者可直接阅读的会议语境，不带“出处：……”、转写时间戳或时间区间。

纪要文件是对象，包含非空字符串 `episode`、`date`、`title`、`overview` 和非空数组 `topics`。新纪要每个话题包含 `speaker`、`title`、`context`、`keyPoints`、`quote`、`discussion`；`keyPoints` 是非空字符串数组。`highlights` 是字符串数组，没有额外片段时可为空。没有现场讨论时 `discussion` 可为空，不为满足格式补造问答。校验兼容历史话题的 `summary` 字段。

具体写法分别见 [纪要 skill](../.agents/skills/inspireplanet-summary/SKILL.md) 与 [金句 skill](../.agents/skills/inspireplanet-cards/SKILL.md)。纪要中的代表金句可以与卡片重复；两份文件分别服务整场阅读和独立卡片，不要求数量或顺序一一对应。修改事实、署名或匿名边界时检查两份文件及相关渠道稿。

## 事实与审核

会议事实回查本期 `transcript.txt`；已有文章只辅助理解。原始转写不随编辑稿润色，历史期无转写时不补造出处。需要留存具体时间区间时，写入本期 README 折叠的编辑核对记录，不放进金句展示字段。Git 历史保留修订记录。

完整发布包生成两份 JSON；单独任务只生成指定内容。文件生成后仍须核对事实、署名、隐私及公开授权，生成文件不等于获准公开。README 只维护导航、制作流程与发布备注，不记录制作进度。

## 网站读取与修订

网站当前从 GitHub 的 `sunling/inspire-planet/main` 扫描每期目录并读取 JSON，目录列表缓存约 5 分钟，解析后的数据按文件 SHA 缓存。因此合并到 `main` 会使内容被网站读取，不应把未经确认的草稿合入该分支。

审核后运行 `python3 scripts/check-content.py`，通过分支与 PR 提交。用户确认具体公开范围后再合并；本地修改或 Draft PR 不会更新网站正式数据。修订也在本仓库完成，网站随后读取新版本；未显示更新时先核对文件是否已合入 `main` 与缓存刷新情况。

历史期没有 `summary.json` 时保留缺失，网站现有逻辑会尝试内置纪要、历史 `recap.md` / `gzh-epXX.md`，没有纪要时详情页展示金句或整理中提示。没有金句时不生成空卡片补位。两类数据都未必每期齐全。

新增或改名字段、移动文件前，同时修改生成 skills、校验器和网站读取代码；普通文案修订保持现有结构。
