"""Behavioral checks using synthetic local media, never private meeting fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from common import private_path, repository, run_ffmpeg
from render import mapped_captions, validate


class ClipRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = private_path(repository() / 'replays/.tests')
        parent.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='clips-', dir=parent)
        cls.base = Path(cls.temp.name)
        cls.source = cls.base / 'source.mp4'
        run_ffmpeg(['-f', 'lavfi', '-i', 'color=c=blue:s=320x180:r=25:d=3',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                    '-shortest', str(cls.source)], cls.base / 'source.log')
        cls.plan = {'version': 1, 'source': 'source.mp4',
                    'event': {'year': 2026, 'episode': 1, 'date': '2026-01-01'},
                    'brand': {'website': 'inspireplanet.cc'},
                    'clips': [{'slug': 'fixture', 'speaker': '测试', 'confirmed': True,
                               'title': ['本地测试'], 'spans': [[0, 1], [2, 3]],
                               'crop': [0, 0, 320, 180], 'cover_time': 2.5,
                               'captions': [[0.1, 0.8, '第一段'], [2.1, 2.8, '第二段']]}]}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def save(self, plan):
        path = self.base / 'edit-plan.json'
        path.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
        return path

    def test_deleted_speech_cannot_appear_in_captions(self):
        plan = copy.deepcopy(self.plan)
        plan['clips'][0]['captions'] = [[0.5, 2.5, '跨过删除区间']]
        with self.assertRaises(ValueError):
            validate(self.save(plan))

    def test_overlapping_spans_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['clips'][0]['spans'] = [[0, 2.5], [2, 3]]
        with self.assertRaises(ValueError):
            validate(self.save(plan))

    def test_source_cannot_be_replaced_by_output(self):
        plan = copy.deepcopy(self.plan)
        plan['source'] = 'fixture-draft.mp4'
        target = self.base / plan['source']
        target.write_bytes(self.source.read_bytes())
        with self.assertRaises(ValueError):
            validate(self.save(plan))
        target.unlink()

    def test_public_output_rejected(self):
        with self.assertRaises(ValueError):
            private_path(repository() / 'events/generated-clips.json')

    def test_timestamps_follow_kept_media(self):
        rows = mapped_captions(self.plan['clips'][0])
        self.assertAlmostEqual(rows[1][0], 1.1)
        self.assertAlmostEqual(rows[1][1], 1.8)

    def test_unconfirmed_selection_does_not_render(self):
        plan = copy.deepcopy(self.plan)
        plan['clips'][0]['confirmed'] = False
        plan['clips'][0]['slug'] = 'not-approved'
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('render.py')),
                                 str(self.save(plan))], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / 'not-approved-draft.mp4').exists())

    def test_video_and_audio_only_export_preserve_source(self):
        original = hashlib.sha256(self.source.read_bytes()).hexdigest()
        script = Path(__file__).with_name('render.py')
        for audio_only in [False, True]:
            with self.subTest(audio_only=audio_only):
                plan = copy.deepcopy(self.plan)
                if audio_only:
                    audio = self.base / 'audio.m4a'
                    run_ffmpeg(['-i', str(self.source), '-vn', '-c:a', 'copy', str(audio)],
                               self.base / 'audio.log')
                    plan['source'] = audio.name
                    plan['clips'][0]['crop'] = None
                    plan['clips'][0]['slug'] = 'audio-only'
                command = [sys.executable, str(script), str(self.save(plan))]
                if audio_only:
                    command.append('--cover')
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                slug = plan['clips'][0]['slug']
                qa = json.loads((self.base / 'work' / f'{slug}-qa.json').read_text())
                self.assertTrue(qa['decode_passed'])
                self.assertAlmostEqual(qa['seconds'], 2.0, delta=0.15)
                self.assertEqual((qa['width'], qa['height']), (1080, 1920))
                self.assertTrue((self.base / f'{slug}.srt').is_file())
                self.assertEqual((self.base / f'{slug}-cover.jpg').is_file(), audio_only)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), original)


if __name__ == '__main__':
    unittest.main()
