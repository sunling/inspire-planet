#!/usr/bin/env python3
"""Inspect local replay media or transcribe a bounded local audio window."""
import argparse
from pathlib import Path
from common import private_path, probe, run_ffmpeg, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('source', type=Path)
    inspect.add_argument('--frame', type=float, action='append', default=[])
    inspect.add_argument('--output', type=Path)
    transcribe = sub.add_parser('transcribe')
    transcribe.add_argument('source', type=Path)
    transcribe.add_argument('--start', type=float, required=True)
    transcribe.add_argument('--duration', type=float, required=True)
    transcribe.add_argument('--output', type=Path, required=True)
    transcribe.add_argument('--model', default='small')
    transcribe.add_argument('--model-dir', type=Path)
    transcribe.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    metadata = probe(args.source)
    print(__import__('json').dumps(metadata, ensure_ascii=False, indent=2))
    if args.command == 'inspect':
        if not args.frame:
            return
        if not args.output or not metadata['width']:
            raise ValueError('提取画面需要 --output 和含视频轨的源文件')
        if any(not 0 <= t < metadata['seconds'] for t in args.frame):
            raise ValueError('预览时间超出视频范围')
        output = private_path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / 'metadata.json', metadata)
        for index, t in enumerate(args.frame):
            run_ffmpeg(['-ss', str(t), '-i', str(args.source.resolve()), '-frames:v', '1',
                        '-vf', 'scale=1080:-2', str(output / f'frame-{index:02}.jpg')],
                       output / f'frame-{index:02}.log')
        return
    if not 0 <= args.start < metadata['seconds'] or args.duration <= 0:
        raise ValueError('识别窗口需要有效的开始时间和正时长')
    if args.start + args.duration > metadata['seconds'] + 0.05:
        raise ValueError('识别窗口超出媒体范围')
    output = private_path(args.output)
    source = args.source.resolve()
    if source.is_relative_to(output):
        raise ValueError('识别输出目录不能包含原回放，以免覆盖源文件')
    # Optional dependency; inspection and rendering do not need an ASR model.
    from faster_whisper import WhisperModel
    models = private_path(args.model_dir or private_path('replays/.models'))
    output.mkdir(parents=True, exist_ok=True)
    wav = output / 'window.wav'
    run_ffmpeg(['-ss', str(args.start), '-i', str(source), '-t', str(args.duration),
                '-vn', '-ac', '1', '-ar', '16000', str(wav)], output / 'extract.log')
    model = WhisperModel(args.model, device='cpu', compute_type='int8', cpu_threads=4,
                         download_root=str(models), local_files_only=args.offline)
    segments, _ = model.transcribe(str(wav), language='zh', beam_size=5,
                                   word_timestamps=True, vad_filter=False,
                                   condition_on_previous_text=False)
    rows = []
    for segment in segments:
        row = {'start': round(args.start + segment.start, 3),
               'end': round(args.start + segment.end, 3), 'text': segment.text,
               'words': [{'start': round(args.start + w.start, 3),
                          'end': round(args.start + w.end, 3), 'text': w.word,
                          'probability': w.probability} for w in segment.words or []]}
        rows.append(row)
        print(row['start'], row['end'], row['text'], flush=True)
    write_json(output / 'words.json', {'source_window': [args.start, args.start + args.duration],
                                     'human_reviewed': False, 'segments': rows})


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, ImportError) as exc:
        raise SystemExit(str(exc))
