#!/usr/bin/env python3
"""Integration checks: dimensions, local photos, overflow refusal, alternate themes."""
import argparse
import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path
from PIL import Image
import render


def run(font, browser):
    with tempfile.TemporaryDirectory(prefix='inspire-cover-test-') as tmp:
        root=Path(tmp)
        cfg={'speaker':'分享者','episode':'EP38','date':'2026-09-26','theme':'collage','format':'portrait','asset':'cover.jpg','headline':['一个具体场景','一个真实问题'],'subtitle':'保留一点好奇','tiles':[{'label':'起点','value':'片段','note':'具体经历'},{'label':'变化','value':'行动','note':'仍在尝试'}]}
        source=root/'sample.md'
        def write():
            source.write_text('<!-- cover-config -->\n```json\n'+json.dumps(cfg,ensure_ascii=False)+'\n```')
        write()
        with contextlib.redirect_stdout(io.StringIO()):
            result=render.render([source],root/'portrait',font=font,browser_path=browser)
        with Image.open(root/'portrait/cover.jpg') as im:
            assert im.size==(1080,1440) and im.mode=='RGB' and im.info['progressive']==1
        assert result[0]['bytes']<400*1024
        # An episode file renders every block and keeps distinct previews.
        batch=root/'cover-configs.md'
        wide=dict(cfg,format='wide',asset='assets/wide.jpg',headline=['保留一点好奇'],subtitle='')
        portrait=dict(cfg,asset='assets/portrait.jpg')
        def block(config):
            return '<!-- cover-config -->\n```json\n'+json.dumps(config,ensure_ascii=False)+'\n```\n'
        batch.write_text(block(wide)+block(portrait))
        with contextlib.redirect_stdout(io.StringIO()):
            results=render.render([batch],preview_dir=root/'previews',font=font,browser_path=browser)
        assert len(results)==2
        for name,size in [('wide',(1920,817)),('portrait',(1080,1440))]:
            with Image.open(root/f'assets/{name}.jpg') as im:
                assert im.size==size
            assert (root/f'previews/{name}.html').is_file()
        batch.write_text(block(wide)+block(wide))
        try:
            render.render([batch],out_dir=root/'duplicate',font=font,browser_path=browser)
        except ValueError as exc:
            assert 'duplicate output paths' in str(exc)
        else:
            raise AssertionError('duplicate output paths unexpectedly accepted')
        cfg['format']='wide';cfg['headline']=['保留一点好奇'];cfg['subtitle']=''
        # Distinct color blocks allow a local photo to be rendered without external requests.
        photo=Image.new('RGB',(600,800),'#1474ac');photo.paste('#e85930',(300,0,600,800));photo.save(root/'photo.jpg')
        cfg['photo']='photo.jpg';cfg['photo_position']=[25,50];write()
        with contextlib.redirect_stdout(io.StringIO()):
            render.render([source],root/'photo',font=font,browser_path=browser)
        with Image.open(root/'photo/cover.jpg') as im:
            assert im.size==(1920,817)
            assert any(b>r+50 and b>g+20 for r,g,b in im.resize((192,82)).getdata())
        # Oversized text must fail instead of quietly clipping or shrinking.
        cfg['headline']=['很长的标题'*20];write()
        try:
            render.render([source],root/'overflow',font=font,browser_path=browser)
        except ValueError as exc:
            assert 'overflow or overlap' in str(exc)
        else:
            raise AssertionError('oversized text unexpectedly rendered')
        assert not (root/'overflow/cover.jpg').exists()
        # Theme extension changes appearance without editing Python or the template.
        cfg.pop('photo');cfg.pop('photo_position');cfg['headline']=['保留一点好奇'];write()
        original=render.HERE
        shutil.copytree(original,root/'renderer')
        (root/'renderer/themes/test.css').write_text((original/'themes/collage.css').read_text()+'\n.cover{background:#183d35;color:#ffffff}')
        render.HERE=root/'renderer'
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                render.render([source],root/'theme',font=font,browser_path=browser,theme='test')
            with Image.open(root/'theme/cover.jpg') as im:
                assert im.getpixel((10,10))[1]>im.getpixel((10,10))[0]
        finally:
            render.HERE=original
        print('Passed: portrait/wide JPEG, multi-config rendering and previews, duplicate path rejection, photo rendering, overflow rejection, CSS theme extension.')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--font',required=True,type=Path)
    ap.add_argument('--browser',type=Path)
    args=ap.parse_args()
    run(args.font,args.browser)
