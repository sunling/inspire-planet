"""Local-only paths and media metadata shared by the clips tools."""
import json
import math
import subprocess
from pathlib import Path


def repository():
    for parent in Path(__file__).resolve().parents:
        if (parent / '.git').exists():
            return parent
    return Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())


def private_path(path):
    path = Path(path).resolve()
    root = repository()
    try:
        path.relative_to(root / 'replays')
    except ValueError:
        raise ValueError('制作资料必须保存在仓库的 replays/ 内')
    result = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', str(path)])
    if result.returncode != 0:
        raise ValueError('replays/ 忽略规则未生效；先修复 .gitignore，再写制作资料')
    tracked = subprocess.check_output(
        ['git', '-C', str(root), 'ls-files', '--', str(path)], text=True).strip()
    if tracked:
        raise ValueError('目标包含已被 Git 跟踪的文件，不能写入私人制作资料')
    return path


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def probe(source):
    import av
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError('未找到本地源文件')
    with av.open(str(source)) as container:
        video = container.streams.video[0] if container.streams.video else None
        audio = container.streams.audio[0] if container.streams.audio else None
        duration = container.duration / av.time_base if container.duration is not None else None
        if not duration:
            durations = [float(s.duration * s.time_base) for s in container.streams
                         if s.duration is not None and s.time_base]
            duration = max(durations) if durations else None
        if not duration or not audio:
            raise ValueError('源文件缺少可读取时长或音轨')
        return {'seconds': duration, 'width': video.width if video else None,
                'height': video.height if video else None,
                'video_codec': video.codec_context.name if video else None,
                'audio_codec': audio.codec_context.name}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run_ffmpeg(args, log):
    import imageio_ffmpeg
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-y'] + args,
                            capture_output=True, text=True)
    Path(log).write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'FFmpeg 失败，详情见 {log}')
    return result
