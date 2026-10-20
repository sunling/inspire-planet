#!/usr/bin/env python3
"""Render confirmed local replay clips from an editable JSON plan."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont
from common import number, private_path, probe, run_ffmpeg, write_json

INK = '#F6F2E9'
ACCENT = '#D1AA7E'
BG = '#25382F'
MUTED = '#BDCAC0'
RULE = '#526359'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local(base, value):
    return (base / value).resolve()


def choose_font(base, value=None):
    if value:
        candidate = local(base, value)
        require(candidate.is_file(), '指定字体不存在')
        return candidate
    for value in ['/System/Library/Fonts/STHeiti Medium.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                  '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']:
        if Path(value).is_file():
            return Path(value)
    raise ValueError('没有可用中文字体；在 style.font 中指定实际字体路径')


def mapped_captions(clip):
    rows = []
    offset = 0.0
    for a, b in clip['spans']:
        for start, end, text in clip['captions']:
            if a <= start < end <= b:
                rows.append((offset + start - a, offset + end - a, text))
        offset += b - a
    return rows


def timecode(seconds, ass=False):
    base = 100 if ass else 1000
    whole, fraction = divmod(round(seconds * base), base)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    return (f'{hours}:{minutes:02}:{secs:02}.{fraction:02}' if ass else
            f'{hours:02}:{minutes:02}:{secs:02},{fraction:03}')


def validate(path, slug=None):
    path = private_path(path)
    plan = json.loads(path.read_text(encoding='utf-8'))
    base = path.parent
    require(plan.get('version') == 1, '剪辑单 version 必须为 1')
    source = local(base, plan['source'])
    media = probe(source)
    event = plan['event']
    require(date.fromisoformat(event['date']).year == int(event['year']), '日期与年份不符')
    require(int(event['episode']) > 0, '期数必须为正数')
    website = plan['brand']['website']
    require(isinstance(website, str) and re.fullmatch(r'[a-z0-9.-]+\.[a-z]{2,}', website),
            'brand.website 只填写已确认的简短域名')
    style = plan.get('style', {})
    title_font = choose_font(base, style.get('font'))
    light = Path('/System/Library/Fonts/STHeiti Light.ttc')
    regular_font = choose_font(base, style.get('regular_font') or
                               str(light if light.is_file() else title_font))
    fonts = (title_font, regular_font)
    draw = ImageDraw.Draw(Image.new('RGB', (1080, 1920)))
    def fits(text, size, width=960):
        box = draw.textbbox((0, 0), text, font=ImageFont.truetype(str(title_font), size))
        return box[2] - box[0] <= width
    require(fits(website, 34, 650), '官网域名过长，不能放入页脚')
    clips = plan['clips']
    require(isinstance(clips, list) and clips, '没有剪辑条目')
    slugs = [clip['slug'] for clip in clips]
    require(len(set(slugs)) == len(slugs) and all(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', s)
                                               for s in slugs), 'slug 必须唯一且仅用英文小写、数字和连字符')
    if slug:
        clips = [c for c in clips if c['slug'] == slug]
        require(bool(clips), '未找到所选 slug')
    protected = {source, path, *fonts}
    for clip in clips:
        title = clip['title']
        require(isinstance(title, list) and 1 <= len(title) <= 2 and
                all(isinstance(t, str) and t.strip() and '\n' not in t and fits(t, 76) for t in title),
                '标题须为 1–2 行，且每行适合画面宽度')
        require(isinstance(clip['speaker'], str) and clip['speaker'].strip() and
                fits(clip['speaker'], 38, 750), '署名缺失或过长')
        require(fits(clip.get('label', ''), 30, 850) and '\n' not in clip.get('label', ''), '提示语过长')
        require(fits(clip.get('cover_text', ''), 47) and '\n' not in clip.get('cover_text', ''), '封面收尾文字过长')
        previous_end = -1.0
        require(isinstance(clip['spans'], list) and clip['spans'], '保留区间不能为空')
        for span in clip['spans']:
            require(len(span) == 2 and all(number(t) for t in span), '区间必须使用实际媒体秒数')
            a, b = span
            require(0 <= a < b <= media['seconds'] + 0.05 and a >= previous_end,
                    '区间倒序、重叠或超出媒体时长')
            previous_end = b
        cover = clip.get('cover_time', clip['spans'][0][0])
        require(number(cover) and any(a <= cover < b for a, b in clip['spans']),
                '封面时间必须在保留区间内')
        clip['cover_time'] = cover
        box = clip.get('video_box', [60, 610, 960, 540])
        require(isinstance(box, list) and len(box) == 4 and all(type(v) is int for v in box), 'video_box 无效')
        x, y, w, h = box
        require(x >= 60 and y >= 560 and w > 0 and h > 0 and x + w <= 1020 and
                y + h <= 1160 and w % 2 == 0 and h % 2 == 0, '画面区域越界或侵占文字区域')
        clip['video_box'] = box
        crop = clip.get('crop')
        if crop:
            require(media['width'] and len(crop) == 4 and all(type(v) is int for v in crop), '裁切需要视频轨与整数坐标')
            cx, cy, cw, ch = crop
            require(cx >= 0 and cy >= 0 and cw > 0 and ch > 0 and cx + cw <= media['width'] and
                    cy + ch <= media['height'], '裁切区域超出源视频')
        if clip.get('still'):
            still = local(base, clip['still'])
            require(still.is_file(), '授权静态图片不存在')
            protected.add(still)
            with Image.open(still) as im:
                im.verify()
        cues = clip['captions']
        require(isinstance(cues, list) and cues, '字幕不能为空；先对齐实际原声')
        previous_end = -1.0
        for start, end, text in cues:
            require(number(start) and number(end) and 0 <= start < end and start >= previous_end,
                    '字幕时间无效或相互重叠')
            require(any(a <= start < end <= b for a, b in clip['spans']), '字幕跨越删减点或位于保留范围之外；先拆分')
            require(isinstance(text, str) and text.strip() and len(text.splitlines()) <= 2 and
                    all(fits(line, 52, 940) for line in text.splitlines()), '字幕过长，先断句或拆分时间段')
            require(not any(char in text for char in '{}\\'), '字幕不能含 ASS 控制字符')
            previous_end = end
    require(all(not p.is_relative_to(base / 'work') for p in protected),
            '原始资料不能放在渲染器的 work/ 临时目录内')
    for clip in clips:
        destinations = [base / f'{clip["slug"]}{suffix}' for suffix in
                        ['-draft.mp4', '.srt', '.ass', '-cover.jpg', '-preview.jpg']]
        require(all(p.resolve() not in protected for p in destinations), '生成文件会覆盖原始资料')
    return plan, clips, source, media, fonts


def make_template(plan, clip, fonts, work):
    title_font, regular_font = fonts
    def font(size, bold=False):
        return ImageFont.truetype(str(title_font if bold else regular_font), size)
    im = Image.new('RGB', (1080, 1920), BG)
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((60, 108, 248, 156), radius=24, outline=MUTED, width=1)
    draw.text((154, 132), '启发星球', font=font(26, True), fill=INK, anchor='mm')
    event = plan['event']
    draw.text((1018, 132), f'{event["year"]} / EP{event["episode"]}', font=font(26), fill=MUTED, anchor='rm')
    for index, line in enumerate(clip['title']):
        draw.text((60, 246 + index * 112), line, font=font(76, True), fill=INK)
    draw.rectangle((60, 492, 136, 499), fill=ACCENT)
    draw.text((162, 483), clip.get('label', ''), font=font(30), fill=ACCENT)
    x, y, w, h = clip['video_box']
    draw.rectangle((x-2, y-2, x+w+2, y+h+2), fill=RULE)
    draw.rectangle((x, y, x+w, y+h), fill=BG)
    for index, line in enumerate(clip['title']):
        draw.text((x+w/2, y+h/2-50+index*64), line, font=font(44, True), fill=INK, anchor='mm')
    draw.text((x+w/2, y+h-40), '原声分享', font=font(25), fill=MUTED, anchor='mm')
    draw.text((60, 1198), clip['speaker'], font=font(38, True), fill=INK)
    draw.text((1018, 1221), '会议原声', font=font(25), fill=MUTED, anchor='rs')
    draw.line((60, 1270, 1020, 1270), fill=RULE, width=2)
    # Preserve the original footer arrangement above the platform description.
    draw.line((60, 1478, 1020, 1478), fill=RULE, width=2)
    draw.text((60, 1500), '真实的生活 · 具体的分享', font=font(27), fill=MUTED)
    draw.text((60, 1550), plan['brand']['website'], font=font(34, True), fill=INK)
    draw.text((1018, 1587), event['date'].replace('-', '.'), font=font(23), fill=MUTED, anchor='rs')
    path = work / f'{clip["slug"]}-template.png'
    im.save(path)
    return path


def write_captions(clip, base, font_path):
    rows = mapped_captions(clip)
    slug = clip['slug']
    srt = '\n\n'.join(f'{index}\n{timecode(start)} --> {timecode(end)}\n{text}'
                       for index, (start, end, text) in enumerate(rows, 1)) + '\n'
    (base / f'{slug}.srt').write_text(srt, encoding='utf-8')
    family = ImageFont.truetype(str(font_path), 50).getname()[0].replace(',', '')
    ass = f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{family},52,&H00E9F2F6,&H00E9F2F6,&H002F3825,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,65,65,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    for start, end, text in rows:
        text = text.replace('\n', r'\N')
        ass += f'Dialogue: 0,{timecode(start, True)},{timecode(end, True)},Default,,0,0,0,,{{\\pos(540,1395)}}{text}\n'
    path = base / f'{slug}.ass'
    path.write_text(ass, encoding='utf-8')
    return path


def filter_path(path):
    # FFmpeg filter arguments have two escaping layers, unlike subprocess argv.
    return str(path).replace('\\', '\\\\').replace(':', '\\:').replace("'", "'\\''")


def render(plan, clip, source, media, fonts, base, export_cover=False):
    work = private_path(base / 'work')
    work.mkdir(exist_ok=True)
    slug = clip['slug']
    template = make_template(plan, clip, fonts, work)
    ass = write_captions(clip, base, fonts[0])
    args = []
    spans = clip['spans']
    for a, b in spans:
        args += ['-ss', str(a), '-t', str(b-a), '-i', str(source)]
    n = len(spans)
    args += ['-loop', '1', '-framerate', '25', '-i', str(template)]
    x, y, w, h = clip['video_box']
    visual = bool(media['width']) and not clip.get('still')
    filters = []
    if visual:
        crop = clip.get('crop')
        transform = f'crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},' if crop else ''
        for index in range(n):
            filters.append(f'[{index}:v]{transform}scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x25382F,fps=25,setsar=1,setpts=PTS-STARTPTS[v{index}]')
    for index in range(n):
        filters.append(f'[{index}:a]aresample=48000,asetpts=PTS-STARTPTS[a{index}]')
    if visual:
        streams = ''.join(f'[v{i}][a{i}]' for i in range(n))
        filters.append(f'{streams}concat=n={n}:v=1:a=1[footage][voice]')
        filters.append(f'[{n}:v][footage]overlay={x}:{y}:shortest=1[layout]')
    else:
        filters.append(''.join(f'[a{i}]' for i in range(n)) + f'concat=n={n}:v=0:a=1[voice]')
        if clip.get('still'):
            args += ['-loop', '1', '-framerate', '25', '-i', str(local(base, clip['still']))]
            filters.append(f'[{n+1}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x25382F[still]')
            filters.append(f'[{n}:v][still]overlay={x}:{y}[layout]')
        else:
            filters.append(f'[{n}:v]null[layout]')
    filters.append(f"[layout]ass=filename='{filter_path(ass)}':fontsdir='{filter_path(fonts[0].parent)}'[outv]")
    filters.append('[voice]loudnorm=I=-16:TP=-1.5:LRA=11[outa]')
    duration = sum(b-a for a, b in spans)
    target = base / f'{slug}-draft.mp4'
    run_ffmpeg(args + ['-filter_complex', ';'.join(filters), '-map', '[outv]', '-map', '[outa]',
                       '-t', str(duration), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
                       '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                       '-movflags', '+faststart', str(target)], work / f'{slug}-render.log')
    if export_cover:
        # Export a cover from the rendered layout at a kept source moment, with captions removed.
        cover_offset = 0.0
        for a, b in spans:
            if a <= clip['cover_time'] < b:
                cover_offset += clip['cover_time'] - a
                break
            cover_offset += b-a
        cover_frame = work / f'{slug}-cover-frame.png'
        run_ffmpeg(['-ss', str(cover_offset), '-i', str(target), '-frames:v', '1', str(cover_frame)],
                   work / f'{slug}-cover.log')
        cover = Image.open(cover_frame).convert('RGB')
        draw = ImageDraw.Draw(cover)
        draw.rectangle((50, 1290, 1030, 1462), fill=BG)
        draw.text((540, 1395), clip.get('cover_text', ''), fill=INK,
                  font=ImageFont.truetype(str(fonts[0]), 47), anchor='mm')
        cover.save(base / f'{slug}-cover.jpg', quality=95)
    run_ffmpeg(['-ss', str(min(12, duration/2)), '-i', str(target), '-frames:v', '1',
                str(base / f'{slug}-preview.jpg')], work / f'{slug}-preview.log')
    run_ffmpeg(['-v', 'error', '-i', str(target), '-f', 'null', '-'], work / f'{slug}-decode.log')
    result = probe(target)
    require((result['width'], result['height']) == (1080, 1920), '导出尺寸不正确')
    require(abs(result['seconds'] - duration) < 0.15, '导出时长与剪辑单不符')
    write_json(work / f'{slug}-qa.json', {**result, 'decode_passed': True, 'human_reviewed': False})
    print(f'{slug}: {result["seconds"]:.2f}s, 1080×1920, decode passed', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--slug')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--cover', action='store_true', help='按需额外导出独立封面，默认不生成')
    args = parser.parse_args()
    plan, clips, source, media, fonts = validate(args.plan, args.slug)
    if args.check:
        print(json.dumps({'media': media, 'clips': [c['slug'] for c in clips]}, ensure_ascii=False, indent=2))
        return
    require(all(c.get('confirmed') is True for c in clips), '先取得用户的选段确认，再将对应条目 confirmed 设为 true')
    for clip in clips:
        render(plan, clip, source, media, fonts, args.plan.resolve().parent, export_cover=args.cover)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, RuntimeError, ImportError) as exc:
        raise SystemExit(str(exc))
