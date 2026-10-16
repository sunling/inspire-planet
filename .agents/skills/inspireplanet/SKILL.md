---
name: inspireplanet
description: 启发星球对外内容总控：从某期会议转写一次生成公众号文章、小红书和视频号图文、网站纪要与金句卡片，并写本期索引 `README.md`。目标是把分享者的分享整理出来，让更多人看见。
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
  summary.json                  网站单期详情页的分享纪要
  quote-cards.json              金句卡片与周刊数据
  assets/cover-configs.md              公众号横版封面的配置与设计信息
  （生成的公众号 JPG 不入库）
  README.md                     本期导航、命令与发布备注
```

`{slug}` 是分享者的英文小写名，一位分享者一个文件，如 `gzh-liying.md`。只创建真实需要的文件。

## 路由

- 逐字稿 / 转写 → GitHub Actions，入口与历史补录见 [下载说明](../../../scripts/meeting-content.md)
- 公众号文章 / 标题 / 摘要 / 横版封面 → `inspireplanet-gzh`
- 小红书 / 图集 / 竖版封面 → `inspireplanet-xhs`
- 视频号 → `inspireplanet-sph`
- 网站纪要 / summary.json → `inspireplanet-summary`
- 金句 / 卡片 JSON → `inspireplanet-cards`
- 本期导航 / 命令 / 发布备注 → 本 Skill

完整发布包包含两份 JSON；只生成指定交付物时不扩展范围。字段、期次身份、溯源和审核后同步方式见 [内容数据约定](../../../events/data-contract.md)。生成不等于公开，提交到网站读取的 `main` 分支前核对具体稿件与授权。

## 工作流程

1. **下载与归档**：通过 GitHub Actions 拉取转写并创建公开 Draft PR，人工审核期次与公开范围后归档为本期 `transcript.txt`。已有转写不重复下载；缺少时提供 Actions 入口，等待转写归档或用户提供原稿。触发下载并公开原稿须有用户授权；仅请求整理内容不视为下载公开授权。
2. **生成发布包**：全套包括公众号文章、小红书与视频号各自的图文脚本、网站纪要 `summary.json`、金句 `quote-cards.json`，以及 `assets/cover-configs.md`；只要某个渠道时只生成相关交付物。先完成内容，再汇总公众号封面配置，并更新本期 README 的导航与本期命令，此阶段不渲染。公众号配置的布局 `layout` 和配色 `theme` 通过 `scripts/covers/assign_themes.py {本期目录}/assets/cover-configs.md` 将未指定值随机均衡分配为具体组合，保留已有选择。小红书／视频号各篇在脚本中写明 `- 主题：paper` 或 `inspire`，首图内容在第 1 页；没有公众号稿时无需新建独立封面配置。
3. **确认**：在 README 的稿件导航与“本期命令”中提供文章、`assets/cover-configs.md` 和各篇小红书／视频号脚本的导航、渲染命令；通用 prompt 见 `scripts/content-workflow.md`。确认对应文章、封面文字、视觉命题、图卡每页文字、署名与主题后，才生成公众号封面和分别渲染图卡，再检查。按保存的布局与主题出图，不重新抽选；结果在交付回复中说明。各渠道可分别确认并出图，不必等待无关篇目。
4. **发布**：当事人确认具体稿件与公开范围后，下载临时 Artifact 中的图片，检查后人工发布。不直接操作外部平台。

已有渲染确认在脚本未变时继续有效；用户明确确认已有脚本并要求渲染时直接执行。改动图中文字或视觉命题后重新确认受影响部分。

封面与文字卡仍使用原渲染器；确认后手动触发 GitHub Actions `render-content.yml`，在临时 runner 中生成、检查、打包，Artifact 保留 1 天，绝不将生成 JPG 回写仓库或长期保存 ready/history。详细步骤见 `scripts/publish.md`。

## README.md

通用制作步骤与 prompt 集中在 [内容制作说明](../../../scripts/content-workflow.md)，每期 README 链接该说明，按“稿件导航 → 本期命令 → 发布备注”排列，不复制四步流程或 Mermaid 图。替换下列示例为本期真实日期、路径与篇目，只链接已存在的文件；只列具备配置和脚本的渠道命令。

````md
# EPXX｜{YYYY-MM-DD}

{一句话概括本期}

通用步骤与 prompt 见 [内容制作说明](../../../scripts/content-workflow.md)。

## 稿件导航

| 分享者／选题 | 公众号 | 小红书 | 视频号 |
|---|---|---|---|
| {名字：选题} | [文章](gzh-{slug}.md) | [图文脚本](xhs-{slug}.md) | [图文脚本](sph-{slug}.md) |

来源：[转写](transcript.txt)。纪要：[JSON](summary.json)。金句：[JSON](quote-cards.json)。公众号封面：[配置](assets/cover-configs.md)。

## 本期命令

确认对应稿件、封面配置与图文脚本后，在仓库根目录执行：

```bash
python3 scripts/render-publish.py {本期目录} --channel gzh
python3 scripts/render-publish.py {本期目录} --channel xhs --channel sph
```

下载：GitHub Actions 的临时 Artifact（保留 1 天，不入库）。

## 发布备注

- {本期特有的授权、隐私或事实核对事项；详细依据按需用 details 折叠}
````

- 每期仅保留转写、各平台稿、纪要、金句、索引、封面配置及必要的授权原始素材；所有生成 JPG、预览与 ZIP 不入库。
- 只列真实存在的文件，不补空小节，不重复文章正文或摘要。稿件链接集中列一次，不另建“本期文件”“这一期有谁”等重复清单。
- README 不写生成、审稿或渲染进度，不设状态列；制作结果与临时成品链接在交付回复中说明。事实核对和发布授权事项保留在发布备注，长记录折叠。
