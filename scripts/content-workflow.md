# 内容制作说明

每期从原始转写生成稿件，经确认后出图，再按授权范围发布。单期 README 只保留稿件导航、本期命令与发布备注；不重复本说明，不记录制作进度。

## 1. 下载与归档

通过 GitHub Actions 的 **Transcript draft** 获取最新会议，无需填写日期或期数；历史会议使用 **Historical transcript (advanced)**，见 [下载说明](meeting-content.md)。流水线创建的是公开、未经人工审阅的 Draft PR，人工核对期次与公开范围后归档；期次不明的材料先进入 `incoming/meetings/`。已有本期 `transcript.txt` 无需重复下载，也可接收用户手动提供的原稿。原始转写不润色。

## 2. 生成稿件与配置

在仓库根目录打开支持项目 skills 的 AI 工具，先读取 [AGENTS.md](../AGENTS.md)。完整发布包包含公众号文章、小红书和视频号各自的图文脚本、网站纪要 `summary.json`、金句 `quote-cards.json`，以及公众号封面配置 `assets/cover-configs.md`；也可只生成指定内容，不补空文件。

公众号封面配置按文章保存封面文字、布局、配色、设计意图和临时输出文件名（配置中的 asset 不意味着将图片提交仓库）。小红书／视频号的首图文字、主题与字体放在各自图文脚本中；两平台分别编排。此阶段只生成文字与配置。

将下列 prompt 的 `{本期目录}` 替换为真实路径，例如 `events/2026/20261010-ep40`：

> 使用 inspireplanet，基于 {本期目录}/transcript.txt 生成本期发布包：公众号、小红书、视频号、summary.json、quote-cards.json 和公众号封面配置。小红书与视频号分别编排；更新本期 README 的导航、本期命令与发布备注，先不要渲染。

## 3. 确认后渲染与检查

先审阅文章、公众号封面配置、各平台脚本的首图与每页文字、署名、主题和字体。各渠道可以分别确认；文字或视觉命题变更后重新确认受影响部分。

确认后打开 GitHub Actions 中的 Render content (temporary download) 工作流，选择期次、渠道与已审阅分支，手动运行。它调用 `render-publish.py` 在 runner 临时目录渲染；首图随各平台内页生成，各自保持主题与字体一致，不跨平台复用整套图片。

- 渲染环境：[公众号封面](covers/README.md)、[图卡](text-cards/README.md)。需 Python 依赖、Chromium 和相应字体；必要时指定 `--font`、`--browser`。
- 输出与下载：[按需渲染](publish.md)。检查通过后以 GitHub Actions Artifact 提供 JPG、预览和 ZIP，保留 1 天；不提交生成图片、不维护 ready/history 永久版本。
- 出图后检查文字溢出、遮挡、分页、署名、图片尺寸与完整性；结果在交付回复中说明。

确认公众号配置后的 prompt：

> {本期目录} 的公众号文章及 assets/cover-configs.md 已确认，请从已审阅分支触发云端 Render content 工作流，检查图片并提供临时 Artifact 下载入口，不回写成品图片。

确认图文脚本后的 prompt（按已确认范围选择平台或篇目）：

> {本期目录} 的小红书与视频号图文脚本已确认，请从已审阅分支触发云端 Render content 工作流，首图随内页生成，提供临时 Artifact 下载入口，不永久保存。

历史期如仍将公众号封面配置嵌在文章中，重新使用统一发布工具前先整理到 `assets/cover-configs.md` 并确认。历史首图不能直接替代新平台脚本的首图。

## 4. 发布

当事人确认具体稿件、署名、可识别隐私及公开范围后，发布者从 `ready/gzh/`、`ready/xhs/{slug}/` 或 `ready/sph/{slug}/` 取图。出图确认不等于发布授权；AI 只有收到明确发布指令才操作外部平台。

本期特有的授权边界、待核对事实、实际发布日期和平台链接放在单期 README 的发布备注中，详细溯源按需折叠。活动时间与加入方式使用经过确认的 [current.md](../current.md)，不从历史文案推断。网站数据遵循 [内容数据约定](../events/data-contract.md)；JSON 合入 `main` 前完成内容与授权审核。
