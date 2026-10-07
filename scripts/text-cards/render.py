#!/usr/bin/env python3
"""启发星球 · 文字卡渲染器

把文字稿渲染为 1080 x 1440 的小红书 / 视频号竖版卡片（HTML/CSS + 浏览器截图）。

支持两种输入：
  1. 分页 Markdown：独占一行 `---` 分页，第一页为封面；整页只有 `>` 时为引用页，
     整页只有 `-` 列表项时为清单页，其余为正文页。适合可连续阅读的长文。
  2. 图集脚本（`xhs-{slug}.md` / `sph-{slug}.md`）：标题含「脚本」的小节（如 `## 图集脚本`）
     下按更深一级的 `### 第 N 页` 分页，层级不固定、按语义识别；页内 `- 图上大字：` / `- 小字：` /
     `- 左上署名：` / `- 主标题：` / `- 副标题：`；页标题含“原声”或写 `- 主题：dark` 时为深色页。
     一个文件里多个篇目（各自带脚本小节）各自输出到子目录。
     页眉页脚文字：文件开头 frontmatter（同下）对全文件生效；脚本小节下、第一页之前可写
     篇目级设置 `- 分享者：` `- 日期：` `- 期数：` `- 栏目：` `- 署名：` `- 站点：` `- 主题：` 覆盖。

主题是纯 CSS：`theme-{name}.css` 覆盖 `theme.css` 的变量与少量规则。
  inspire  启发星球橙（分页 Markdown 的默认）
  paper    暖纸摘录风，毛笔大字，深色原声页（图集脚本的默认）
用 frontmatter `theme:` 或 `--theme` 选择；不同分享者可以用不同主题。

frontmatter（分页 Markdown，均可选）：
    theme / series / episode / date / speaker / signature / site
字体缺失时自动下载到 ~/.cache/inspireplanet-fonts（可用 INSPIRE_FONTS_DIR 覆盖）。
"""
import argparse
import base64
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FONT_DIR = Path(os.environ.get('INSPIRE_FONTS_DIR', Path.home() / '.cache/inspireplanet-fonts'))
FONTS = {  # CSS font-family -> (file, url); all OFL
    'LocalChinese': ('LXGWWenKai-Regular.ttf',
                     'https://github.com/lxgw/LxgwWenKai/releases/download/v1.520/LXGWWenKai-Regular.ttf'),
    'BrushChinese': ('MaShanZheng-Regular.ttf',
                     'https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/mashanzheng/MaShanZheng-Regular.ttf'),
}
SITE_DEFAULT = 'inspireplanet.cc'


# ---------- input: paged Markdown ----------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end < 0:
            raise ValueError('frontmatter 缺少结束分隔线 ---')
        for raw in text[4:end].splitlines():
            if not raw.strip() or raw.lstrip().startswith('#'):
                continue
            if ':' not in raw:
                raise ValueError(f'无法解析 frontmatter：{raw}')
            key, value = raw.split(':', 1)
            meta[key.strip()] = value.strip().strip('"\'')
        text = text[end + 5:].strip()
    return meta, text


def clean_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


def parse_page(page: str) -> dict:
    """Return {kind, title, items}. kind is text, quote or list."""
    lines = page.strip().splitlines()
    title = ''
    if lines and re.match(r'^#{1,2}\s+', lines[0]):
        title = clean_markdown(re.sub(r'^#{1,2}\s+', '', lines.pop(0)))
    body = '\n'.join(lines).strip()
    blocks = [b.strip() for b in re.split(r'\n\s*\n', body) if b.strip()]
    if blocks and all(all(l.startswith('>') for l in b.splitlines()) for b in blocks):
        items = [clean_markdown(' '.join(l.lstrip('> ').strip() for l in b.splitlines())) for b in blocks]
        return {'kind': 'quote', 'title': title, 'items': items}
    item_lines = [l for l in body.splitlines() if l.strip()]
    if item_lines and all(re.match(r'^[-*]\s+', l) for l in item_lines):
        return {'kind': 'list', 'title': title, 'items': [clean_markdown(re.sub(r'^[-*]\s+', '', l)) for l in item_lines]}
    return {'kind': 'text', 'title': title, 'items': [clean_markdown(b.replace('\n', ' ')) for b in blocks]}


