# 设计修改清单

按“只改一篇内容 / 调整一种风格 / 修改通用渲染器”选择入口。**渲染后的封面和文字图卡都不是源文件，不提交 Git**；修改源稿或 CSS 后重新渲染即可。

## 快速定位

| 想修改什么 | 优先修改哪里 |
|---|---|
| 某篇公众号封面的文字、两张信息卡、布局与主题 | `events/{year}/{event}/assets/cover-configs.md` |
| 公众号封面的 HTML 结构 | `scripts/covers/template.html` |
| 公众号通用字号、间距及基础规则 | `scripts/covers/base.css` |
| 公众号布局（`collage` / `editorial` / `signal`） | `scripts/covers/layouts/`（`collage` 为默认基础布局） |
| 公众号配色、装饰及主题 | `scripts/covers/themes/` |
| 公众号配置解析、截图、字体和尺寸验证 | `scripts/covers/render.py` |
| 某篇小红书首图、分页内容及主题 | `events/{year}/{event}/xhs-{slug}.md` |
| 某篇视频号首图、分页内容及主题 | `events/{year}/{event}/sph-{slug}.md` |
| 图卡通用排版：留白、行距、字号、页眉页脚 | `scripts/text-cards/theme.css` |
| 图卡具体主题的字体与配色 | `scripts/text-cards/theme-inspire.css`、`theme-paper.css` |
| 图卡 Markdown 解析、分页、截图、溢出检查 | `scripts/text-cards/render.py` |
| GitHub Actions 可选渠道、环境及 Artifact 上传 | `.github/workflows/render-content.yml` |
| 多渠道渲染、JPG 验证、本地预览及打包 | `scripts/render-publish.py` |

## 公众号封面：内容和设计分开改

一篇封面用 `assets/cover-configs.md` 中对应的 `cover-config` JSON 控制。常用字段：

- `headline`：封面文字；`tiles`：两组信息卡内容
- `layout`：排布方式；`theme`：配色主题
- `asset`：**输出文件名**，不是要求图片入库
- `photo`、`photo_position`：经许可使用的源照片与裁切位置

如果只想改某期标题或布局，先修改配置，而不是全局 CSS。若要改变所有封面的字体、卡片位置或视觉风格，再修改模板、基础样式或主题文件。

现有布局：`collage`、`editorial`、`signal`；现有配色：`collage`、`pop`、`garden`、`blueprint`、`night`。添加布局或主题，需要同步检查渲染器的选择范围和相应测试，不能只放入新 CSS 文件。

## 小红书与视频号图卡

每篇 `xhs-{slug}.md`、`sph-{slug}.md` 自己维护首图文字、内页文案及选定主题。**图卡第 1 页就是首图**，它不是公众号横版封面，不要把两个渠道共用一张静态图。

- 改某页图上文字、页序或主题：优先修改对应的 `.md` 脚本。
- 改全部图卡的边距、标题大小、页眉页脚位置：修改 `theme.css`。
- 改 `paper` 或 `inspire` 主题的视觉语言：修改对应的 `theme-*.css`。
- 改脚本解析、分页或图片渲染行为：修改 `render.py` 并回归测试。

小红书和视频号即使分享同一主题，也应各自审阅对应图文脚本；不要直接复制另一渠道已渲染的图卡。

## 改设计以后怎么验证

1. 先审阅调整后的文字、署名、原始素材与设计配置。
2. 按 [渲染与协作指南](rendering.md) 在本地快速测试，或在 GitHub Actions 中选对应渠道出图。
3. 检查中文字体、标题溢出、正文碰撞、页眉页脚、分页连续性、图像尺寸以及预览是否可读。
4. 提交**源文件**改动；如需发布，从临时渲染产物中取图片，不提交成品 JPG。
5. 新增全局布局或主题时，建议再用一篇短稿和一篇长稿测试，确认已有风格没有回归问题。

参考：[公众号封面说明](../scripts/covers/README.md) · [图卡渲染说明](../scripts/text-cards/README.md) · [内容工作流](content-workflow.md)。
