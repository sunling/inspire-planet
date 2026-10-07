"""Browser regression checks for local HTML rendering."""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image
from render import render


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', required=True, type=Path)
    parser.add_argument('--browser', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='xhs-tests-') as tmp:
        t = Path(tmp)
        source = t / 'pages.md'
        source.write_text('---\nepisode: 第 9 期\ndate: 2026-03-07\nsignature: 测试署名\n---\n\n# 测试 <script>\n\n更新前。\n\n---\n\n> 一句引用。\n\n---\n\n## 清单\n\n- 第一项\n- 第二项')
        render(source, args.font, t / 'before', args.browser, t / 'preview.html')
        document = (t / 'preview.html').read_text()
        assert '<script>' not in document
        assert '启发星球 · 第 9 期' in document and '测试署名 · 2026年3月7日' in document and document.count('class="site">inspireplanet.cc<') == 2
        assert 'card cover' in document and 'card quote' in document and 'card list' in document
        assert '<li>第一项</li>' in document and '01 / 03' not in document and '02 / 03' in document
        with Image.open(t / 'before/01.png') as im:
            assert im.size == (1080,1440)
        source.write_text(source.read_text().replace('更新前', '更新后'))
        render(source, args.font, t / 'after', args.browser)
        assert (t / 'before/01.png').read_bytes() != (t / 'after/01.png').read_bytes()
        source.write_text('---\nspeaker: 孙玲\nsite:\n---\n\n# 无站点\n\n副标题。')
        render(source, args.font, t / 'nosite', args.browser, t / 'nosite.html')
        document = (t / 'nosite.html').read_text()
        assert 'class="site">inspireplanet.cc<' not in document and '孙玲' in document
        for text, out, message in [('# 太长\n\n' + '正文溢出测试。'*800, t/'overflow', '溢出'),
                                   ('---\nseries: ' + '超长栏目'*30 + '\n---\n\n# 页眉\n\n正文。', t/'header', '页眉'),
                                   ('# 拒绝覆盖\n\n正文。', t/'before', '为空')]:
            source.write_text(text)
            try:
                render(source, args.font, out, args.browser)
            except ValueError as e:
                assert message in str(e)
            else:
                raise AssertionError(message + '未被拒绝')
        copy = t/'no-git'
        tool = Path(__file__).resolve().parent
        shutil.copytree(tool, copy, ignore=shutil.ignore_patterns('__pycache__'))
        source.write_text('# 本地副本\n\n不需要 Git 元数据。')
        command = [sys.executable, str(copy/'render.py'), str(source), str(t/'relocated'), '--font', str(args.font)]
        if args.browser:
            command += ['--browser', str(args.browser)]
        subprocess.run(command, check=True)
    print('PASS: escaping, metadata, cover, page kinds, episode/site, source update, dimensions, overflow, header overlap, output protection, no-Git build')


if __name__ == '__main__':
    main()