def load_paged(text: str) -> tuple[dict, list[dict]]:
    meta, body = parse_frontmatter(text)
    pages = [parse_page(p) for p in re.split(r'(?m)^---\s*$', body) if p.strip()]
    if not pages:
        raise ValueError('没有找到可渲染的页面')
    return meta, pages


# ---------- input: 图集脚本 ----------

FIELD_MAP = {'左上署名': 'meta', '主标题': 'big', '图上大字': 'big', '副标题': 'small', '小字': 'small'}
# 图集脚本里页面之外的设置行（脚本标题与第一个「第 N 页」之间），对应 frontmatter 字段
META_MAP = {'主题': 'theme', '栏目': 'series', '期数': 'episode', '日期': 'date',
            '分享者': 'speaker', '署名': 'signature', '站点': 'site'}


def load_script(text: str) -> list[tuple[str, list[dict], dict]]:
    """Parse 图集脚本 sections into [(篇名, [page, ...], 篇目级设置), ...].

    标题按语义识别，不依赖固定层级：标题含「脚本」开一节；节内更深层级、形如「第 N 页」的
    标题分页；篇目名取脚本标题之上最近一个更浅层级的标题。既支持扁平的
    `# 篇名 / ## 图集脚本 / ### 第 N 页`，也兼容旧的 `## 篇名 / ### 图集脚本 / #### 第 N 页`。
    """
    groups, pages, page, gmeta = [], [], None, {}
    title, in_pages, last_key = '', False, None
    script_level, headings = 0, []  # headings: [(level, text)] seen so far

    def close_page():
        nonlocal page
        if page and (page.get('big') or page.get('small')):
            pages.append(page)
        page = None

    def close_group():
        nonlocal pages, gmeta, in_pages
        close_page()
        if pages:
            groups.append((title, pages, gmeta))
        pages, gmeta, in_pages = [], {}, False

    for raw in text.splitlines():
        s = raw.strip()
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            level, text_ = len(m.group(1)), m.group(2).strip()
            if in_pages and level > script_level and re.match(r'^第\s*\d+\s*页', text_):
                close_page()
                page = {'big': '', 'small': '', 'dark': '原声' in text_}
                continue
            if in_pages and level > script_level:
                continue  # 脚本节内的其他子标题，忽略
            if in_pages:
                close_group()
            if '脚本' in text_:
                in_pages, script_level = True, level
                title = next((t for l, t in reversed(headings) if l < level), '')
            else:
                headings.append((level, text_))
            continue
        if not in_pages or s.startswith('>'):
            continue
        if page is None:
            if s.startswith('- ') and '：' in s:
                key, val = (x.strip() for x in s[2:].split('：', 1))
                if key in META_MAP:
                    gmeta[META_MAP[key]] = val
            continue
        if s.startswith('- ') and '：' in s:
            key, val = (x.strip() for x in s[2:].split('：', 1))
            last_key = key
            if key == '主题':
                page['dark'] = val == 'dark'
            elif key in FIELD_MAP:
                f = FIELD_MAP[key]
                page[f] = (page.get(f, '') + '\n' + val).strip() if page.get(f) else val
        elif s and last_key in FIELD_MAP:
            f = FIELD_MAP[last_key]
            page[f] = page.get(f, '') + s
    close_group()
    out = []
    for name, pgs, gm in groups:
        out.append((name, [{'kind': 'text', 'title': p['big'].replace('\n', ' '),
                            'items': [x for x in p['small'].split('\n') if x.strip()],
                            'dark': p.get('dark', False), 'meta': p.get('meta', '')} for p in pgs], gm))
    return [(n, p, m) for n, p, m in out if p]


# ---------- fonts ----------

def ensure_font(family: str, explicit=None) -> Path:
    file, url = FONTS[family]
    if explicit and family == 'LocalChinese':
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f'字体不存在：{path}')
        return path
    for path in (FONT_DIR / file, HERE / file, Path.home() / 'Library/Fonts' / file,
                 Path.home() / '.local/share/fonts' / file):
        if path.is_file() and path.stat().st_size > 100_000:
            return path
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    target = FONT_DIR / file
    sys.stderr.write(f'下载字体 {file} ...\n')
    try:
        urllib.request.urlretrieve(url, target)
    except Exception as e:
        raise ValueError(f'字体 {file} 缺失且下载失败：{e}\n请手动下载后放入 {FONT_DIR}（或设置 INSPIRE_FONTS_DIR）')
    return target


