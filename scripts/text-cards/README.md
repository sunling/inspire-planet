# 长文文字卡渲染器

把一篇分页 Markdown 渲染为小红书竖版（1080 × 1440）文字卡 PNG。用 HTML/CSS 排版、浏览器截图，文字精确、可复现。

与 `scripts/render-cards.py` 的分工：

| | `render-cards.py` | `text-cards/render.py` |
|---|---|---|
| 适合 | 大字摘录卡：一页一句大字 + 一行小字 | 需要连续阅读的长文：一位分享者的完整分享稿 |
| 输入 | `xhs-{slug}.md` 的图集脚本 / 逐页 JSON | 分页 Markdown（独占一行 `---` 分页） |
| 依赖 | Pillow | Playwright + 本机 Chrome/Chromium |
| 风格 | 暖纸、毛笔大字 | 启发星球橙、霞鹜文楷正文 |

来源同步自 `sunling-os/tools/xiaohongshu/`，此处只保留启发星球的主题与默认值。

## 分页 Markdown

```markdown
---
episode: 第 23 期
date: 2026-06-12
speaker: 孙玲
---

# 自我欺骗的边界

当我说"所有努力都有意义"，我是在乐观，还是在自我欺骗？

---

## 第一页标题

正文自然段，100–150 字为宜，超过约 165 字会溢出报错。

---

> 整页只有一个引用块时成为引用页：原文里已有的一句话，单独放大。

---

## 清单页

- 整页只有列表项时成为清单页
- 只在原文本来就是并列短句时使用
```

第一页自动成为封面（橙色底 `#fff9f0`、大标题、无页码）。frontmatter 均可选：

| 字段 | 位置 | 默认 |
|---|---|---|
| `series` | 页眉左 | `启发星球` |
| `episode` | 页眉左，`series · episode` | 无 |
| `date` | 封面底部，显示为 `YYYY年M月D日` | 无 |
| `speaker` | 页眉右、封面底部 | 无；缺省用 `signature` |
| `signature` | 同上 | `启发星球笔记` |
| `site` | 封面右下、末页左下 | `inspireplanet.cc`；写 `site:` 留空可隐藏 |

一组 7–11 页里穿插 1–2 个引用页即可，不连续两页引用，也不为了节奏造一句原文没有的话。

## 运行

```bash
python3 -m pip install -r scripts/text-cards/requirements.txt
python3 -m playwright install chromium          # 或用 --browser 指定本机 Chrome
python3 scripts/text-cards/render.py <分页稿.md> <空输出目录> \
  --browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --contact-sheet /tmp/sheet.png                 # 临时总览图，便于检查
```

- 字体：优先读 `~/.cache/inspireplanet-fonts/LXGWWenKai-Regular.ttf`（`render-cards.py` 首次运行会下载到这里），也查 `~/Library/Fonts/`；都没有时用 `--font` 指定。
- 输出目录必须为空；先渲染到临时目录检查，再复制到 `events/{year}/{YYYYMMDD}-epXX/assets/`。渲染器会拒绝溢出和页眉重叠的页面；遇到溢出先拆页或删重复，不缩字号。
- 卡片图是产物，不提交进仓库；仓库只保留分页 Markdown。
- 微调配色：`--accent`、`--background`、`--cover-background`。

改动渲染器后运行：

```bash
python3 scripts/text-cards/test_render.py --font <字体.ttf> [--browser <浏览器路径>]
```
