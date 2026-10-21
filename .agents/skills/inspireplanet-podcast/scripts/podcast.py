#!/usr/bin/env python3
"""Inspect, find silence candidates, or render a local podcast edit plan."""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile


def repository():
    return Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()


def private_directory(path, source):
    path = Path(path).resolve()
    root = repository()
    if not path.is_relative_to(root / 'replays'):
        raise ValueError('输出必须位于本仓库 replays/ 内')
    if source.resolve().is_relative_to(path):
        raise ValueError('输出目录不能包含源文件')
    if subprocess.run(['git', 'check-ignore', '-q', str(path)]).returncode:
        raise ValueError('输出目录未被 Git 忽略')
    if subprocess.check_output(['git', 'ls-files', '--', str(path)], text=True).strip():
        raise ValueError('输出目录含已跟踪文件')
    return path


def ffmpeg(args):
    import imageio_ffmpeg
    p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-nostdin'] + args,
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-4000:])
    return p.stderr


def probe(source):
    import av
    with av.open(str(source)) as c:
        if not c.streams.audio:
            raise ValueError('源文件没有音轨')
        a = c.streams.audio[0]
        seconds = c.duration / av.time_base if c.duration is not None else float(a.duration * a.time_base)
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('无法读取有效时长')
        return {'seconds': seconds, 'channels': a.codec_context.channels,
                'sample_rate': a.codec_context.sample_rate, 'codec': a.codec_context.name}


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('时间必须是有限数字')
    return value


