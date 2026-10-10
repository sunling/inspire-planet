#!/usr/bin/env python3
"""Read cover-config JSON blocks from Markdown and render HTML to JPEG."""
import argparse
import base64
import html
import io
import json
import mimetypes
import re
from pathlib import Path
from string import Template
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent


def config_base(source):
    """Episode configs in assets/ keep asset and photo paths event-relative."""
    if source.name == 'cover-configs.md' and source.parent.name in ('assets', 'cover'):
        return source.parent.parent
    return source.parent


def read_configs(source):
    text = source.read_text(encoding='utf-8')
    found = re.findall(r'<!-- cover-config -->\s*```json\s*\n(.*?)\n```', text, re.S)
    if not found:
        raise ValueError(f'{source.name}: expected at least one cover-config JSON block')
    configs = [json.loads(block) for block in found]
    for cfg in configs:
        validate_config(cfg)
    return configs


def read_config(source):
    configs = read_configs(source)
    if len(configs) != 1:
        raise ValueError(f'{source.name}: expected one cover-config JSON block')
    return configs[0]


def validate_config(cfg):
    if not isinstance(cfg, dict):
        raise ValueError('cover config must be an object')
    for field in ('speaker', 'episode', 'date', 'asset'):
        if not isinstance(cfg.get(field), str) or not cfg[field].strip():
            raise ValueError(f'missing {field}')
    lines = cfg.get('headline')
    if not isinstance(lines, list) or not 1 <= len(lines) <= 3 or not all(isinstance(s, str) and s.strip() for s in lines):
        raise ValueError('headline must contain 1–3 nonempty lines')
    tiles = cfg.get('tiles')
    if not isinstance(tiles, list) or len(tiles) != 2:
        raise ValueError('tiles must contain two cards')
    for tile in tiles:
        if not isinstance(tile, dict) or not all(isinstance(tile.get(k), str) for k in ('label', 'value', 'note')):
            raise ValueError('each tile needs label, value, note strings')
    asset = Path(cfg['asset'])
    if asset.is_absolute() or '..' in asset.parts or asset.suffix.lower() != '.jpg':
        raise ValueError('asset must be a relative .jpg path inside the event')
    return cfg


def font_path(explicit):
    choices = [Path(explicit).expanduser()] if explicit else [
        Path.home() / 'Library/Fonts/LXGWWenKai-Regular.ttf',
        Path.home() / '.cache/inspireplanet-fonts/LXGWWenKai-Regular.ttf',
        Path.home() / '.local/share/fonts/LXGWWenKai-Regular.ttf']
    for path in choices:
        if path.is_file():
            return path
    raise ValueError('LXGWWenKai-Regular.ttf not found; pass --font')


def document(cfg, source, font, theme=None):
    name = theme or cfg.get('theme', 'collage')
    if name == 'random':
        raise ValueError('choose themes with assign_themes.py and review the saved selections before rendering')
    if not re.fullmatch(r'[a-z0-9-]+', name):
        raise ValueError('invalid theme name')
    theme_file = HERE / 'themes' / f'{name}.css'
    if not theme_file.is_file():
        raise ValueError(f'unknown theme: {name}')
    layout = cfg.get('layout', 'collage')
    if layout not in ('collage', 'editorial', 'signal'):
        raise ValueError('layout must be collage, editorial or signal; resolve random selections before review')
    layout_css = '' if layout == 'collage' else (HERE / 'layouts' / f'{layout}.css').read_text()
    form = cfg.get('format')
    if form not in ('wide', 'portrait'):
        raise ValueError('format must be wide or portrait')
    esc = html.escape
    def tile_markup(tile):
        return f'<small>{esc(tile["label"])}</small><span class="value">{esc(tile["value"])}</span><small>{esc(tile["note"])}</small>'
    tiles = [tile_markup(t) for t in cfg['tiles']]
    photo_css = ''
    if cfg.get('photo'):
        path = (config_base(source) / cfg['photo']).resolve()
        with Image.open(path) as im:
            im.verify()
        mime = mimetypes.guess_type(path.name)[0]
        if mime not in ('image/jpeg', 'image/png', 'image/webp'):
            raise ValueError('photo must be JPEG, PNG or WebP')
        pos = cfg.get('photo_position', [50, 50])
        if not isinstance(pos, list) or len(pos) != 2 or not all(isinstance(x, (int, float)) and 0 <= x <= 100 for x in pos):
            raise ValueError('photo_position must be [x, y], 0–100')
        data = base64.b64encode(path.read_bytes()).decode('ascii')
        tiles[0] = f'<img src="data:{mime};base64,{data}" alt="">'
        photo_css = f'.one{{padding:0!important}}.one img{{width:100%;height:100%;object-fit:cover;object-position:{pos[0]}% {pos[1]}%}}'
    font_data = base64.b64encode(font.read_bytes()).decode('ascii')
    return Template((HERE / 'template.html').read_text()).substitute(
        font_css=f'@font-face{{font-family:CoverChinese;src:url(data:font/ttf;base64,{font_data})}}',
        base_css=(HERE / 'base.css').read_text(), theme_css=theme_file.read_text()+layout_css+photo_css,
        form=f'{form} {layout}', speaker=esc(cfg['speaker']), episode=esc(cfg['episode']), date=esc(cfg['date']),
        headline=''.join(f'<span>{esc(s)}</span>' for s in cfg['headline']),
        subtitle=f'<p class="subtitle">{esc(cfg["subtitle"])}</p>' if cfg.get('subtitle') else '',
        tile_one=tiles[0], tile_two=tiles[1])


