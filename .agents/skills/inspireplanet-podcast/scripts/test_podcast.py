import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import podcast


class PodcastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = podcast.repository() / 'replays/.tests'
        cls.base.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=self.base)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.wav'
        # A synthetic tone checks retained audio without any meeting input.
        podcast.ffmpeg(['-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=8:sample_rate=32000', str(self.source)])
        self.digest = hashlib.sha256(self.source.read_bytes()).digest()
        self.plan = self.root / 'edit-plan.json'
        self.data = {'source': 'source.wav', 'cuts': [
            {'start': 0, 'end': 1, 'reason': 'test', 'evidence': 'synthetic'},
            {'start': 3, 'end': 4, 'reason': 'test', 'evidence': 'synthetic'}],
            'chapters': [{'source_seconds': 1, 'title': 'Opening'},
                         {'source_seconds': 5, 'title': 'Next'}]}
        self.save()

    def tearDown(self):
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), self.digest)
        self.tmp.cleanup()

    def save(self):
        self.plan.write_text(json.dumps(self.data))

    def test_mapping_and_render(self):
        source, meta, spans, chapters = podcast.load_plan(self.plan)
        self.assertEqual(podcast.map_time(5, spans), 3)
        report = podcast.render(self.plan, self.root / 'export')
        self.assertAlmostEqual(report['output_seconds'], 6, delta=.1)
        self.assertTrue(report['full_decode_passed'])
        self.assertFalse(report['human_listening_reviewed'])
        actual = json.loads((self.root / 'export/chapters.json').read_text())
        self.assertEqual([c['seconds'] for c in actual], [0, 3])

    def test_check_does_not_write(self):
        podcast.render(self.plan, self.root / 'export', check=True)
        self.assertFalse((self.root / 'export').exists())

    def test_overlap_and_bounds(self):
        for a,b in [(0.5, 2), (3, 9), (-1, 2), (4, 3)]:
            self.data['cuts'][1].update(start=a, end=b)
            self.save()
            with self.assertRaises(ValueError): podcast.load_plan(self.plan)

    def test_nonfinite_and_boolean(self):
        for v in [float('nan'), float('inf'), True]:
            self.data['cuts'][0]['start'] = v
            self.save()
            with self.assertRaises(ValueError): podcast.load_plan(self.plan)

    def test_deleted_chapter(self):
        self.data['chapters'][0]['source_seconds'] = .5
        self.save()
        with self.assertRaises(ValueError): podcast.load_plan(self.plan)

    def test_whole_file_and_missing_evidence(self):
        self.data['cuts'] = [{'start':0, 'end':8, 'reason':'test', 'evidence':'synthetic'}]
        self.save()
        with self.assertRaises(ValueError): podcast.load_plan(self.plan)
        del self.data['cuts'][0]['evidence']
        self.save()
        with self.assertRaises(ValueError): podcast.load_plan(self.plan)

    def test_input_and_public_output_protection(self):
        for output in [self.root, podcast.repository() / 'events/test-export']:
            with self.assertRaises(ValueError): podcast.render(self.plan, output)

    def test_analyze_silence_is_only_candidate(self):
        silence = self.root / 'silence.wav'
        podcast.ffmpeg(['-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'anullsrc=r=32000:cl=mono', '-t', '5', str(silence)])
        podcast.analyze(silence, self.root / 'analysis')
        data = json.loads((self.root / 'analysis/analysis.json').read_text())
        self.assertEqual(len(data['silence_candidates']), 1)
        self.assertEqual(data['silence_candidates'][0]['status'], 'candidate')
        self.assertFalse((self.root / 'analysis/podcast.m4a').exists())

    def test_symlink_output_protection(self):
        output = self.root / 'export'
        output.mkdir()
        (output / 'podcast.m4a').symlink_to(self.source)
        with self.assertRaises(ValueError): podcast.render(self.plan, output)


if __name__ == '__main__':
    unittest.main()
