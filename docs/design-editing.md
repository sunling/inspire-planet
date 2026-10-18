# 设计修改清单

公众号封面修改 AI 提示词；小红书／视频号修改图文脚本或图卡渲染器。生成图片不是源文件，不提交 Git。

## 快速定位

| 想修改什么 | 修改哪里 |
|---|---|
| 某篇公众号封面的文案、画面与风格 | `events/{year}/{event}/assets/cover-prompts.md`，然后用 AI 重新生成或定向修改 |
| 公众号默认生图与检查原则 | `.agents/skills/inspireplanet/references/cover-design.md` |
| 某篇小红书首图、分页与主题 | `events/{year}/{event}/xhs-{slug}.md` |
| 某篇视频号首图、分页与主题 | `events/{year}/{event}/sph-{slug}.md` |
| 图卡通用留白、行距、字号、页眉页脚 | `scripts/text-cards/theme.css` |
| 图卡主题字体与配色 | `scripts/text-cards/theme-inspire.css`、`theme-paper.css` |
| 图卡解析、分页、截图、溢出检查 | `scripts/text-cards/render.py` |
| Actions 渠道、环境与下载 | `.github/workflows/render-content.yml` |
| 图卡 JPG 验证、预览与打包 | `scripts/render-publish.py` |

## 公众号 AI 封面

读完整篇文章，明确要调整的是文字、主体、画面关系还是风格。更新该篇实际提示词后调用 AI 生图工具；修改已有图片时保留无关部分。检查中文准确、主体完整、构图与正文相符，再交付结果。

不通过固定 HTML/CSS 模板、随机布局或双纸卡来代替 AI 生图。历史 `cover-config` 只作旧版参考，新提示词不需要 `layout`、`theme` 或 `tiles` 字段。

## 小红书／视频号图卡

各篇脚本维护自己的首图和内页；第 1 页就是该平台的首图，不使用公众号封面替换。

- 改图上文字、页序或主题：修改对应 Markdown。
- 改通用边距、标题与页眉页脚：修改 `theme.css`。
- 改主题字体与配色：修改相应 `theme-*.css`。
- 改解析、分页或渲染：修改 `render.py` 并运行相关测试。

两平台分别审阅与渲染。按 [协作指南](rendering.md) 在本地或 Actions 取图，检查字体、溢出、遮挡、分页、署名、尺寸与预览。新增全局布局或主题后用不同长度稿件检查回归。

参考：[AI 封面说明](../.agents/skills/inspireplanet/references/cover-design.md) · [图卡说明](../scripts/text-cards/README.md) · [内容流程](content-workflow.md)。
