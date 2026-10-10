# 文字卡渲染器

首图内容和整套主题都写在图文脚本中，用户确认后一次生成首图与内页。`assets/cover-configs.md` 仅用于公众号封面，本工具的首图不再由独立封面图片替换。

把文字稿渲染为小红书 / 视频号竖版（1080 × 1440）卡片图。HTML/CSS 排版、浏览器截图，文字精确、可复现；主题是纯 CSS，不同分享者、不同栏目可以用不同主题。

## 两种输入

**1. 图集脚本**（`events/.../xhs-{slug}.md`、`sph-{slug}.md`，`inspireplanet-xhs` / `inspireplanet-sph` Skill 的产物）。标题含「脚本」的小节开始图集脚本，其下更深一级、形如「第 N 页」的标题分页；**层级不固定，按语义识别**（`## 图集脚本 / ### 第 N 页` 与旧的 `### / ####` 都可以）

```markdown
## 图集脚本

### 第 1 页（封面）
- 主标题：大字
- 副标题：一行小字
- 左上署名：启发星球 · 第 39 期

### 第 2 页
- 图上大字：一句摘录
- 小字：一两行补充

### 第 7 页（原声）
- 图上大字：页标题含“原声”自动变深色页，也可写 `- 主题：dark`
```

页眉页脚文字：`## 图集脚本` 之后、第一页之前可写篇目级设置行，字段与下面 frontmatter 一一对应：

```markdown
## 图集脚本
- 分享者：李影          → speaker
- 日期：2026-10-03     → date
- 期数：第 39 期        → episode
- 栏目：/ 署名：/ 站点：/ 主题：   → series / signature / site / theme
```

文件开头也可以放一段 frontmatter 对整个文件生效；优先级：命令行 `--theme` > 篇目级设置 > 文件 frontmatter > 默认值。一个文件里有多个 `##` 篇目时，各自输出到 `out_dir/01-{篇名}/`、`02-.../`，每篇可以有自己的分享者和主题。默认主题 `paper`。

**2. 分页 Markdown**（一位分享者的完整分享稿，可连续阅读）

```markdown
---
episode: 第 23 期
date: 2026-06-12
speaker: 孙玲
---

# 封面标题

封面副题一两句。

---

## 第一页标题

正文自然段，100–150 字为宜，超过约 165 字会溢出报错。

---

> 整页只有引用块时成为引用页。

---

- 整页只有列表项时成为清单页
- 只在原文本来就是并列短句时使用
```

第一页自动成为封面（无页码）。默认主题 `inspire`。frontmatter 均可选：

| 字段 | 位置 | 默认 |
|---|---|---|
| `theme` | 主题名 | `inspire` |
| `series` | 页眉左 | `启发星球` |
| `episode` | 页眉左，`series · episode` | 无 |
| `date` | 封面底部，`YYYY年M月D日` | 无 |
| `speaker` | 页眉右、封面底部 | 无；缺省用 `signature` |
| `signature` | 同上 | `启发星球笔记` |
| `site` | 封面右下、末页左下 | `inspireplanet.cc`；写 `site:` 留空可隐藏 |

## 主题

| 主题 | 风格 | 适合 |
|---|---|---|
| `inspire` | 启发星球橙（`#ff5a36` / 封面 `#fff9f0`），霞鹜文楷 | 官方账号的连续长文 |
| `paper` | 暖纸摘录风：纸色渐变、马善政毛笔大字、原声页深色 | 一页一句的大字摘录卡 |

选择方式：frontmatter `theme: paper` 或命令行 `--theme paper`；都不写时按输入类型取默认。

整套主题决定封面和内页的标题／正文字体与配色。`paper`：马善政标题 + 霞鹜文楷正文；`inspire`：标题与正文都用霞鹜文楷。首图只调整字号与版式，原声页可使用同主题深色版本。用户指定字体时先选对应主题；`--font` 只覆盖正文字体，不能据此声称已更换 `paper` 的毛笔标题字体。

新增主题：复制 `theme-paper.css` 为 `theme-{name}.css`，改 `:root` 里的变量（`--accent --background --cover-background --ink --muted --muted-strong --rule`）和少量规则即可，`theme.css` 只负责版式结构，不要改它来换色。主题名只用小写字母、数字和连字符。临时微调用 `--accent`、`--background`、`--cover-background`。

## 运行

```bash
python3 -m pip install -r scripts/text-cards/requirements.txt
python3 -m playwright install chromium          # 或用 --browser 指定本机 Chrome

python3 scripts/text-cards/render.py events/{year}/{YYYYMMDD}-epXX/xhs-{slug}.md out_dir/ \
  --browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --contact-sheet /tmp/sheet.png                 # 临时总览图，便于检查
# 可选：--theme inspire|paper   --jpeg（输出 JPEG q88 而非 PNG）
```

- 字体首次运行自动下载到 `~/.cache/inspireplanet-fonts/`（`INSPIRE_FONTS_DIR` 可改；也会查 `~/Library/Fonts/`、`~/.local/share/fonts/`）；离线时用 `--font` 指定霞鹜文楷。
- 输出目录必须为空。渲染器会拒绝溢出和页眉重叠的页面；遇到溢出先拆页或删重复，不缩字号。
- 整套图卡包含 `01.jpg` 首图，不单独复制首图到本期 `assets/`。同一批渲染的图集、总览与 ZIP 使用仓库外一个输出目录；两渠道图片脚本与主题完全一致时可复用整套成品。
- 卡片图是产物，不提交进仓库；仓库只保留文字稿及其主题设置。

改动渲染器或主题后运行：

```bash
python3 scripts/text-cards/test_render.py --font <字体.ttf> [--browser <浏览器路径>]
```
