#!/usr/bin/env python3
"""Render reviewed episode scripts into one stable external publishing folder."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[1]
CHANNELS = ('gzh', 'xhs', 'sph')


def external_root(path):
    root = Path(path).expanduser().resolve()
    if root == REPO or REPO in root.parents:
        raise ValueError('Publishing folder must be outside the repository')
    return root


@contextmanager
def locked(root):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.render.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        lock.unlink()


def validate(ready):
    from PIL import Image
    count = 0
    for channel in CHANNELS:
        folder = ready / channel
        if not folder.exists():
            continue
        files = sorted(folder.rglob('*.jpg'))
        if not files:
            raise ValueError(f'No JPEGs in {channel}')
        if any(p.is_file() and p.suffix.lower() != '.jpg' for p in folder.rglob('*')):
            raise ValueError(f'Only JPEGs belong in ready/{channel}')
        for f in files:
            if f.is_symlink():
                raise ValueError(f'Symlink is not a publishing image: {f}')
            with Image.open(f) as im:
                if im.format != 'JPEG':
                    raise ValueError(f'Expected JPEG: {f}')
                im.verify()
            with Image.open(f) as im:
                expected = (1920, 817) if channel == 'gzh' else (1080, 1440)
                if im.size != expected:
                    raise ValueError(f'Unexpected image dimensions: {f}: {im.size}')
            count += 1
        if channel != 'gzh':
            for post in folder.iterdir():
                if not post.is_dir():
                    raise ValueError(f'Unexpected file: {post}')
                names = sorted(p.name for p in post.iterdir())
                if names != [f'{n:02}.jpg' for n in range(1, len(names) + 1)] or not names:
                    raise ValueError(f'Non-contiguous image set: {post}')
    if not count:
        raise ValueError('No publishing images')
    return count


def package(stage, episode):
    ready = stage / 'ready'
    validate(ready)
    sections = []
    labels = {'gzh': '公众号', 'xhs': '小红书', 'sph': '视频号'}
    all_files = []
    for channel in CHANNELS:
        folder = ready / channel
        if not folder.exists():
            continue
        files = sorted(folder.rglob('*.jpg'))
        all_files.extend(files)
        with zipfile.ZipFile(stage / f'{channel}.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.relative_to(ready))
        sections.append(f'<h2>{labels[channel]}</h2><a href="{channel}.zip">下载本平台图片</a>')
        for f in files:
            relative = f.relative_to(stage).as_posix()
            label = html.escape(f.relative_to(ready).as_posix())
            sections.append(f'<figure><a href="{relative}"><img loading="lazy" src="{relative}"></a><figcaption>{label}</figcaption></figure>')
    with zipfile.ZipFile(stage / 'all.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for f in all_files:
            z.write(f, f.relative_to(ready))
    (stage / 'preview.html').write_text('<!doctype html><meta charset="utf-8">'
        f'<title>{html.escape(episode)} 发布图片</title><style>body{{font-family:system-ui;background:#faf7f0;margin:32px}}'
        'h2{clear:both;padding-top:24px}figure{display:inline-block;vertical-align:top;margin:12px;width:240px}'
        'img{width:100%}figcaption{font-size:14px}</style>'
        f'<h1>{html.escape(episode)} 发布图片</h1><p>发布时只使用 ready/ 中的图片。</p>'
        '<a href="all.zip">下载全部图片</a><br>'+''.join(sections), encoding='utf-8')


def promote(root, stage):
    """Archive the previous bundle; restore it if promotion fails."""
    names = ('ready', 'preview.html', 'all.zip', 'gzh.zip', 'xhs.zip', 'sph.zip')
    old = [name for name in names if (root / name).exists()]
    history = root / 'history' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    moved_old, moved_new = [], []
    if old:
        history.mkdir(parents=True)
    try:
        for name in old:
            (root / name).rename(history / name)
            moved_old.append(name)
        for name in names:
            if (stage / name).exists():
                (stage / name).rename(root / name)
                moved_new.append(name)
    except BaseException:
        for name in reversed(moved_new):
            (root / name).rename(stage / name)
        for name in reversed(moved_old):
            (history / name).rename(root / name)
        raise


def run(event, root, channels, slug=None, imported=None, browser=None, font=None):
    event = Path(event).resolve()
    if not event.is_dir() or not re.fullmatch(r'\d{8}-ep\d+', event.name):
        raise ValueError('Expected an existing YYYYMMDD-epNN event directory')
    if slug and ('gzh' in channels or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug)):
        raise ValueError('--slug supports xhs/sph only and requires an ASCII slug')
    root = external_root(root) / event.name
    with locked(root), tempfile.TemporaryDirectory(prefix='.render-', dir=root) as temp:
        stage = Path(temp)
        ready = stage / 'ready'
        if (root / 'ready').exists():
            shutil.copytree(root / 'ready', ready)
        else:
            ready.mkdir()
        shared = []
        if browser:
            shared += ['--browser', str(browser)]
        if font:
            shared += ['--font', str(font)]
        for channel in channels:
            target = ready / channel
            if imported:
                source = Path(imported).resolve() / channel
                if slug:
                    source, target = source / slug, target / slug
                if not source.is_dir():
                    raise ValueError(f'Missing import directory: {source}')
                if any(p.is_symlink() for p in source.rglob('*')):
                    raise ValueError('Import images must not be symlinks')
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(source, target)
                continue
            if channel == 'gzh':
                if target.exists():
                    shutil.rmtree(target)
                command = [sys.executable, str(REPO / 'scripts/covers/render.py'),
                    str(event / 'assets/cover-configs.md'), '--out-dir', str(target), *shared]
                commands = [command]
            else:
                scripts = [event / f'{channel}-{slug}.md'] if slug else sorted(event.glob(f'{channel}-*.md'))
                if not scripts or any(not p.is_file() for p in scripts):
                    raise ValueError(f'Missing {channel} scripts')
                if not slug and target.exists():
                    shutil.rmtree(target)
                commands = []
                for script in scripts:
                    post = target / script.stem[len(channel) + 1:]
                    if post.exists():
                        shutil.rmtree(post)
                    commands.append([sys.executable, str(REPO / 'scripts/text-cards/render.py'),
                        str(script), str(post), '--jpeg', *shared])
            for n, command in enumerate(commands):
                with (stage / f'{channel}-{n}.log').open('w') as log:
                    result = subprocess.run(command, stdout=log, stderr=log)
                if result.returncode:
                    raise ValueError((stage / f'{channel}-{n}.log').read_text())
        package(stage, event.name)
        count = validate(ready)
        promote(root, stage)
    print(f'{count} images: {root / "ready"}')
    print(f'Preview: {root / "preview.html"}')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event', type=Path)
    parser.add_argument('--root', type=Path, default=REPO.parent / 'inspire-planet-publish',
        help='External publishing root; default: inspire-planet-publish beside the repository')
    parser.add_argument('--channel', action='append', choices=CHANNELS, required=True)
    parser.add_argument('--slug', help='Update only this xhs/sph post; preserve other posts')
    parser.add_argument('--import-dir', type=Path, help='Import already checked JPEGs from channel directories')
    parser.add_argument('--browser', type=Path)
    parser.add_argument('--font', type=Path)
    args = parser.parse_args()
    try:
        run(args.event, args.root, list(dict.fromkeys(args.channel)), args.slug,
            args.import_dir, args.browser, args.font)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