def font_face(family: str, path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    return f'@font-face{{font-family:{family};src:url(data:font/ttf;base64,{data})}}'


# ---------- build ----------

def format_date(value: str) -> str:
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', value)
    return f'{m.group(1)}年{int(m.group(2))}月{int(m.group(3))}日' if m else value


def load_theme(name: str) -> str:
    if not re.fullmatch(r'[a-z0-9-]+', name):
        raise ValueError('theme 只能使用小写字母、数字和连字符')
    path = HERE / f'theme-{name}.css'
    if not path.is_file():
        available = ', '.join(sorted(p.stem[6:] for p in HERE.glob('theme-*.css')))
        raise ValueError(f'未找到主题 {name}；可用：{available}')
    return path.read_text()


def build(meta: dict, pages: list[dict], theme: str, font=None,
          accent=None, background=None, cover_background=None) -> str:
    for color in (accent, background, cover_background):
        if color and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('颜色必须为 #RRGGBB')
    episode = meta.get('episode', '')
    site = meta.get('site', SITE_DEFAULT)
    series = meta.get('series', '启发星球')
    label = ' · '.join(x for x in (series, episode) if x)
    cover_date = format_date(meta.get('date', ''))
    signature = meta.get('speaker') or meta.get('signature', '启发星球笔记')
    cards = []
    n = len(pages)
    for i, page in enumerate(pages, 1):
        kind, title, items = page['kind'], page['title'], page['items']
        page_label = page.get('meta') or label
        header = (f'<header><span class="label">{html.escape(page_label)}</span>'
                  f'<span class="signature">{html.escape(signature)}</span></header>')
        heading = f'<h1>{html.escape(title)}</h1>' if title else ''
        if kind == 'list':
            body = '<ul>' + ''.join('<li>' + html.escape(x) + '</li>' for x in items) + '</ul>'
        else:
            body = ''.join('<p>' + html.escape(x) + '</p>' for x in items)
        classes = ['card', 'cover' if i == 1 else kind] + (['dark'] if page.get('dark') else [])
        if i == 1:
            left = ' · '.join(x for x in (signature, cover_date) if x)
            footer = f'<footer><span>{html.escape(left)}</span><span class="site">{html.escape(site)}</span></footer>'
        else:
            site_span = f'<span class="site">{html.escape(site)}</span>' if site and i == n else '<span></span>'
            footer = f'<footer>{site_span}<span>{i:02} / {n:02}</span></footer>'
        cards.append(f'<section class="{" ".join(classes)}">{header}<main>{heading}{body}</main>{footer}</section>')
    css = (HERE / 'theme.css').read_text() + '\n' + load_theme(theme)
    overrides = {'--accent': accent, '--background': background, '--cover-background': cover_background}
    override_css = ''.join(f'{k}:{v};' for k, v in overrides.items() if v)
    if override_css:
        css += f'\n:root{{{override_css}}}'
    faces = font_face('LocalChinese', ensure_font('LocalChinese', font))
    if 'BrushChinese' in css:
        faces += font_face('BrushChinese', ensure_font('BrushChinese'))
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; font-src data:; style-src \'unsafe-inline\'">'
            f'<style>{faces}{css}</style><body>{"".join(cards)}</body></html>')


# ---------- render ----------

