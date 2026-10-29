"""Synthetic data only; never reads Tencent or writes public meeting content."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import latest_transcript as l
import meeting_content as m

POLICY = {'min_spoken_chars': 1000, 'timezone': 'Asia/Shanghai'}
TITLE = '启发星球，互相赋能'
LONG = '合成发言人(00:01):\n' + '真实讨论' * 400 + '\n'
SHORT = '合成发言人(00:01):\n你好。\n'


def row(sub, time):
    return {'subject': TITLE, 'meeting_id': 'synthetic-series', 'sub_meeting_id': sub,
            'start_time': time, 'records': []}


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.formal = row('formal', '2026-10-17T00:00:00Z')
        self.accidental = row('accidental', '2026-10-17T08:00:00Z')

    def select(self, rows, responses):
        def fetch(client, item):
            value = responses[item['sub_meeting_id']]
            if isinstance(value, Exception):
                raise value
            return value
        with patch.object(m, 'fetch_occurrence', side_effect=fetch) as calls, redirect_stdout(io.StringIO()):
            result = l.select_content_occurrence(object(), rows, POLICY)
            return result, calls.call_count

    def test_counts_only_spoken_letters_and_digits(self):
        self.assertEqual(l.spoken_chars('很长的发言人姓名(00:01):\n！！ 你 好 123 。\n'), 5)

    def test_older_formal_beats_newer_accidental_and_logs_no_text_or_speaker(self):
        output = io.StringIO()
        with patch.object(m, 'fetch_occurrence', side_effect=[LONG, SHORT]), redirect_stdout(output):
            chosen, text = l.select_content_occurrence(object(), [self.accidental, self.formal], POLICY)
        self.assertEqual(chosen, self.formal)
        self.assertEqual(text, LONG)
        self.assertIn('spoken_chars=1600', output.getvalue())
        self.assertNotIn('合成发言人', output.getvalue())
        self.assertNotIn('真实讨论', output.getvalue())

    def test_two_substantial_transcripts_stop_even_if_one_is_much_longer(self):
        with self.assertRaises(m.SafeError):
            self.select([self.formal, self.accidental], {'formal': LONG * 2, 'accidental': LONG})

    def test_only_short_occurrences_stop_and_do_not_misassign_an_episode(self):
        with self.assertRaises(m.SafeError):
            self.select([self.formal], {'formal': SHORT})

    def test_verified_empty_transcript_is_ignored_but_failed_read_is_not(self):
        result, count = self.select([self.formal, self.accidental],
                                    {'formal': LONG, 'accidental': m.NoTranscript('empty')})
        self.assertEqual(result[0], self.formal)
        self.assertEqual(count, 2)
        with self.assertRaises(m.SafeError):
            self.select([self.formal, self.accidental],
                        {'formal': LONG, 'accidental': m.SafeError('unreadable')})

    def test_bounded_candidates_and_duplicate_metadata(self):
        rows = [row(str(i), f'2026-10-17T{str(i).zfill(2)}:00:00Z') for i in range(9)]
        with patch.object(m, 'fetch_occurrence') as fetch, self.assertRaises(m.SafeError):
            l.select_content_occurrence(object(), rows, POLICY)
        fetch.assert_not_called()
        _, count = self.select([self.formal, self.formal], {'formal': LONG})
        self.assertEqual(count, 1)
        with self.assertRaises(m.SafeError):
            self.select([self.formal, dict(self.formal, records=[{'different': True}])], {'formal': LONG})

    def test_policy_is_explicit_and_validates_timezone(self):
        self.assertIsNone(l.transcript_policy({}))
        self.assertEqual(l.transcript_policy({'transcript_selection': POLICY}), POLICY)
        for policy in ({'min_spoken_chars': True, 'timezone': 'Asia/Shanghai'},
                       {'min_spoken_chars': 1000, 'timezone': 'not-a-zone'}):
            with self.assertRaises(m.SafeError):
                l.transcript_policy({'transcript_selection': policy})

    def test_prepare_groups_same_day_without_reading_any_transcript(self):
        config = {'title': TITLE, 'lookback_days': 90, 'anchor':
                  {'date': '2026-10-10', 'episode': '40', 'meeting_id': 'synthetic-series'},
                  'transcript_selection': POLICY}
        archive = {'keys': set(), 'dates': set(), 'mapping': {}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps(config))
            def run(args):
                if args[:3] == ['git', 'branch', '--show-current']: return 'main'
                if args[:3] == ['git', 'status', '--porcelain']: return ''
                if args[:2] == ['git', 'rev-parse']: return 'a' * 40
                raise AssertionError(args)
            with patch.object(l, 'archives', return_value=archive), \
                 patch.object(l, 'discover', return_value=[self.formal, self.accidental]), \
                 patch.object(m, 'fetch_occurrence') as fetch, redirect_stdout(io.StringIO()):
                l.main(['prepare'], root=root, run=run, client_factory=object,
                       now=datetime(2026, 10, 18, tzinfo=timezone.utc))
            fetch.assert_not_called()
            plan = json.loads((root / '.git/latest-plan.json').read_text())
            self.assertEqual(len(plan['candidate_meetings']), 2)
            self.assertFalse((root / 'events').exists())

    def test_fetch_rewrites_identity_to_actual_formal_occurrence_not_newer_entry(self):
        archive = {'keys': set(), 'dates': set(), 'mapping': {'2026-10-17': {'41'}}}
        meta = l.instance(self.accidental)
        plan = {'skip': False, 'base': 'main', 'head': 'a' * 40, 'meeting': self.accidental,
                'metadata': meta, 'date': meta['date'], 'episode': None,
                'event': 'incoming/meetings/' + meta['instance_key'],
                'branch': 'content/meeting-' + meta['instance_key'],
                'candidate_meetings': [self.formal, self.accidental], 'transcript_policy': POLICY}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir()
            state = root / '.git/latest-plan.json'; state.write_text(json.dumps(plan))
            def run(args):
                if args[:3] == ['git', 'branch', '--show-current']: return 'main'
                if args[:2] == ['git', 'rev-parse']: return 'a' * 40
                raise AssertionError(args)
            with patch.object(l, 'archives', return_value=archive), \
                 patch.object(m, 'fetch_occurrence', side_effect=[LONG, SHORT]), redirect_stdout(io.StringIO()):
                l.main(['fetch'], root=root, run=run, client_factory=object)
            saved = json.loads(state.read_text())
            self.assertEqual(saved['metadata'], l.instance(self.formal))
            self.assertEqual(saved['episode'], '41')
            self.assertEqual(saved['event'], 'events/2026/20261017-ep41')
            self.assertEqual((root / '.git/latest-transcript.txt').read_text(), LONG)
            self.assertFalse((root / 'events').exists())

    def test_date_candidates_never_mix_another_calendar_day(self):
        outside = row('other-day', '2026-10-18T00:00:00Z')
        candidates = [self.formal, self.accidental, outside]
        class Client:
            def call(self, name, args):
                return {'meeting_info_list': candidates, 'has_more': False}
        self.assertEqual(l.historical_candidates(Client(), {'title': TITLE}, '2026-10-17'),
                         [self.formal, self.accidental])


if __name__ == '__main__':
    unittest.main()
