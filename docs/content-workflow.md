# 内容制作说明

每期从原始转写整理内容。公众号封面根据文章直接由 AI 生成；小红书／视频号图卡继续审阅脚本后用代码渲染。内容公开与发布须有当事人授权。

## 1. 下载与归档

通过 GitHub Actions 的 **Transcript draft** 获取最新会议；历史会议使用 **Historical transcript (advanced)**，见 [下载说明](meeting-content.md)。流水线创建公开的 Draft PR，人工核对期次与公开范围后归档。已有本期 `transcript.txt` 无需重复下载，也可使用用户提供的原稿；原始转写不润色。

## 2. 生成稿件

在仓库根目录打开支持项目 skills 的 AI 工具，先读 [AGENTS.md](../AGENTS.md)。完整发布包包含公众号文章、小红书和视频号各自图文脚本、网站纪要 `summary.json`、金句 `quote-cards.json`，以及公众号 `assets/cover-prompts.md`。也可只生成指定内容。

只写稿、暂不出图的示例：

> 使用 inspireplanet，基于 {本期目录}/transcript.txt 生成本期公众号、小红书、视频号、summary.json、quote-cards.json 和公众号 AI 封面提示词。两平台分别编排，更新本期 README，先不要生成图片。

## 3. 公众号 AI 封面

使用具备图像生成能力的 AI 工具，按照 [公众号 skill](../.agents/skills/inspireplanet-gzh/SKILL.md) 读取每篇完整文章，提取短副标题与视觉关系，直接生成带字横版封面。每篇的提示词保存在 `assets/cover-prompts.md`；不再生成 JSON 布局配置或调用代码封面渲染器。

> 根据 {本期目录} 的每篇公众号文章直接用 AI 生成一张横版封面，约 2.35:1；使用与文章相符的画面和准确的中文短副标题，检查文字与裁切并直接交付图片，不提交图片到仓库。

用户已要求“生成文章和封面”时，完成文章后直接出图；明确要求先给方案、只写稿或暂不出图时才停在文字阶段。不额外等待封面配置确认。AI 工具不可用时只交提示词并说明未出图，不将计划路径当成成品。

图片由当前 AI 生图工具交付，不经 GitHub Actions，不承诺 Artifact 链接。生成图片不自动获得对外发布授权。

## 4. 小红书与视频号图卡

先审阅各自脚本的首图、每页文字、署名、主题与字体；确认后从已审阅分支运行 `render-content.yml`。渠道仅为 `xhs`、`sph`、`all`；`all` 仅包含存在的小红书／视频号脚本，不包含公众号封面。

> {本期目录} 的小红书与视频号脚本已确认，请从已审阅分支运行 Render content 工作流，检查版式并提供临时 Artifact 下载入口。

- 环境与脚本格式：[图卡渲染器](../scripts/text-cards/README.md)。
- 操作与下载：[渲染与协作指南](rendering.md)。Artifact 保留 1 天，不提交生成图片、预览或 ZIP。
- 首图随各平台内页生成，不拿公众号横版封面替代，不跨平台复用整套成品。

历史 `cover-configs.md` 或稿内 `cover-config` 是旧记录；重新制作公众号封面时直接读文章并用 AI 生图。

## 5. 发布

发布前由分享者本人确认具体稿件、署名、家庭或他人信息与公开范围。公众号封面取自本次 AI 生图结果，图卡取自 Artifact 的 `ready/xhs/` 或 `ready/sph/`。只有收到明确发布指令，才操作外部平台。

本期授权边界、待核对事实、发布日期和平台链接放在单期 README 的发布备注中。活动安排只使用经过确认的 [current.md](../current.md)，网站数据遵循 [内容数据约定](../events/data-contract.md)。
