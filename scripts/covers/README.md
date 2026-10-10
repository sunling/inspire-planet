# HTML 封面渲染

从封面配置 Markdown 生成 HTML，用 Chromium 截图并保存 JPEG。默认 `collage`（C 版纸张拼贴），不调用图像生成模型。复用 `scripts/text-cards/requirements.txt` 的依赖。

## 配置位置

每期用 `events/{year}/{event}/cover-configs.md` 集中保存所有封面的配置与设计信息，按篇目和渠道分节。每节记录对应稿件、成品路径、选定的封面文字、视觉命题，以及一个完整的 `cover-config` JSON 块。配置只在此维护，不在渠道稿中重复保存；复用同一张封面时只记录对应关系。

渲染器按文件内的配置顺序生成全部封面。历史稿中的单个配置块仍可直接读取，无需迁移所有历史期。

<!-- 示例放在四重代码块中，避免与真实配置混淆。 -->
````md
<!-- cover-config -->
```json
{
  "theme": "collage",
  "format": "portrait",
  "asset": "assets/xiaohongshu-cover-example.jpg",
  "speaker": "分享者",
  "episode": "2026EP38",
  "date": "2026-09-26",
  "headline": ["一个具体场景", "一个真实问题"],
  "subtitle": "保留一点好奇",
  "tiles": [
    {"label": "起点", "value": "片段一", "note": "源于分享的细节"},
    {"label": "变化", "value": "片段二", "note": "源于分享的动作"}
  ]
}
```
````

- `format`: `wide` 为 1920×817；`portrait` 为 1080×1440，独立构图。
- 公众号：`headline` 只放 6–14 字的短副标题，按语义断成 1–2 行，`subtitle` 留空。
- 图集首图：`headline` 放具体的核心标题，按语义断成 2–3 行（建议每行不超过 7 个中文字），`subtitle` 可以放补充短句，避免重复。
- 两张纸卡表达本篇特有的起点、变化或关系，不套空泛口号；标签、卡片文字也须有内容依据。`value` 建议 2–4 字，`note` 建议 8 字以内。
- `asset` 和本地照片路径相对配置 Markdown 的目录。文件名沿用原渠道规范；同一文件内不能配置重复的成品路径。已有成品时须显式 `--force`。

## 运行

```bash
python3 -m pip install -r scripts/text-cards/requirements.txt
python3 scripts/covers/render.py events/{year}/{event}/cover-configs.md \
  --browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --font /path/to/LXGWWenKai-Regular.ttf
```

可传多个配置文件；`--out-dir` 把成品输出到其他目录，`--preview-dir` 按成品文件名保存可独立打开的 HTML，`--theme` 覆盖配置。字体只读本机文件，不自动下载。预览 HTML 含嵌入字体与照片，放在仓库外。

输出前检查文字溢出、标题与纸卡碰撞和页眉重叠；出现问题调整断行或精简文字，不自动缩小字号。JPEG 转 RGB，q88、optimize、progressive；超 400 KB 依次尝试 q85 / 4:2:0，超 500 KB 报错，不缩小规定尺寸。

## 真实照片

提供本人确认可用的原图，在原有 JSON 中增加：

```json
{
  "photo": "assets/source-photo.jpg",
  "photo_position": [50, 40]
}
```

这两个字段是对完整配置的补充，不能单独作为配置。照片替换第一张纸卡，保持原图内容，用 `photo_position`（横、纵焦点百分比）控制裁切。输出后需检查是否裁掉人脸、主体或必须保留的细节；不以占位图冒充真实照片。照片能否入库按参与者授权与隐私要求判断。

## 新主题

当前实现 `collage`。以后新增 `themes/{name}.css`，通过配置或 `--theme {name}` 选择；字体、配色、纸卡质感等视觉规则放在主题文件。尺寸、检查、截图和压缩逻辑共享。若新主题确实需要不同结构，再增加对应布局，不提前堆积未使用的模板。

视频号同题图集可复用小红书竖版封面；正文与内页继续使用文字卡渲染器。图集成品存仓库外，封面按本篇配置存入 `assets/`。

## 验证

```bash
python3 scripts/covers/test_render.py --font /path/to/LXGWWenKai-Regular.ttf [--browser /path/to/chrome]
python3 scripts/check-content.py
```

集成检查包含横竖尺寸、照片显示、过长文字拒绝和新增 CSS 主题。
