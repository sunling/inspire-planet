#!/usr/bin/env python3
"""启发星球 · 长文文字卡渲染器

把分页 Markdown 渲染为 1080 x 1440 的小红书竖版文字卡 PNG（HTML/CSS + 浏览器截图）。
与 scripts/render-cards.py（大字摘录卡）互补：这里处理需要连续阅读的长文，
例如一位分享者的完整分享稿。页型从普通 Markdown 推断：第一页为封面，
整页只有 `>` 引用块时为引用页，整页只有 `-` 列表项时为清单页，其余为正文页。

frontmatter（均可选）：
    series:  启发星球            # 页眉左，默认 启发星球
    episode: 第 23 期            # 页眉左，与 series 以 · 连接
    date:    2026-06-12          # 封面底部显示为 2026年6月12日
    speaker: 孙玲                # 页眉右与封面底部；缺省为 signature
    signature: 启发星球笔记      # 落款，默认 启发星球笔记
    site:    inspireplanet.cc    # 封面与末页；写 site: 留空可隐藏，默认 inspireplanet.cc
"""
import argparse
import base64
import html
import io
import json
import os
import re
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent

def parse_document(path: Path) -> tuple[dict[str, str], list[str]]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    meta: dict[str, str] = {}
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end < 0:
            raise ValueError("frontmatter 缺少结束分隔线 ---")
        for raw in text[4:end].splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            if ":" not in raw:
                raise ValueError(f"无法解析 frontmatter：{raw}")
            key, value = raw.split(":", 1)
            meta[key.strip()] = value.strip().strip('"\'')
        text = text[end + 5 :].strip()
    pages = [p.strip() for p in re.split(r"(?m)^---\s*$", text) if p.strip()]
    if not pages:
        raise ValueError("没有找到可渲染的页面")
    return meta, pages


def clean_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def parse_page(page: str) -> tuple[str, str, list[str]]:
    """Return (kind, title, items). kind is text, quote or list."""
    lines = page.splitlines()
    title = ""
    if lines and re.match(r"^#{1,2}\s+", lines[0]):
        title = clean_markdown(re.sub(r"^#{1,2}\s+", "", lines.pop(0)))
    body = "\n".join(lines).strip()
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body) if b.strip()]
    if blocks and all(all(l.startswith(">") for l in b.splitlines()) for b in blocks):
        items = [clean_markdown(" ".join(l.lstrip("> ").strip() for l in b.splitlines())) for b in blocks]
        return "quote", title, items
    item_lines = [l for l in body.splitlines() if l.strip()]
    if item_lines and all(re.match(r"^[-*]\s+", l) for l in item_lines):
        items = [clean_markdown(re.sub(r"^[-*]\s+", "", l)) for l in item_lines]
        return "list", title, items
    paragraphs = [clean_markdown(b.replace("\n", " ")) for b in blocks]
    return "text", title, paragraphs



def find_font(explicit=None):
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise ValueError(f"字体不存在：{path}")
        return path
    font_dir = Path(os.environ.get('INSPIRE_FONTS_DIR', Path.home() / '.cache/inspireplanet-fonts'))
    candidates = [font_dir / 'LXGWWenKai-Regular.ttf',
                  HERE / 'LXGWWenKai-Regular.ttf',
                  Path.home() / 'Library/Fonts/LXGWWenKai-Regular.ttf',
                  Path.home() / '.local/share/fonts/LXGWWenKai-Regular.ttf',
                  Path('/usr/share/fonts/truetype/LXGWWenKai-Regular.ttf'),
                  Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/LXGWWenKai-Regular.ttf']
    for path in candidates:
        if path.is_file():
            return path
    raise ValueError('未找到 LXGWWenKai-Regular.ttf；先运行一次 scripts/render-cards.py 自动下载，或用 --font 指定本地字体')


def font_uri(path):
    data = path.read_bytes()
    if path.suffix.lower() == '.ttc':
        from fontTools.ttLib import TTCollection
        collection = TTCollection(path)
        face = collection.fonts[0]
        for candidate in collection.fonts:
            if any(n.toUnicode().lower() == 'zh-cn' for n in candidate['name'].names if n.nameID == 10):
                face = candidate
                break
        buffer = io.BytesIO()
        face.save(buffer)
        data = buffer.getvalue()
    return 'data:font/ttf;base64,' + base64.b64encode(data).decode()


def format_date(value: str) -> str:
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})', value)
    return f'{m.group(1)}年{int(m.group(2))}月{int(m.group(3))}日' if m else value


