"""Verify stable bundles, partial replacement, and failed validation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image

spec = importlib.util.spec_from_file_location('publish', Path(__file__).with_name('render-publish.py'))
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)


class BundleTest(unittest.TestCase):
    def test_partial_update_and_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            event = base / '20261010-ep40'
            event.mkdir()
            source = base / 'source'
            for c in ('xhs', 'sph'):
                for slug in ('liying', 'mocha'):
                    post = source / c / slug
                    post.mkdir(parents=True)
                    for n in (1, 2):
                        Image.new('RGB', (1080, 1440), 'white').save(post / f'{n:02}.jpg')
            root = publish.run(event, base / 'output', ['xhs', 'sph'], imported=source)
            untouched = (root / 'ready/sph/liying/01.jpg').read_bytes()
            (source / 'xhs/liying/02.jpg').unlink()
            Image.new('RGB', (1080, 1440), 'red').save(source / 'xhs/liying/01.jpg')
            same = publish.run(event, base / 'output', ['xhs'], slug='liying', imported=source)
            self.assertEqual(root, same)
            self.assertFalse((root / 'ready/xhs/liying/02.jpg').exists())
            self.assertEqual((root / 'ready/sph/liying/01.jpg').read_bytes(), untouched)
            self.assertTrue((root / 'ready/xhs/mocha/02.jpg').exists())
            history = list((root / 'history').iterdir())
            self.assertEqual(len(history), 1)
            self.assertTrue((history[0] / 'ready/xhs/liying/02.jpg').is_file())
            with zipfile.ZipFile(root / 'all.zip') as z:
                self.assertEqual(len(z.namelist()), 7)
                self.assertNotIn('xhs/liying/02.jpg', z.namelist())
                self.assertIsNone(z.testzip())
            before = (root / 'all.zip').read_bytes()
            Image.new('RGB', (10, 10)).save(source / 'xhs/liying/01.jpg')
            with self.assertRaises(ValueError):
                publish.run(event, base / 'output', ['xhs'], slug='liying', imported=source)
            self.assertEqual((root / 'all.zip').read_bytes(), before)
            self.assertEqual(len(list((root / 'history').iterdir())), 1)
            self.assertFalse((root / '.render.lock').exists())
            self.assertFalse(list(root.glob('.render-*')))

    def test_promotion_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'ready').mkdir()
            (root / 'ready/old.jpg').write_bytes(b'old')
            (root / 'preview.html').write_text('old preview')
            stage = root / 'stage'
            (stage / 'ready').mkdir(parents=True)
            (stage / 'ready/new.jpg').write_bytes(b'new')
            (stage / 'preview.html').write_text('new preview')
            rename = Path.rename
            def fail_preview(path, target):
                if path == stage / 'preview.html':
                    raise OSError('simulated promotion failure')
                return rename(path, target)
            with patch.object(Path, 'rename', fail_preview):
                with self.assertRaises(OSError):
                    publish.promote(root, stage)
            self.assertEqual((root / 'ready/old.jpg').read_bytes(), b'old')
            self.assertFalse((root / 'ready/new.jpg').exists())
            self.assertEqual((root / 'preview.html').read_text(), 'old preview')

    def test_output_and_lock(self):
        with self.assertRaises(ValueError):
            publish.external_root(publish.REPO / 'assets')
        with tempfile.TemporaryDirectory() as temp:
            with publish.locked(Path(temp)):
                with self.assertRaises(FileExistsError):
                    with publish.locked(Path(temp)):
                        pass


if __name__ == '__main__':
    unittest.main()
