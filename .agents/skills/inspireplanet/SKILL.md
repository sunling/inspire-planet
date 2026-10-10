---
name: inspireplanet
description: 启发星球对外内容总控：从某期会议转写一次生成公众号文章、小红书和视频号图文、金句卡片，并写本期索引 `README.md`。目标是把分享者的分享整理出来，让更多人看见。
---

# Inspire Planet

## 定位

把分享者的分享整理出来，让更多人看见。默认产出是**一位分享者的一件事**：一期多篇，一篇一个人一件事，不写会议纪要式的长篇汇总。

## 本期目录

```text
events/{year}/{YYYYMMDD}-epXX/
  transcript.txt                会议原始转写
  gzh-{slug}.md                 公众号文章（文末附标题、摘要、封面成品路径）
  xhs-{slug}.md                 小红书图文
  sph-{slug}.md                 视频号图文
  quote-cards.json              金句卡片
  assets/cover-configs.md              公众号横版封面的配置与设计信息
  assets/recap-cover.jpg        公众号横版封面（多篇时加 -{slug}）
  README.md                     本期索引与发布状态
```

`{slug}` 是分享者的英文小写名，一位分享者一个文件，如 `gzh-liying.md`。只创建真实需要的文件。

## 路由

- 逐字稿 / 转写 → `inspireplanet-transcript`
- 公众号文章 / 标题 / 摘要 / 横版封面 → `inspireplanet-gzh`
- 小红书 / 图集 / 竖版封面 → `inspireplanet-xhs`
- 视频号 → `inspireplanet-sph`
- 金句 / 卡片 JSON → `inspireplanet-cards`
- 本期索引 / 发布状态 → 本 Skill

## 工作流程

1. **下载转写稿（暂由孙玲完成）**：孙玲手动下载或在自己的已授权环境中用 `inspireplanet-transcript` 调用 CLI 拉取，原样保存为本期 `transcript.txt`。已有转写不重复下载；缺少时标记等待孙玲提供，不要求其他协作者登录她的账号。
2. **生成发布包**：全套包括公众号文章、小红书与视频号各自的图文脚本、金句 JSON，以及 `assets/cover-configs.md`；只要某个渠道时只生成相关交付物。先完成内容，再汇总公众号封面配置，并更新本期 README 的链接与状态，此阶段不渲染。公众号配置的布局 `layout` 和配色 `theme` 通过 `scripts/covers/assign_themes.py {本期目录}/assets/cover-configs.md` 将未指定值随机均衡分配为具体组合，保留已有选择。小红书／视频号各篇在脚本中写明 `- 主题：paper` 或 `inspire`，首图内容在第 1 页；没有公众号稿时无需新建独立封面配置。
3. **确认配置并生成公众号封面**：README 提供 `assets/cover-configs.md` 链接、使用本期实际路径的渲染 command 和 prompt。用户确认对应文章、封面文字和视觉命题后，按保存的布局与配色渲染，不重新抽选；更新制作状态。
4. **确认脚本并生成小红书／视频号图卡**：README 提供各篇脚本链接、各自的渲染 command 和 prompt。确认首图、内页文字、署名与主题后，分别生成首图和内页，并更新制作状态。
5. **发布**：当事人确认具体稿件与公开范围后，由发布者上传对应平台。README 分渠道记录待本人过目／待发／已发日期及平台链接。AI 仅在用户明确要求时操作外部平台，出图确认不视为发布授权。

已有渲染确认在脚本未变时继续有效；用户明确确认已有脚本并要求渲染时直接执行。改动图中文字或视觉命题后重新确认受影响部分。

封面出图方法见 `scripts/covers/README.md`；文字卡见 `scripts/text-cards/README.md`。公众号封面成品存本期 `assets/`。小红书与视频号按平台分别编排首图、叙事节奏、内页和互动收尾，各自选择主题、审阅并渲染，不能直接复制另一平台的整套脚本或复用其图片。两平台可选同一主题，各自首图与内页一次生成，不再替换首图。仓库外同批输出按 `xhs/{slug}/`、`sph/{slug}/` 分目录保存，总览和 ZIP 保留渠道分类。渲染后核对裁切、溢出、重叠及文字，并更新本期状态。渲染确认与对外发布授权分别记录。

## README.md

