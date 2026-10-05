#!/usr/bin/env python3
"""启发星球 · 卡片渲染器

把"图集脚本"(逐页 JSON) 渲染成小红书竖版卡片 PNG。
不依赖浏览器：只用 Pillow + 一款中文字体，输出文字精确、可复现、零模型开销。

用法：
    python3 scripts/render-cards.py pages.json out_dir/                    # 逐页 JSON
    python3 scripts/render-cards.py events/{年}/{期}/xiaohongshu.md out_dir/  # 直接读图集脚本 md

pages.json 是一个数组，每项对应一张卡：

    [
      {
        "meta":    "2026EP39 · 启发星球",   # 左上角小字，可省
        "big":     "一个人在夏威夷\\n开了一整天车",  # 大字，\\n 强制换行
        "small":   "带着害怕，也在路上",       # 小字，可省
        "big_font":"brush",                # brush(默认) | kai | klee
        "big_size":100,                    # 可选，默认 90
        "sm_size": 46,                     # 可选，默认 46
        "theme":   "dark",                 # 可选，深色原声页
        "footer":  "启发星球笔记",           # 可选
        "page":    "09"                    # 可选，右下角页码
      }
    ]

字体首次运行会自动下载到字体目录（默认 ~/.cache/inspireplanet-fonts，
可用环境变量 INSPIRE_FONTS_DIR 覆盖）。三款字体均为 OFL 开源许可。
"""
import argparse
import json
import os
import random
import sys
import urllib.request

W, H = 1080, 1440  # 小红书竖版 3:4
MARGIN = 100

FONT_URLS = {
    "LXGWWenKai-Regular.ttf": "https://github.com/lxgw/LxgwWenKai/releases/download/v1.520/LXGWWenKai-Regular.ttf",
    "LXGWWenKai-Medium.ttf": "https://github.com/lxgw/LxgwWenKai/releases/download/v1.520/LXGWWenKai-Medium.ttf",
    "MaShanZheng-Regular.ttf": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/mashanzheng/MaShanZheng-Regular.ttf",
    "KleeOne-Regular.ttf": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/kleeone/KleeOne-Regular.ttf",
}

FONT_DIR = os.environ.get("INSPIRE_FONTS_DIR",
                          os.path.expanduser("~/.cache/inspireplanet-fonts"))

FONT_FILES = {
    "kai": "LXGWWenKai-Medium.ttf",   # 霞鹜文楷 Medium：大字（默认）
    "kai_r": "LXGWWenKai-Regular.ttf",  # 霞鹜文楷：小字/正文
    "brush": "MaShanZheng-Regular.ttf",  # 马善政毛笔楷书：手写感大字
    "klee": "KleeOne-Regular.ttf",    # Klee One：楷书大字
}


def ensure_fonts():
    """确保所需字体存在，缺失则下载。返回 {逻辑名: 绝对路径}。"""
    os.makedirs(FONT_DIR, exist_ok=True)
    paths = {}
    for key, fname in FONT_FILES.items():
        path = os.path.join(FONT_DIR, fname)
        if not os.path.exists(path) or os.path.getsize(path) < 100_000:
            url = FONT_URLS[fname]
            sys.stderr.write(f"下载字体 {fname} ...\n")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:  # 网络不可用时给出可操作的提示
                sys.exit(f"字体 {fname} 缺失且下载失败：{e}\n"
                         f"请手动下载后放入 {FONT_DIR}（或设置 INSPIRE_FONTS_DIR）。")
        paths[key] = path
    return paths