def load_plan(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    source = (path.parent / data['source']).resolve()
    metadata = probe(source)
    cursor = 0
    spans = []
    cuts = data.get('cuts', [])
    for cut in cuts:
        a, b = seconds(cut['start']), seconds(cut['end'])
        if not 0 <= cursor <= a < b <= metadata['seconds']:
            raise ValueError('删减范围须按时间递增、不重叠且不超出源媒体')
        if not all(isinstance(cut.get(k), str) and cut[k].strip() for k in ('reason', 'evidence')):
            raise ValueError('每处删减须记录 reason 和 evidence')
        if a > cursor:
            spans.append([cursor, a])
        cursor = b
    if cursor < metadata['seconds']:
        spans.append([cursor, metadata['seconds']])
    if not spans:
        raise ValueError('不能删除整段音频')
    chapters = data.get('chapters', [])
    previous = -1
    for chapter in chapters:
        t = seconds(chapter['source_seconds'])
        if t <= previous or not any(a <= t < b for a, b in spans):
            raise ValueError('章节须递增且位于保留区间；不得将已删内容映射到邻近章节')
        if not isinstance(chapter.get('title'), str) or not chapter['title'].strip():
            raise ValueError('章节缺少标题')
        previous = t
    return source, metadata, spans, chapters


def map_time(t, spans):
    elapsed = 0
    for a, b in spans:
        if a <= t < b:
            return elapsed + t - a
        elapsed += b - a
    raise ValueError('章节落在删减区间或源媒体之外')


def timestamp(t):
    t = math.floor(t)
    return f'{t // 3600:02}:{t // 60 % 60:02}:{t % 60:02}'


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def analyze(source, output):
    source = source.resolve()
    metadata = probe(source)
    output = private_directory(output, source)
    output.mkdir(parents=True, exist_ok=True)
    for name in ('analysis.json', 'analysis.log'):
        if (output / name).is_symlink():
            raise ValueError('分析目标不能是符号链接')
    log = ffmpeg(['-i', str(source), '-vn', '-af', 'silencedetect=noise=-48dB:d=4', '-f', 'null', '-'])
    # Match each start with its following end, including a possible trailing silence.
    candidates = []
    start = None
    for line in log.splitlines():
        m = re.search(r'silence_start: ([\d.]+)', line)
        if m:
            start = float(m[1])
        m = re.search(r'silence_end: ([\d.]+)', line)
        if m and start is not None:
            candidates.append({'start': start, 'end': min(float(m[1]), metadata['seconds']),
                               'status': 'candidate', 'evidence': 'silencedetect -48 dB / 4 s'})
            start = None
    if start is not None:
        candidates.append({'start': start, 'end': metadata['seconds'], 'status': 'candidate',
                           'evidence': 'silencedetect -48 dB / 4 s; trailing silence'})
    write_json(output / 'analysis.json', {'source': str(source), 'metadata': metadata,
                                         'silence_candidates': candidates, 'human_listening_reviewed': False})
    (output / 'analysis.log').write_text(log)
    return {'metadata': metadata, 'candidates': len(candidates)}


def render(plan, output, check=False):
    plan = plan.resolve()
    source, metadata, spans, chapters = load_plan(plan)
    output = private_directory(output, source)
    if plan.is_relative_to(output):
        raise ValueError('剪辑单须放在导出目录之外')
    if check:
        return {'valid': True, 'metadata': metadata, 'keep_spans': spans,
                'output_seconds': sum(b-a for a, b in spans)}
    output.mkdir(parents=True, exist_ok=True)
    # Stage all generated files before replacing prior exports; never overwrite source or plan.
    with tempfile.TemporaryDirectory(prefix='.podcast-', dir=output) as tmp:
        work = Path(tmp)
        sample_rate = 48000 if metadata['sample_rate'] >= 44100 else 32000
        for i, (a, b) in enumerate(spans):
            duration = b-a
            fade = min(0.008, duration / 4)
            ffmpeg(['-v', 'error', '-y', '-ss', str(a), '-i', str(source), '-t', str(duration),
                    '-vn', '-af', f'afade=t=in:d={fade},afade=t=out:st={duration-fade}:d={fade}',
                    '-ar', str(sample_rate), '-ac', str(min(metadata['channels'], 2)),
                    '-c:a', 'pcm_s16le', str(work / f'part-{i:04}.wav')])
        concat = work / 'parts.ffconcat'
        concat.write_text('ffconcat version 1.0\n' + ''.join(
            f"file 'part-{i:04}.wav'\n" for i in range(len(spans))))
        target = -19 if metadata['channels'] == 1 else -16
        audio = work / 'podcast.m4a'
        log = ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', str(concat),
                      '-af', f'loudnorm=I={target}:TP=-2:LRA=11:print_format=json',
                      '-ar', str(sample_rate), '-c:a', 'aac', '-b:a', '128k',
                      '-movflags', '+faststart', str(audio)])
        (work / 'render.log').write_text(log)
        qa = ffmpeg(['-nostats', '-i', str(audio), '-af', 'ebur128=peak=true', '-f', 'null', '-'])
        (work / 'qa.log').write_text(qa)
        summary = qa.rsplit('Summary:', 1)[-1]
        measured_i = re.search(r'I:\s*([-\d.]+) LUFS', summary)
        measured_peak = re.search(r'Peak:\s*([-\d.]+) dBFS', summary)
        actual = probe(audio)
        expected = sum(b-a for a, b in spans)
        if abs(actual['seconds']-expected) > max(0.2, len(spans)/sample_rate + 0.1):
            raise ValueError('导出时长与剪辑单不符')
        if not measured_i or not measured_peak:
            raise ValueError('响度检查缺少有效测量，详查输入是否为静音')
        loudness, peak = float(measured_i[1]), float(measured_peak[1])
        if abs(loudness-target) > 1 or peak > -1:
            raise ValueError(f'响度或峰值需调整：{loudness} LUFS / {peak} dBTP')
        mapped = [{'seconds': round(map_time(c['source_seconds'], spans), 3),
                   'source_seconds': c['source_seconds'], 'title': c['title']} for c in chapters]
        write_json(work / 'chapters.json', mapped)
        (work / 'chapters.txt').write_text('\n'.join(f'{timestamp(c["seconds"])} {c["title"]}' for c in mapped)+'\n')
        report = {'source_seconds': metadata['seconds'], 'output_seconds': actual['seconds'],
                  'removed_seconds': metadata['seconds']-expected, 'cuts': len(spans)-1 +
                  int(spans[0][0]>0) + int(spans[-1][1]<metadata['seconds']),
                  'integrated_lufs': loudness, 'true_peak_dbtp': peak,
                  'full_decode_passed': True, 'human_listening_reviewed': False,
                  'release_approved': False, 'plan': str(plan), 'bytes': audio.stat().st_size}
        write_json(work / 'report.json', report)
        for name in ('podcast.m4a', 'render.log', 'qa.log', 'chapters.json', 'chapters.txt', 'report.json'):
            target_path = output / name
            if target_path.is_symlink() or target_path.resolve() in (source, plan):
                raise ValueError('导出目标与源文件或符号链接冲突')
        for name in ('podcast.m4a', 'render.log', 'qa.log', 'chapters.json', 'chapters.txt', 'report.json'):
            (work / name).replace(output / name)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('inspect'); p.add_argument('source', type=Path)
    p = sub.add_parser('analyze'); p.add_argument('source', type=Path); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('render'); p.add_argument('plan', type=Path); p.add_argument('--output', type=Path, required=True); p.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.command == 'inspect':
        result = probe(args.source)
    elif args.command == 'analyze':
        result = analyze(args.source, args.output)
    else:
        result = render(args.plan, args.output, args.check)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
        raise SystemExit(str(exc))
