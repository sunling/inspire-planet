# HTML 封面渲染

从封面配置 Markdown 生成 HTML，用 Chromium 截图并保存 JPEG。提供 3 种布局与 5 套配色；配置生成时独立随机均衡选择，确认后按选定组合渲染，不调用图像生成模型。复用 `scripts/text-cards/requirements.txt` 的依赖。

## 配置位置

每期用 `events/{year}/{event}/cover/cover-configs.md` 集中保存所有封面的配置与设计信息，按篇目和渠道分节。每节记录对应稿件、成品路径、选定的封面文字、视觉命题，以及一个完整的 `cover-config` JSON 块。配置只在此维护，不在渠道稿中重复保存；复用同一张封面时只记录对应关系。

先生成内容与此配置文件，用户明确确认图文脚本和封面脚本后，再运行渲染命令。

渲染器按文件内的配置顺序生成全部封面。历史稿中的单个配置块仍可直接读取，无需迁移所有历史期。

<!-- 示例放在四重代码块中，避免与真实配置混淆。 -->
````md
<!-- cover-config -->
```json
{
  "layout": "random",
  "theme": "random",
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
- 两组信息表达本篇特有的起点、变化或关系，不套空泛口号；标签、卡片文字也须有内容依据。`value` 建议 2–4 字，`note` 建议 8 字以内。
- `cover/cover-configs.md` 中的 `asset` 和本地照片 `photo` 路径相对本期目录，例如 `assets/recap-cover-liying.jpg`；Markdown 稿件链接相对 `cover/`，例如 `../gzh-liying.md`。历史稿中的配置路径仍相对稿件目录。文件名沿用原渠道规范；同一文件内不能配置重复的成品路径。已有成品时须显式 `--force`。

## 随机选择主题

配置生成后、交用户确认前运行：

```bash
python3 scripts/covers/assign_themes.py events/{year}/{event}/cover/cover-configs.md
```

脚本分别将缺失或为 `"random"` 的 `layout`、`theme` 替换为具体布局和配色，两项独立均衡分配并尽量避免相邻重复；保留已选值。可以只固定其中一项、随机另一项。`--seed 42` 可重现同一批组合；`--reshuffle` 重新抽选全部配置的两项，更新后需重新确认。渲染时不会重新随机，历史稿未指定布局或配色时仍用 `collage`。

## 运行

```bash
python3 -m pip install -r scripts/text-cards/requirements.txt
python3 scripts/covers/render.py events/{year}/{event}/cover/cover-configs.md \
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

这两个字段是对完整配置的补充，不能单独作为配置。照片替换第一组信息区域，保持原图内容，用 `photo_position`（横、纵焦点百分比）控制裁切。输出后需检查是否裁掉人脸、主体或必须保留的细节；不以占位图冒充真实照片。照片能否入库按参与者授权与隐私要求判断。

## 布局与配色

| `layout` | 构图 |
|---|---|
| `collage` | 倾斜的双纸卡，标题与纸卡并置 |
| `editorial` | 杂志分栏，信息以分隔线与段落组织 |
| `signal` | 居中大标题，底部横向注解，通栏分隔 |

布局决定信息结构，`theme` 决定配色及视觉装饰，3 × 5 共 15 种组合。新布局会覆盖配色中的纸卡造型，避免每种风格都出现同一组浮动卡片。


| 主题 | 风格 |
|---|---|
| `collage` | 暖色纸张拼贴、倾斜纸卡 |
| `pop` | 黄、珊瑚、青色撞色，几何色块与卡片硬阴影 |
| `garden` | 草木绿与暖黄，有机弧线与不对称圆角 |
| `blueprint` | 蓝色网格、直角卡片与虚线连接 |
| `night` | 深蓝夜空、轨道圆弧与亮色圆点 |

每种组合都有横版和竖版；核心文字与内容关系仍来自文章。

新增配色使用 `themes/{name}.css`，新增布局使用 `layouts/{name}.css`；同时更新选择池与渲染检查。通过配置中的 `layout`、`theme` 选择组合，`--theme` 可覆盖配色。尺寸、检查、截图和压缩逻辑共享。

视频号同题图集可复用小红书竖版封面；正文与内页继续使用文字卡渲染器。图集成品存仓库外，封面按本篇配置存入 `assets/`。

## 验证

```bash
python3 scripts/covers/test_render.py --font /path/to/LXGWWenKai-Regular.ttf [--browser /path/to/chrome]
python3 scripts/check-content.py
```

集成检查包含横竖尺寸、照片显示、过长文字拒绝和新增 CSS 主题。
