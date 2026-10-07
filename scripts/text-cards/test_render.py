"""Browser regression checks for local HTML rendering."""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image
from render import render


SCRIPT = '''---
episode: 第 39 期
site:
---
# 第 39 期 · 测试

## 测试篇目

### 图集脚本

- 分享者：李影
- 日期：2026-10-03

#### 第 1 页（封面）
- 主标题：大字封面
- 副标题：副标题一行
- 左上署名：启发星球 · 第 39 期

#### 第 2 页
- 图上大字：第二页大字
- 小字：第一段小字。
  续行也算。
- 小字：第二段小字。

#### 第 3 页（原声）
- 图上大字：原声页
- 小字：这一页应是深色。
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--font', required=True, type=Path)
    parser.add_argument('--browser', type=Path)
    args = parser.parse_args()
    kw = dict(font=args.font, browser_path=args.browser)
    with tempfile.TemporaryDirectory(prefix='xhs-tests-') as tmp:
        t = Path(tmp)
        source = t / 'pages.md'
        source.write_text('---\nepisode: 第 9 期\ndate: 2026-03-07\nsignature: 测试署名\n---\n\n# 测试 <script>\n\n更新前。\n\n---\n\n> 一句引用。\n\n---\n\n## 清单\n\n- 第一项\n- 第二项')
        render(source, t / 'before', preview=t / 'preview.html', **kw)
        document = (t / 'preview.html').read_text()
        assert '<script>' not in document
        assert '--accent: #ff5a36' in document, '分页 Markdown 默认 inspire 主题'
        assert '启发星球 · 第 9 期' in document and '测试署名 · 2026年3月7日' in document and document.count('class="site">inspireplanet.cc<') == 2
        assert 'card cover' in document and 'card quote' in document and 'card list' in document
        assert '<li>第一项</li>' in document and '01 / 03' not in document and '02 / 03' in document
        with Image.open(t / 'before/01.png') as im:
            assert im.size == (1080, 1440)
        source.write_text(source.read_text().replace('更新前', '更新后'))
        render(source, t / 'after', **kw)
        assert (t / 'before/01.png').read_bytes() != (t / 'after/01.png').read_bytes()
        source.write_text('---\nspeaker: 孙玲\nsite:\ntheme: paper\n---\n\n# 无站点\n\n副标题。')
        render(source, t / 'nosite', preview=t / 'nosite.html', **kw)
        document = (t / 'nosite.html').read_text()
        assert 'class="site">inspireplanet.cc<' not in document and '孙玲' in document
        assert 'BrushChinese' in document, 'frontmatter theme: paper 生效'
        # 图集脚本输入：默认 paper，原声页深色，署名覆盖页眉
        source.write_text(SCRIPT)
        results = render(source, t / 'script', preview=t / 'script.html', **kw)
        document = (t / 'script.html').read_text()
        assert results[0]['theme'] == 'paper' and len(results[0]['cards']) == 3
        assert 'card text dark' in document and '启发星球 · 第 39 期' in document
        assert '李影 · 2026年10月3日' in document and 'class="site">inspireplanet.cc<' not in document, '图集脚本 frontmatter / 篇目级设置'
        assert '第一段小字。续行也算。' in document and '第二段小字。' in document
        results = render(source, t / 'script-inspire', theme='inspire', **kw)
        assert results[0]['theme'] == 'inspire'
        for text, out, message, extra in [('# 太长\n\n' + '正文溢出测试。'*800, t/'overflow', '溢出', {}),
                                          ('---\nseries: ' + '超长栏目'*30 + '\n---\n\n# 页眉\n\n正文。', t/'header', '页眉', {}),
                                          ('# 拒绝覆盖\n\n正文。', t/'before', '为空', {}),
                                          ('# 没有主题\n\n正文。', t/'notheme', '可用', {'theme': 'nope'})]:
            source.write_text(text)
            try:
                render(source, out, **kw, **extra)
            except ValueError as e:
                assert message in str(e), (message, str(e))
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
    print('PASS: escaping, themes, metadata, script settings, cover, page kinds, episode/site, script input, dark page, source update, dimensions, overflow, header overlap, output protection, unknown theme, no-Git build')


if __name__ == '__main__':
    main()