def jpeg_bytes(png):
    im = Image.open(io.BytesIO(png)).convert('RGB')
    for options in ({'quality': 88}, {'quality': 85}, {'quality': 85, 'subsampling': 2}):
        data = io.BytesIO()
        im.save(data, format='JPEG', optimize=True, progressive=True, **options)
        if data.tell() <= 400 * 1024:
            return data.getvalue()
    if data.tell() > 500 * 1024:
        raise ValueError('JPEG exceeds 500 KB; simplify the photograph or layout')
    return data.getvalue()


def render(sources, out_dir=None, preview_dir=None, browser_path=None, font=None, theme=None, force=False):
    jobs=[]
    for source in sources:
        source=Path(source).resolve()
        for cfg in read_configs(source):
            target=(Path(out_dir)/Path(cfg['asset']).name) if out_dir else config_base(source)/cfg['asset']
            if target.exists() and not force:
                raise ValueError(f'{target} exists; use --force to replace it')
            jobs.append((source,cfg,target))
    if len({p.resolve() for _,_,p in jobs})!=len(jobs):
        raise ValueError('duplicate output paths')
    font=font_path(font)
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(**({'executable_path': str(browser_path)} if browser_path else {}))
        try:
            for source,cfg,target in jobs:
                doc=document(cfg,source,font,theme)
                w,h=(1920,817) if cfg['format']=='wide' else (1080,1440)
                page=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
                try:
                    page.route('http://**/*',lambda route:route.abort())
                    page.route('https://**/*',lambda route:route.abort())
                    page.set_content(doc)
                    page.evaluate('document.fonts.ready')
                    page.locator('img').evaluate_all('imgs => Promise.all(imgs.map(i => i.decode()))')
                    checks=page.evaluate('''() => {
                        const content=[...document.querySelectorAll('header,footer,main,h1 span,.subtitle,.paper')];
                        const boxes=content.map(e=>{const r=e.getBoundingClientRect();return {text:e.innerText,inside:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight,overflow:e.scrollWidth>e.clientWidth+1||e.scrollHeight>e.clientHeight+1}});
                        const intersects=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
                        const main=document.querySelector('main').getBoundingClientRect();
                        const overlap=[...document.querySelectorAll('header,footer,.paper')].some(e=>intersects(main,e.getBoundingClientRect()));
                        const header=document.querySelector('header');const spans=header.querySelectorAll('span');
                        const headerOverlap=spans[0].getBoundingClientRect().right+24>spans[1].getBoundingClientRect().left;
                        return {boxes,overlap,headerOverlap};
                    }''')
                    if checks['overlap'] or checks['headerOverlap'] or any(not x['inside'] or x['overflow'] for x in checks['boxes']):
                        raise ValueError(f'{source.name}: overflow or overlap; split headline lines or shorten text. {checks}')
                    data=jpeg_bytes(page.locator('.cover').screenshot())
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(data)
                    if preview_dir:
                        preview=Path(preview_dir)/f'{target.stem}.html'
                        preview.parent.mkdir(parents=True,exist_ok=True)
                        preview.write_text(doc)
                    result={'source':source.name,'output':str(target),'theme':theme or cfg.get('theme','collage'),'layout':cfg.get('layout','collage'),'width':w,'height':h,'bytes':len(data),'checks':checks}
                    results.append(result)
                    print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False),flush=True)
                finally:
                    page.close()
        finally:
            browser.close()
    return results


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('sources',nargs='+',type=Path)
    ap.add_argument('--out-dir',type=Path,help='override output directory, retaining configured filename')
    ap.add_argument('--preview-dir',type=Path,help='save standalone HTML previews outside the repo')
    ap.add_argument('--browser',type=Path)
    ap.add_argument('--font',type=Path)
    ap.add_argument('--theme',help='override the configured theme; default collage')
    ap.add_argument('--force',action='store_true')
    args=ap.parse_args()
    try:
        render(args.sources,args.out_dir,args.preview_dir,args.browser,args.font,args.theme,args.force)
    except (ValueError,OSError,json.JSONDecodeError) as exc:
        ap.exit(1,f'{exc}\n')