def build(source, font, accent='#ff5a36', background='#ffffff', cover_background='#fff9f0'):
    for color in (accent, background, cover_background):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('颜色必须为 #RRGGBB')
    meta, pages = parse_document(Path(source))
    date = meta.get('date', '')
    episode = meta.get('episode', '')
    site = meta.get('site', 'inspireplanet.cc')
    series = meta.get('series', '启发星球')
    label = ' · '.join(x for x in (series, episode) if x)
    cover_date = format_date(date)
    signature = meta.get('speaker') or meta.get('signature', '启发星球笔记')
    header = f'<header><span class="label">{html.escape(label)}</span><span class="signature">{html.escape(signature)}</span></header>'
    cards = []
    for i, raw in enumerate(pages, 1):
        kind, title, items = parse_page(raw)
        heading = f'<h1>{html.escape(title)}</h1>' if title else ''
        if kind == 'list':
            body = '<ul>' + ''.join('<li>' + html.escape(x) + '</li>' for x in items) + '</ul>'
        else:
            body = ''.join('<p>' + html.escape(x) + '</p>' for x in items)
        if i == 1:
            left = ' · '.join(x for x in (signature, cover_date) if x)
            footer = f'<footer><span>{html.escape(left)}</span><span class="site">{html.escape(site)}</span></footer>'
            cards.append(f'<section class="card cover">{header}<main>{heading}{body}</main>{footer}</section>')
        else:
            site_span = f'<span class="site">{html.escape(site)}</span>' if site and i == len(pages) else '<span></span>'
            footer = f'<footer>{site_span}<span>{i:02} / {len(pages):02}</span></footer>'
            cards.append(f'<section class="card {kind}">{header}<main>{heading}{body}</main>{footer}</section>')
    css = (HERE / 'theme.css').read_text()
    css = f':root{{--accent:{accent};--background:{background};--cover-background:{cover_background};}}\n' + css
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; font-src data:; style-src \'unsafe-inline\'"><style>@font-face{font-family:LocalChinese;src:url(' + font_uri(font) + ')}' + css + '</style><body>' + ''.join(cards) + '</body></html>'


def render(source, font, out, browser_path=None, preview=None, contact_sheet=None,
           accent='#ff5a36', background='#ffffff', cover_background='#fff9f0'):
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('输出目录必须为空，请先渲染到临时目录再替换本贴文图片')
    document = build(source, find_font(font), accent, background, cover_background)
    external = []
    with sync_playwright() as pw:
        options = {'executable_path': str(browser_path)} if browser_path else {}
        browser = pw.chromium.launch(**options)
        try:
            page = browser.new_page(viewport={'width':1120, 'height':1480}, device_scale_factor=1)
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
                raise ValueError('页面溢出或页眉重叠：' + json.dumps(checks))
            if external:
                raise ValueError('检测到外部请求：' + str(external))
            out.mkdir(parents=True, exist_ok=True)
            for i, card in enumerate(page.locator('.card').all(), 1):
                card.screenshot(path=str(out / f'{i:02}.png'))
        finally:
            browser.close()
    if preview:
        preview = Path(preview)
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_text(document, encoding='utf-8')
    if contact_sheet:
        files = sorted(out.glob('[0-9][0-9].png'))
        columns = min(5, len(files))
        sheet = Image.new('RGB', (columns*270, ((len(files)+columns-1)//columns)*360), '#e8e5e1')
        for i, path in enumerate(files):
            with Image.open(path) as im:
                sheet.paste(im.resize((270,360)), ((i%columns)*270,(i//columns)*360))
        contact_sheet = Path(contact_sheet)
        contact_sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(contact_sheet)
    result = {'cards': checks, 'external_requests': external}
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--font', type=Path)
    parser.add_argument('--browser', type=Path, help='Optional local Chrome/Chromium executable')
    parser.add_argument('--preview', type=Path, help='Optional HTML preview outside final images directory')
    parser.add_argument('--contact-sheet', type=Path, help='Optional temporary layout overview')
    parser.add_argument('--accent', default='#ff5a36')
    parser.add_argument('--background', default='#ffffff')
    parser.add_argument('--cover-background', default='#fff9f0', help='Cover page background colour')
    args = parser.parse_args()
    render(args.source, args.font, args.output, args.browser, args.preview, args.contact_sheet, args.accent, args.background, args.cover_background)
