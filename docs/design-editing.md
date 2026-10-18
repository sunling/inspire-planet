# 设计修改清单

小红书／视频号修改图文脚本或图卡渲染器。生成图片不是源文件，不提交 Git。

## 快速定位

| 想修改什么 | 修改哪里 |
|---|---|
| 某篇小红书首图、分页与主题 | `events/{year}/{event}/xhs-{slug}.md` |
| 某篇视频号首图、分页与主题 | `events/{year}/{event}/sph-{slug}.md` |
| 图卡通用留白、行距、字号、页眉页脚 | `scripts/text-cards/theme.css` |
| 图卡主题字体与配色 | `scripts/text-cards/theme-inspire.css`、`theme-paper.css` |
| 图卡解析、分页、截图、溢出检查 | `scripts/text-cards/render.py` |
| Actions 渠道、环境与下载 | `.github/workflows/render-content.yml` |
| 图卡 JPG 验证、预览与打包 | `scripts/render-publish.py` |

## 小红书／视频号图卡

各篇脚本维护自己的首图和内页；第 1 页就是该平台的首图，各自独立生成。

- 改图上文字、页序或主题：修改对应 Markdown。
- 改通用边距、标题与页眉页脚：修改 `theme.css`。
- 改主题字体与配色：修改相应 `theme-*.css`。
- 改解析、分页或渲染：修改 `render.py` 并运行相关测试。

两平台分别审阅与渲染。按 [协作指南](rendering.md) 在本地或 Actions 取图，检查字体、溢出、遮挡、分页、署名、尺寸与预览。新增全局布局或主题后用不同长度稿件检查回归。

参考：[图卡说明](../scripts/text-cards/README.md) · [内容流程](content-workflow.md)。