def paper(size, warm=True):
    """暖纸底：竖向渐变 + 柔和水彩斑（模糊），营造"摘录本"的质感。"""
    top, bot = ((250, 246, 239), (241, 231, 214)) if warm else ((44, 40, 36), (28, 26, 24))
    img = Image.new("RGB", size, top)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        t = y / size[1]
        d.line([(0, y), (size[0], y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    if warm:
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        random.seed(7)
        for _ in range(7):
            cx, cy = random.randint(0, W), random.randint(0, H)
            r = random.randint(220, 460)
            col = random.choice([(236, 214, 180, 70), (244, 226, 196, 60), (228, 208, 176, 55)])
            ld.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
        layer = layer.filter(ImageFilter.GaussianBlur(90))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return img


def wrap(draw, text, font, max_w):
    """按像素宽度折行；逐字符判断，适配中文（无空格）。"""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if draw.textlength(cur + ch, font=font) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def render(page, out, fonts):
    dark = page.get("theme") == "dark"
    img = paper((W, H), warm=not dark)
    ink = (250, 246, 240) if dark else (60, 50, 40)
    sub = (196, 186, 172) if dark else (140, 124, 104)
    accent = (198, 150, 96) if dark else (196, 142, 84)
    draw = ImageDraw.Draw(img)
    maxw = W - MARGIN * 2

    f_meta = ImageFont.truetype(fonts["kai_r"], 34)
    f_big = ImageFont.truetype(fonts.get(page.get("big_font", "brush"), fonts["brush"]),
                               page.get("big_size", 90))
    f_sm = ImageFont.truetype(fonts["kai_r"], page.get("sm_size", 46))

    if page.get("meta"):
        draw.text((MARGIN, 92), page["meta"], font=f_meta, fill=sub)

    big_lines = wrap(draw, page["big"], f_big, maxw)
    sm_lines = wrap(draw, page.get("small", ""), f_sm, maxw)
    lh_b = int(page.get("big_size", 90) * 1.34)
    lh_s = int(page.get("sm_size", 46) * 1.72)
    block = len(big_lines) * lh_b + (44 if sm_lines else 0) + len(sm_lines) * lh_s
    y = (H - block) // 2 - 30

    for ln in big_lines:
        draw.text((MARGIN, y), ln, font=f_big, fill=ink)
        y += lh_b
    if sm_lines:
        y += 34
        draw.line([(MARGIN, y - 6), (MARGIN + 70, y - 6)], fill=accent, width=4)
        y += 26
        for ln in sm_lines:
            draw.text((MARGIN, y), ln, font=f_sm, fill=sub)
            y += lh_s

    draw.text((MARGIN, H - 104), page.get("footer", "启发星球笔记"), font=f_meta, fill=sub)
    if page.get("page"):
        t = str(page["page"])
        draw.text((W - MARGIN - draw.textlength(t, font=f_meta), H - 104),
                  t, font=f_meta, fill=sub)
    img.save(out, "PNG")
    return out


FIELD_MAP = {
    "左上署名": "meta",
    "主标题": "big",
    "图上大字": "big",
    "副标题": "small",
    "小字": "small",
}


def slug(text):
    keep = "".join(c for c in text if c.isalnum() or c in "-_")
    return (keep or "post")[:40]


def parse_md(text):
    """从 xiaohongshu.md 解析出 [(篇名, [页, ...]), ...]。

    识别约定格式：`### 图集脚本` 开一节，`#### 第 N 页` 开一页，
    页内用 `- 图上大字：` / `- 小字：` / `- 左上署名：` / `- 主标题：` / `- 副标题：`。
    页标题里含"原声"时默认用深色主题，也可用 `- 主题：dark` 显式指定。
    """
    groups, pages, page = [], [], None
    title, in_pages, last_key = "", False, None

    def close_page():
        nonlocal page
        if page and (page.get("big") or page.get("small")):
            pages.append(page)
        page = None

    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("#### "):
            if in_pages:
                close_page()
                page = {"big": "", "small": "", "_hint_dark": "原声" in s}
            continue
        if s.startswith("### "):
            if in_pages:
                close_page()
                if pages:
                    groups.append((title, pages))
                pages = []
            in_pages = s.startswith("### 图集脚本")
            continue
        if s.startswith("## "):
            if in_pages:
                close_page()
                if pages:
                    groups.append((title, pages))
            pages, in_pages = [], False
            title = s[3:].strip()
            continue
        if not in_pages or page is None or s.startswith(">"):
            continue
        if s.startswith("- ") and "：" in s:
            key, val = s[2:].split("：", 1)
            key, val = key.strip(), val.strip()
            last_key = key
            if key == "图片建议":
                continue
            if key == "主题":
                page["theme"] = val
            elif key == "大字字体":
                page["big_font"] = val
            elif key in FIELD_MAP:
                field = FIELD_MAP[key]
                page[field] = (page.get(field, "") + "\n" + val).strip() if page.get(field) else val
        elif s and last_key in FIELD_MAP:
            field = FIELD_MAP[last_key]
            page[field] = page.get(field, "") + s

    close_page()
    if pages:
        groups.append((title, pages))
    for _, pgs in groups:
        for p in pgs:
            if p.pop("_hint_dark", False) and "theme" not in p:
                p["theme"] = "dark"
    return [(t, p) for t, p in groups if p]


def main():
    ap = argparse.ArgumentParser(description="把图集脚本（JSON 或 xiaohongshu.md）渲染成卡片 PNG")
    ap.add_argument("pages", help="逐页 JSON，或 xiaohongshu.md")
    ap.add_argument("out_dir", help="输出目录")
    args = ap.parse_args()

    global Image, ImageDraw, ImageFont, ImageFilter
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter  # noqa: F401
    except ImportError:
        sys.exit("缺少 Pillow：pip install pillow")

    if args.pages.lower().endswith(".md"):
        groups = parse_md(open(args.pages, encoding="utf-8").read())
        if not groups:
            sys.exit("没从 md 里解析到图集脚本；需要 `### 图集脚本` / `#### 第 N 页` / `- 图上大字：` 这样的格式。")
    else:
        groups = [("", json.load(open(args.pages, encoding="utf-8")))]

    fonts = ensure_fonts()
    os.makedirs(args.out_dir, exist_ok=True)
    total = 0
    for gi, (title, pages) in enumerate(groups, 1):
        sub = os.path.join(args.out_dir, f"{gi:02d}-{slug(title)}") if len(groups) > 1 else args.out_dir
        os.makedirs(sub, exist_ok=True)
        for i, page in enumerate(pages, 1):
            page.setdefault("page", f"{i:02d}")
            render(page, os.path.join(sub, f"{i:02d}.png"), fonts)
            total += 1
        print(f"{title or 'pages'}: {len(pages)} 张 -> {sub}")
    print(f"共 {total} 张")


if __name__ == "__main__":
    import PIL  # noqa: F401
    from PIL import Image, ImageDraw, ImageFont, ImageFilter  # noqa: F401
    main()
