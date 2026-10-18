# 内容制作说明

每期从原始转写整理内容。公众号 skill 聚焦文章叙事、细节与事实核对；小红书／视频号图卡继续审阅脚本后用代码渲染。内容公开与发布须有当事人授权。

## 1. 下载与归档

通过 GitHub Actions 的 **Transcript download** 获取最新会议；历史会议使用 **Historical transcript (advanced)**，见 [下载说明](meeting-content.md)。转写通过校验后直接提交公开 `main`，不创建 PR；运行前确认公开授权，期次不确定时写入 `incoming/meetings/` 等待整理。已有本期 `transcript.txt` 无需重复下载，也可使用用户提供的原稿；原始转写不润色。

## 2. 生成稿件

在仓库根目录打开支持项目 skills 的 AI 工具，先读 [AGENTS.md](../AGENTS.md)。完整发布包包含公众号文章、小红书和视频号各自图文脚本、网站纪要 `summary.json`、金句 `quote-cards.json`。也可只生成指定内容。

生成内容的示例：

> 使用 inspireplanet，基于 {本期目录}/transcript.txt 生成本期公众号、小红书、视频号、summary.json 和 quote-cards.json。两平台分别编排，更新本期 README，先不要生成图片。

## 3. 小红书与视频号图卡

先审阅各自脚本的首图、每页文字、署名、主题与字体；确认后从已审阅分支运行 `render-content.yml`。渠道仅为 `xhs`、`sph`、`all`；`all` 仅包含存在的小红书／视频号脚本。

> {本期目录} 的小红书与视频号脚本已确认，请从已审阅分支运行 Render content 工作流，检查版式并提供临时 Artifact 下载入口。

- 环境与脚本格式：[图卡渲染器](../scripts/text-cards/README.md)。
- 操作与下载：[渲染与协作指南](rendering.md)。Artifact 保留 1 天，不提交生成图片、预览或 ZIP。
- 首图随各平台内页生成，不跨平台复用整套成品。

## 4. 发布

发布前由分享者本人确认具体稿件、署名、家庭或他人信息与公开范围。图卡取自 Artifact 的 `ready/xhs/` 或 `ready/sph/`。只有收到明确发布指令，才操作外部平台。

本期授权边界、待核对事实、发布日期和平台链接放在单期 README 的发布备注中。活动安排只使用经过确认的 [current.md](../current.md)，网站数据遵循 [内容数据约定](../events/data-contract.md)。