def screenshot(document: str, out: Path, browser_path=None, jpeg=False) -> list[dict]:
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('输出目录必须为空，请先渲染到临时目录再替换成品')
    external = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({'executable_path': str(browser_path)} if browser_path else {}))
        try:
            page = browser.new_page(viewport={'width': 1120, 'height': 1480}, device_scale_factor=1)
            page.on('request', lambda r: external.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
            page.route('http://**/*', lambda route: route.abort())
            page.route('https://**/*', lambda route: route.abort())
            page.set_content(document)
            page.evaluate('document.fonts.ready')
            checks = page.evaluate("""() => Array.from(document.querySelectorAll('.card')).map(c => {
                const main = c.querySelector('main'), header = c.querySelector('header');
                const spans = Array.from(header.querySelectorAll('span')).filter(s => s.offsetParent !== null);
                const overlap = spans.length > 1 && spans[0].getBoundingClientRect().right + 24 > spans[1].getBoundingClientRect().left;
                return {width:c.offsetWidth,height:c.offsetHeight,kind:c.className.replace('card','').trim(),
                    overflow:main.scrollHeight>main.clientHeight || main.scrollWidth>main.clientWidth,
                    headerOverlap:header.scrollWidth>header.clientWidth || overlap};
            })""")
            if any(c['overflow'] or c['headerOverlap'] for c in checks):
                raise ValueError('页面溢出或页眉重叠：' + json.dumps(checks, ensure_ascii=False))
            if external:
                raise ValueError('检测到外部请求：' + str(external))
            out.mkdir(parents=True, exist_ok=True)
            for i, card in enumerate(page.locator('.card').all(), 1):
                if jpeg:
                    card.screenshot(path=str(out / f'{i:02}.jpg'), type='jpeg', quality=88)
                else:
                    card.screenshot(path=str(out / f'{i:02}.png'))
        finally:
            browser.close()
    return checks


def contact_sheet(out: Path, target: Path) -> None:
    files = sorted(list(out.glob('[0-9][0-9].png')) + list(out.glob('[0-9][0-9].jpg')))
    columns = min(5, len(files))
    sheet = Image.new('RGB', (columns * 270, ((len(files) + columns - 1) // columns) * 360), '#e8e5e1')
    for i, path in enumerate(files):
        with Image.open(path) as im:
            sheet.paste(im.convert('RGB').resize((270, 360)), ((i % columns) * 270, (i // columns) * 360))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target)


def render(source, out, theme=None, font=None, browser_path=None, preview=None, sheet=None,
           accent=None, background=None, cover_background=None, jpeg=False):
    text = Path(source).read_text(encoding='utf-8').replace('\r\n', '\n').strip()
    out = Path(out)
    if re.search(r'^#{1,6}\s+(图集|图片)脚本', text, flags=re.M):
        file_meta, body = parse_frontmatter(text)
        groups = load_script(body)
        if not groups:
            raise ValueError('没从图集脚本解析到页面；需要 `## 图集脚本` / `### 第 N 页` / `- 图上大字：` 这样的格式。')
        default_theme = 'paper'
    else:
        file_meta, pages = load_paged(text)
        groups, default_theme = [('', pages, {})], 'inspire'
    results = []
    for gi, (name, pages, gmeta) in enumerate(groups, 1):
        meta = {**file_meta, **gmeta}  # 文件 frontmatter < 篇目级设置 < 命令行 --theme
        group_theme = theme or meta.get('theme') or default_theme
        slug = re.sub(r'[^\w-]', '', name)[:40] or 'post'
        sub = out / f'{gi:02d}-{slug}' if len(groups) > 1 else out
        document = build(meta, pages, group_theme, font, accent, background, cover_background)
        checks = screenshot(document, sub, browser_path, jpeg)
        if preview:
            p = Path(preview) if len(groups) == 1 else Path(preview).with_name(f'{Path(preview).stem}-{gi:02d}.html')
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(document, encoding='utf-8')
        if sheet:
            s = Path(sheet) if len(groups) == 1 else Path(sheet).with_name(f'{Path(sheet).stem}-{gi:02d}.png')
            contact_sheet(sub, s)
        results.append({'group': name, 'theme': group_theme, 'output': str(sub), 'cards': checks})
    print(json.dumps(results, ensure_ascii=False))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', type=Path, help='分页 Markdown，或 xhs-*.md / sph-*.md 图集脚本')
    parser.add_argument('output', type=Path, help='空输出目录')
    parser.add_argument('--theme', help='inspire | paper | 其他 theme-{name}.css；默认按输入类型')
    parser.add_argument('--font', type=Path, help='覆盖正文字体（LXGWWenKai-Regular.ttf）')
    parser.add_argument('--browser', type=Path, help='本机 Chrome/Chromium 可执行文件')
    parser.add_argument('--preview', type=Path, help='临时 HTML 预览路径')
    parser.add_argument('--contact-sheet', type=Path, help='临时总览图路径')
    parser.add_argument('--accent')
    parser.add_argument('--background')
    parser.add_argument('--cover-background')
    parser.add_argument('--jpeg', action='store_true', help='输出 JPEG（q88）而非 PNG')
    a = parser.parse_args()
    render(a.source, a.output, a.theme, a.font, a.browser, a.preview, a.contact_sheet,
           a.accent, a.background, a.cover_background, a.jpeg)