本期目录下的 `README.md` 是协作操作入口，不对外发布。使用下面的精简结构；输出时替换为本期真实日期、期数、文件路径及分享者 slug，链接只指向已存在的材料。命令从仓库根目录执行，使用已准备好的渲染环境；可链接工具说明解释依赖、字体和浏览器。每期都写五步；不涉及的渠道标注本次未生成，不补空稿或无效渲染命令。

````md
# EPXX｜{YYYY-MM-DD}

{一句话概括本期}

## 稿件与状态

| 分享者／选题 | 公众号 | 小红书 | 视频号 |
|---|---|---|---|
| {名字：选题} | [文章](gzh-{slug}.md) | [图文脚本](xhs-{slug}.md) | [图文脚本](sph-{slug}.md) |

来源：[转写](transcript.txt)。公众号封面：[配置](assets/cover-configs.md)。金句：[JSON](quote-cards.json)。

当前：{各渠道制作与发布状态；状态不一致时在对应表格单元注明}。

## 制作流程

命令在仓库根目录、已安装依赖的渲染环境中执行。

### 1. 下载转写稿（暂由孙玲完成）

孙玲手动下载，或使用自己的已授权 CLI：

```bash
python3 scripts/pull-transcript.py --date {YYYY-MM-DD} --episode {NN}
```

原样保存为 `transcript.txt`；已有转写无需重复下载。

### 2. 生成发布包

Prompt：基于 {本期目录}/transcript.txt，使用 inspireplanet 生成本期公众号、小红书、视频号、金句 JSON 与公众号封面配置，更新本期 README，先不要渲染。

### 3. 确认公众号封面配置，再出图

审阅 [assets/cover-configs.md](assets/cover-configs.md) 中的文字、布局、配色和对应文章。确认后执行：

```bash
cover_output=$(mktemp -d /tmp/inspireplanet-covers.XXXXXX)
python3 scripts/covers/render.py {本期目录}/assets/cover-configs.md \
  --preview-dir "$cover_output"
```

成品写入本期 `assets/`，预览留在仓库外。已有成品需覆盖时加 `--force`。

Prompt：本期公众号文章及 assets/cover-configs.md 已确认，请按保存的布局与配色渲染封面，检查并更新 README。

### 4. 确认小红书／视频号脚本，再渲染图卡

打开上方索引中的各篇脚本，确认首图、每页文字、署名和主题。分别执行（按本期实际篇目展开）：

```bash
card_output=$(mktemp -d /tmp/inspireplanet-cards.XXXXXX)
python3 scripts/text-cards/render.py {本期目录}/xhs-{slug}.md \
  "$card_output/xhs/{slug}" --jpeg \
  --contact-sheet "$card_output/previews/xhs-{slug}.jpg"
python3 scripts/text-cards/render.py {本期目录}/sph-{slug}.md \
  "$card_output/sph/{slug}" --jpeg \
  --contact-sheet "$card_output/previews/sph-{slug}.jpg"
```

每次用新输出目录；各篇首图与内页一次生成，按脚本选定主题。成品按平台分别交付，图卡不提交 GitHub。

Prompt：本期小红书与视频号图文脚本已确认，请按各篇保存的主题分别渲染，首图随内页生成；成品、预览与 ZIP 存仓库外，按平台和分享者分目录，检查并更新 README。

### 5. 发布

当事人确认稿件与公开范围后发布；在上方对应稿件旁记录 `已发 YYYY-MM-DD` 与平台链接。出图确认与发布授权分别记录。

## 发布备注

- {本期尚待确认的署名授权、事实或隐私；详细核对记录按需用 details 折叠}
````

- 每期根目录只保留转写、渠道稿、金句 JSON、索引及实际需要的历史资料；`assets/` 只放公众号封面配置、成品与经确认的必要原图。不单独保存小红书／视频号首图，不归档预览、临时 HTML、ZIP 或生成日志；
- 只列真实存在的文件和篇目，不补空小节；
- 不放文章正文和摘要；
- 稿件链接只在索引集中列一次，制作流程引用该索引；不另建重复的“本期文件”“这一期有谁”清单，不累积出图流水账。选题说明只保留影响本期协作的内容；详细会议与编辑核对记录按需折叠；
- 制作状态记录 `待确认` / `待渲染` / `已渲染`；发布状态记录 `待本人过目` / `待发` / `已发 YYYY-MM-DD`，在表格或备注中分别注明。
