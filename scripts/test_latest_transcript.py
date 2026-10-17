"""Synthetic fixtures; never real Tencent payloads."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib
import sys
sys.path.insert(0, str(Path(__file__).parent))
import meeting_content as m


class LatestTests(unittest.TestCase):
    def latest(self):
        self.assertIsNotNone(importlib.util.find_spec('latest_transcript'), 'latest workflow implementation missing')
        return importlib.import_module('latest_transcript')

    def row(self, day, **kw):
        return dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id=day,
                    start_time=day + 'T00:00:00Z', **kw)

    def test_history_local_date_matches_utc_shanghai_and_la_zones(self):
        l = self.latest()
        import tempfile, json
        from unittest.mock import patch
        # Same user local calendar day 2025-12-13, seen from three zones:
        # 2025-12-13T02:00Z (UTC), 2025-12-13T10:00+08:00 (Beijing) and
        # 2025-12-13T17:00-08:00 = 2025-12-14T01:00Z (Los Angeles).
        for label, zone, start, expected_start, expected_end in (
                ('utc', 'UTC', '2025-12-13T02:00:00Z', '2025-12-13T00:00:00Z', '2025-12-14T00:00:00Z'),
                ('shanghai', 'Asia/Shanghai', '2025-12-12T17:00:00Z', '2025-12-12T16:00:00Z', '2025-12-13T16:00:00Z'),
                ('la', 'America/Los_Angeles', '2025-12-14T01:00:00Z', '2025-12-13T08:00:00Z', '2025-12-14T08:00:00Z')):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
                (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': '启发星球，互相赋能'}))
                row = dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id=start,
                           start_time=start, records=[{'record_file_id': 'f', 'meeting_record_id': 'r',
                                                       'type': '转写', 'duration': '01:00'}])
                calls = []
                class Client:
                    def call(self, name, args):
                        calls.append((name, args))
                        if name == 'get_user_ended_meetings':
                            return {'meeting_info_list': [row], 'has_more': False}
                        if name == 'get_records_list':
                            return {'record_meetings': [dict(meeting_id='series', sub_meeting_id=start,
                                    meeting_record_id='r', record_files=[{'record_file_id': 'f'}])], 'has_more': False}
                        return {'minutes': {'paragraphs': [{'pid': '0', 'start_time': 0,
                            'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': '合成全文'}]}]}]}, 'more': False}
                with patch.object(m, 'event_identity', side_effect=AssertionError('EP must not gate check')):
                    l.main(['fetch-check', '--date', '2025-12-13', '--timezone', zone], root=root, client_factory=Client,
                           run=lambda args: self.fail('fetch-check must not need GitHub'))
                self.assertIn('合成全文', (root / '.git/meeting-content-fetch-check.txt').read_text())
                self.assertEqual([n for n, _ in calls],
                                 ['get_user_ended_meetings', 'get_records_list', 'get_transcripts_details'])
                # Window must span the union of all three local days, not UTC only.
                self.assertEqual(calls[0][1]['start_time'], expected_start)
                self.assertEqual(calls[0][1]['end_time'], expected_end)

    def test_history_local_date_same_day_multiple_or_none_stops(self):
        l = self.latest()
        import tempfile, json
        day = '2025-12-13'
        first = dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='a',
                     start_time='2025-12-13T02:00:00Z', records=[])
        second = dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='b',
                      start_time='2025-12-13T04:00:00Z', records=[])
        class Multi:
            def call(self, name, args):
                return {'meeting_info_list': [first, second], 'has_more': False}
        class NoneRow:
            def call(self, name, args):
                return {'meeting_info_list': [dict(first, subject='Other')], 'has_more': False}
        for client in (Multi(), NoneRow()):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
                (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': '启发星球，互相赋能'}))
                with self.assertRaises(m.SafeError):
                    l.main(['fetch-check', '--date', day], root=root, client_factory=lambda c=client: c,
                           run=lambda args: self.fail('must not need GitHub'))

    def test_history_pick_selects_numbered_unarchived_occurrence(self):
        l = self.latest()
        import tempfile, json
        day1, day2 = '2026-07-25', '2026-08-15'
        row1 = dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id=day1,
                    start_time=day1 + 'T02:00:00Z',
                    records=[{'record_file_id': 'f', 'meeting_record_id': 'r', 'type': '转写', 'duration': '01:00'}])
        row2 = dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id=day2,
                    start_time=day2 + 'T02:00:00Z',
                    records=[{'record_file_id': 'g', 'meeting_record_id': 'r2', 'type': '转写', 'duration': '01:00'}])
        for mapped in (False, True):
            with self.subTest(mapped=mapped), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir(); (root / 'events').mkdir()
                (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': row1['subject']}))
                def run(args):
                    if args[:2] in (['git', 'fetch'], ['git', 'ls-remote']): return ''
                    if args[:3] == ['gh', 'api', '--paginate']: return '[[]]'
                    if args[:2] == ['git', 'ls-tree']:
                        return 'events/2026/20260815-ep33/recap.md\n' if mapped else ''
                    if args[:3] == ['git', 'branch', '--show-current']: return 'main'
                    if args[:2] == ['git', 'rev-parse']: return 'a' * 40
                    if args[:3] == ['git', 'status', '--porcelain']: return ''
                    raise AssertionError(args)
                class Client:
                    def call(self, name, args):
                        if name == 'get_user_ended_meetings':
                            return {'meeting_info_list': [row1, row2], 'has_more': False}
                        raise AssertionError('discovery only')
                # pick=2 selects the second numbered occurrence (2026-08-15), never the latest.
                l.main(['prepare', '--pick', '2'], root=root, run=run, client_factory=Client,
                       now=datetime(2026, 10, 15, 12, tzinfo=timezone.utc))
                plan = json.loads((root / '.git/latest-plan.json').read_text())
                self.assertFalse(plan['skip'])
                self.assertEqual(plan['date'], day2)
                self.assertEqual(plan['episode'], '33' if mapped else None)
                expected = 'events/2026/20260815-ep33' if mapped else 'incoming/meetings/' + l.instance(row2)['instance_key']
                self.assertEqual(plan['event'], expected)

    def test_history_pick_invalid_index_and_inputs_fail_closed(self):
        l = self.latest()
        import tempfile, json
        row = dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='2026-08-15',
                   start_time='2026-08-15T02:00:00Z', records=[])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': row['subject']}))
            def run(args):
                if args[:2] in (['git', 'fetch'], ['git', 'ls-remote']): return ''
                if args[:3] == ['gh', 'api', '--paginate']: return '[[]]'
                if args[:2] == ['git', 'ls-tree']: return ''
                if args[:3] == ['git', 'branch', '--show-current']: return 'main'
                if args[:2] == ['git', 'rev-parse']: return 'a' * 40
                if args[:3] == ['git', 'status', '--porcelain']: return ''
                raise AssertionError(args)
            class Client:
                def call(self, name, args):
                    if name == 'get_user_ended_meetings':
                        return {'meeting_info_list': [row], 'has_more': False}
                    raise AssertionError('discovery only')
            # Only one occurrence exists; pick=2 is out of range.
            with self.assertRaises(m.SafeError) as ctx:
                l.main(['prepare', '--pick', '2'], root=root, run=run, client_factory=Client,
                       now=datetime(2026, 10, 15, 12, tzinfo=timezone.utc))
            self.assertIn('序号', str(ctx.exception))
            for argv in (['prepare', '--pick', '0'], ['prepare', '--pick', 'abc'],
                         ['fetch-check', '--pick', '1'], ['prepare', '--pick', '1', '--date', '2026-08-15'],
                         ['fetch-check', '--date', ''], ['scan', '--date', '2026-08-15']):
                with self.subTest(argv=argv), self.assertRaises(m.SafeError):
                    l.main(argv, root=root, run=lambda args: self.fail('invalid input must not run Git/GitHub'),
                           client_factory=lambda: self.fail('invalid input must not read remote'))

    def test_episode_hint_is_display_only_from_unambiguous_directories(self):
        l = self.latest()
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / 'events/2026/20261010-ep40'; d.mkdir(parents=True); (d / 'transcript.txt').write_text('x')
            for ep in ('02', '03'):
                e = root / f'events/2025/20250428-ep{ep}'; e.mkdir(parents=True); (e / 'README.md').write_text('x')
            hints = l.episode_hints(root)
            self.assertEqual(hints.get('2026-10-10'), '2026-ep40')
            self.assertNotIn('2025-04-28', hints)

    def test_history_blank_scan_is_bounded_and_reports_counts_only(self):
        l = self.latest()
        import io, tempfile, json
        from contextlib import redirect_stdout
        config = {'title': '启发星球，互相赋能'}
        rows = [
            dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='a',
                 start_time='2025-12-13T02:00:00Z',
                 records=[{'record_file_id': 'f', 'meeting_record_id': 'r', 'type': '转写', 'duration': '01:00'}]),
            dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='b',
                 start_time='2026-07-25T02:00:00Z', records=[]),
            dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='c',
                 start_time='2026-01-01T02:00:00Z', records=[]),
            dict(subject='其他会议', meeting_id='series', sub_meeting_id='d',
                 start_time='2026-02-01T02:00:00Z', records=[]),
            dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='e',
                 start_time='2027-01-01T02:00:00Z', records=[]),
            dict(subject='启发星球，互相赋能', meeting_id='series', sub_meeting_id='f',
                 start_time='2025-01-01T02:00:00Z', records=[]),
        ]
        calls = []
        class Client:
            def call(self, name, args):
                calls.append(name)
                if name == 'get_user_ended_meetings':
                    return {'meeting_info_list': rows, 'has_more': False}
                if name == 'get_records_list':
                    return {'record_meetings': [
                        dict(meeting_id='series', sub_meeting_id='b', meeting_record_id='rb',
                             record_files=[{'record_file_id': 'g'}])], 'has_more': False}
                raise AssertionError(name)
        now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
        archive = {'keys': set(), 'dates': {'2026-01-01'}, 'mapping': {}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / 'events/2026/20260725-ep29'; d.mkdir(parents=True); (d / 'transcript.txt').write_text('x')
            out = io.StringIO()
            with redirect_stdout(out):
                summary = l.scan(Client(), config, archive, now, root=root)
        text = out.getvalue()
        self.assertEqual(summary['unarchived'], 2)
        self.assertEqual(summary['probed'], 2)
        self.assertIn('unarchived=2', text)
        # Numbered rows with real date and weekday; EP hint is display-only.
        self.assertIn('[1] 2025-12-13', text)
        self.assertIn('[2] 2026-07-25', text)
        self.assertIn('周六', text)
        self.assertIn('readable=true', text)
        self.assertIn('readable=false', text)
        self.assertIn('ep_hint=2026-ep29', text)
        self.assertIn('pick=N', text)
        self.assertNotIn('其他会议', text)
        self.assertNotIn('2027-01-01', text)
        self.assertNotIn('2025-01-01', text)
        self.assertEqual(calls.count('get_user_ended_meetings'), 5)
        self.assertEqual(calls.count('get_records_list'), 1)

    def test_history_scan_caps_windows_and_probes(self):
        l = self.latest()
        import io
        from contextlib import redirect_stdout
        config = {'title': 'P'}
        base = datetime(2025, 11, 1, tzinfo=timezone.utc)
        rows = [dict(subject='P', meeting_id='series', sub_meeting_id='s%d' % i,
                     start_time=l.iso(base + timedelta(days=12 * i)), records=[]) for i in range(25)]
        calls = []
        class Client:
            def call(self, name, args):
                calls.append(name)
                if name == 'get_user_ended_meetings':
                    return {'meeting_info_list': rows, 'has_more': False}
                if name == 'get_records_list':
                    return {'record_meetings': [], 'has_more': False}
                raise AssertionError(name)
        now = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
        out = io.StringIO()
        with redirect_stdout(out):
            summary = l.scan(Client(), config, {'keys': set(), 'dates': set(), 'mapping': {}}, now)
        text = out.getvalue()
        self.assertEqual(summary['windows'], 5)
        self.assertEqual(summary['unarchived'], 25)
        self.assertEqual(summary['probed'], 20)
        self.assertIn('windows=5', text)
        self.assertIn('unarchived=25', text)
        self.assertIn('probed=20', text)
        self.assertEqual(calls.count('get_user_ended_meetings'), 5)
        self.assertEqual(calls.count('get_records_list'), 20)

    def test_history_mapped_directory_and_unmapped_pending_reuse_pipeline(self):
        l = self.latest()
        import tempfile, json
        from unittest.mock import patch
        day = '2025-10-11'
        row = self.row(day, records=[{'record_file_id': 'f', 'meeting_record_id': 'r',
                                    'type': '转写', 'duration': '01:00'}])
        for mapped in (True, False):
            with self.subTest(mapped=mapped), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir(); (root / 'events').mkdir()
                (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': row['subject']}))
                (root / 'events/README.md').write_text('# Synthetic index\n')
                def run(args):
                    if args[:2] in (['git', 'fetch'], ['git', 'ls-remote']): return ''
                    if args[:3] == ['gh', 'api', '--paginate']: return '[[]]'
                    if args[:2] == ['git', 'ls-tree']:
                        return 'events/2025/20251011-ep48/recap.md\n' if mapped else ''
                    if args[:3] == ['git', 'branch', '--show-current']: return 'main'
                    if args[:2] == ['git', 'rev-parse']: return 'a'*40
                    if args[:3] == ['git', 'status', '--porcelain']: return ''
                    raise AssertionError(args)
                class Client:
                    def call(self, name, args):
                        if name == 'get_user_ended_meetings':
                            return {'meeting_info_list': [row], 'has_more': False}
                        raise AssertionError('discovery only')
                with patch.object(l, 'episode_for', side_effect=AssertionError('never infer historical EP')):
                    l.main(['prepare', '--date', day], root=root, run=run, client_factory=Client)
                plan = json.loads((root / '.git/latest-plan.json').read_text())
                self.assertFalse(plan['skip'])
                self.assertEqual(plan['episode'], '48' if mapped else None)
                expected = 'events/2025/20251011-ep48' if mapped else 'incoming/meetings/' + l.instance(row)['instance_key']
                self.assertEqual(plan['event'], expected)
                with patch.object(m, 'fetch_occurrence', return_value='合成甲(00:01):\n合成全文\n') as fetch:
                    l.main(['fetch'], root=root, run=run, client_factory=Client)
                    fetch.assert_called_once()
                l.main(['write'], root=root, run=run)
                self.assertTrue((root / expected / 'metadata.json').is_file())
                with self.assertRaises(m.SafeError): l.main(['write'], root=root, run=run)
                self.assertFalse(list(root.rglob('summary.json')))

    def test_history_empty_or_invalid_date_never_falls_back_to_latest(self):
        l = self.latest()
        import tempfile, json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': 'project'}))
            for day in ('', '2025-02-30', '2025-1-1'):
                with self.subTest(day=day), patch.object(l, 'discover', side_effect=AssertionError('must not select latest')):
                    with self.assertRaises(m.SafeError):
                        l.main(['prepare', '--date', day], root=root, run=lambda args: self.fail('invalid date must not run Git/GitHub'),
                               client_factory=lambda: self.fail('invalid date must not read remote'))

    def test_history_ci_uses_date_and_scan_readonly_entries(self):
        workflow = (Path(__file__).parents[1] / '.github/workflows/content-ci.yml').read_text()
        self.assertNotIn('CONTENT_MEETING_ID', workflow)
        self.assertNotIn('--episode', workflow)
        self.assertIn('scripts/latest_transcript.py scan', workflow)

    def test_history_workflow_timezone_and_operation(self):
        workflow = (Path(__file__).parents[1] / '.github/workflows/meeting-history.yml').read_text()
        for required in ('inputs.operation', 'inputs.date', 'inputs.timezone',
                         'default: Asia/Shanghai', 'default: 查找未归档会议',
                         'scripts/latest_transcript.py scan',
                         'scripts/latest_transcript.py prepare --date "$CONTENT_DATE" --timezone "$CONTENT_TIMEZONE"',
                         'scripts/latest_transcript.py fetch', 'scripts/latest_transcript.py write',
                         'scripts/latest_transcript.py publish', 'if: always()'):
            self.assertIn(required, workflow)
        for forbidden in ('inputs.pick', 'inputs.mode', 'CONTENT_PICK', 'CONTENT_MODE',
                          'inputs.episode', '--episode', 'CONTENT_YEAR'):
            self.assertNotIn(forbidden, workflow)

    def test_complete_pagination_exact_title_true_utc_window_latest(self):
        l = self.latest()
        calls = []
        test = self
        class Client:
            def call(self, name, args):
                calls.append(args)
                first = not args['page_token']
                return {'meeting_info_list': ([test.row('2026-10-10'), test.row('2026-10-18'),
                    dict(test.row('2026-10-17'), subject='Other project')] if first else
                    [test.row('2026-07-01'), dict(test.row('2026-10-16'), start_time='2026-10-16T17:00:00-07:00')]),
                    'has_more': first, 'next_page_token': 'next' if first else ''}
        now = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)
        rows = l.discover(Client(), {'title': '启发星球，互相赋能', 'lookback_days': 90}, now)
        self.assertEqual([m.utc_day(r['start_time']) for r in rows], ['2026-10-10', '2026-10-17'])
        self.assertEqual(calls[0]['end_time'], '2026-10-17T12:00:00Z')
        self.assertEqual(calls[0]['start_time'], '2026-07-19T12:00:00Z')
        with self.assertRaises(m.SafeError): l.discover(Client(), {'title': 'x', 'lookback_days': 91}, now)

    def test_scheduled_beijing_day_never_falls_back_to_last_week(self):
        l = self.latest()
        now = datetime(2026, 10, 17, 2, 7, tzinfo=timezone.utc)  # Beijing Sat 10:07
        last_week = self.row('2026-10-10')
        current = self.row('2026-10-17')
        archive = {'keys': set(), 'dates': set(), 'mapping': {}}

        # If today's meeting has not ended, the ended-meetings API only
        # contains last week's row. Do not draft it in a scheduled run.
        self.assertEqual(l.scheduled_beijing_occurrences([last_week], now), [])
        self.assertTrue(l.plan_latest(l.scheduled_beijing_occurrences([last_week], now),
                                      archive, {})['skip'])

        selected = l.scheduled_beijing_occurrences([last_week, current], now)
        self.assertEqual(selected, [current])
        self.assertEqual(l.plan_latest(selected, archive, {})['meeting'], current)

        # Beijing has no DST; avoid UTC-date-only matching at midnight.
        early = {**last_week, 'start_time': '2026-10-16T17:00:00Z'}
        self.assertEqual(l.scheduled_beijing_occurrences([early], now), [early])

        # A delayed job landing on Beijing Sunday must not backfill Saturday.
        late = datetime(2026, 10, 17, 20, tzinfo=timezone.utc)
        self.assertEqual(l.scheduled_beijing_occurrences([current], late), [])

    def test_scheduled_candidate_filter_requires_timezone_aware_now(self):
        l = self.latest()
        with self.assertRaises(m.SafeError):
            l.scheduled_beijing_occurrences([self.row('2026-10-17')],
                                              datetime(2026, 10, 17, 2, 7))

    def test_no_new_main_and_open_draft_dedupe_never_fall_back(self):
        l = self.latest()
        old, new = self.row('2026-10-10'), self.row('2026-10-17')
        empty = {'keys': set(), 'dates': set(), 'mapping': {}}
        self.assertTrue(l.plan_latest([], empty, {})['skip'])
        for archive in (dict(empty, keys={l.instance(new)['instance_key']}),
                        dict(empty, dates={'2026-10-17'})):
            plan = l.plan_latest([old, new], archive, {})
            self.assertTrue(plan['skip'])
        with __import__('tempfile').TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = l.instance(new)['instance_key']
            metadata = l.instance(new)
            files = ['events/2026/20261010-ep40/transcript.txt',
                     'incoming/meetings/' + key + '/metadata.json',
                     'incoming/meetings/' + key + '/transcript.txt']
            def run(args):
                if args[:3] == ['gh', 'api', '--paginate']:
                    return '[[{"head":{"sha":"' + 'a'*40 + '"}}]]'
                if args[:2] == ['git', 'fetch']: return ''
                if args[:2] == ['git', 'ls-tree']: return '\n'.join(files if args[-1] == 'origin/main' else files[1:])
                if args[:2] == ['git', 'show']: return __import__('json').dumps(metadata)
                raise AssertionError(args)
            archive = l.archives(run)
            self.assertIn(key, archive['keys'])
            self.assertIn('2026-10-10', archive['dates'])
            self.assertIn('2026-10-17', archive['dates'])
            self.assertTrue(l.plan_latest([old, new], archive, {})['skip'])

    def test_verified_date_first_next41_only_proven_unique_continuity(self):
        l = self.latest()
        config = {'anchor': {'date': '2026-10-10', 'episode': '40', 'meeting_id': 'series'}}
        anchor, new = self.row('2026-10-10'), self.row('2026-10-17')
        self.assertEqual(l.episode_for(anchor, [anchor], config), '40')
        self.assertEqual(l.episode_for(new, [anchor, new], config), '41')
        for rows in ([new], [anchor, self.row('2026-10-24')],
                     [anchor, self.row('2026-10-11'), new],
                     [anchor, dict(new, meeting_id='second'), new],
                     [anchor, self.row('2027-01-02')], [anchor, self.row('2026-10-03')]):
            with self.subTest(rows=len(rows)):
                self.assertIsNone(l.episode_for(rows[-1], rows, config))
        self.assertIsNone(l.episode_for(dict(new, meeting_id='cycle-changed'),
                                       [anchor, dict(new, meeting_id='cycle-changed')], config))

    def test_pending_and_known_writes_scoped_real_git_public_draft(self):
        l = self.latest()
        import tempfile, subprocess, json
        for episode in (None, '41'):
            with self.subTest(episode=episode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / 'repo'; root.mkdir()
                remote = Path(tmp) / 'remote.git'
                def git(*args):
                    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout
                git('init', '--bare', str(remote)); git('init', '-b', 'main')
                git('config', 'user.name', 'Synthetic'); git('config', 'user.email', 'test@example.invalid')
                git('remote', 'add', 'origin', str(remote))
                (root / 'events').mkdir(); (root / 'events/README.md').write_text('# Test\n')
                git('add', '.'); git('commit', '-m', 'baseline'); git('push', 'origin', 'main')
                metadata = l.instance(self.row('2026-10-17'))
                event = m.event_identity(metadata['date'], episode)[0] if episode else 'incoming/meetings/' + metadata['instance_key']
                plan = dict(latest=True, event=event, metadata=metadata, episode=episode,
                            date=metadata['date'], branch='content/meeting-' + metadata['instance_key'],
                            base='main', head=git('rev-parse', 'HEAD').strip())
                text = '合成甲(00:01):\n这是合成转写。\n'
                paths = l.write(root, plan, text)
                self.assertEqual(set(paths), set(l.allowed_paths(plan)))
                self.assertEqual((root / event / 'transcript.txt').read_text(), text)
                self.assertTrue((root / event / 'metadata.json').is_file())
                self.assertFalse(list(root.rglob('summary.json')))
                with self.assertRaises(m.SafeError): l.write(root, plan, text)
                created = []
                def run(args):
                    if args[0] == 'git': return git(*args[1:])
                    if args[:3] == ['gh', 'pr', 'create']:
                        self.assertIn('--draft', args); created.append(args); return 'synthetic'
                    if args[:3] == ['gh', 'pr', 'view']:
                        return json.dumps(dict(state='OPEN', isDraft=True, headRefName=plan['branch'],
                            baseRefName='main', files=[{'path': p} for p in paths]))
                    raise AssertionError(args)
                (root / 'evil.txt').write_text('unscoped')
                with self.assertRaises(m.SafeError): m.publish(root, plan, run)
                self.assertFalse(created); (root / 'evil.txt').unlink()
                self.assertTrue(m.publish(root, plan, run)['isDraft'])
                self.assertEqual(set(git('diff', '--name-only', 'main...HEAD').splitlines()), set(paths))
                git('switch', 'main')
                self.assertNotEqual(git('rev-parse', 'HEAD').strip(), git('ls-remote', 'origin', plan['branch']).split()[0])

    def test_zero_input_readonly_and_production_skip_never_fetch_or_write(self):
        l = self.latest()
        import tempfile, json, io
        from contextlib import redirect_stdout
        config = {'title': '启发星球，互相赋能', 'lookback_days': 90,
                  'anchor': {'date': '2026-10-10', 'episode': '40', 'meeting_id': 'series'}}
        test = self
        class Client:
            def call(self, name, args):
                test.assertEqual(name, 'get_user_ended_meetings')
                return {'meeting_info_list': [test.row('2026-10-10')], 'has_more': False}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps(config))
            def run(args):
                if args[:2] == ['git', 'fetch']: return ''
                if args[:3] == ['gh', 'api', '--paginate']: return '[[]]'
                if args[:2] == ['git', 'ls-tree']: return 'events/2026/20261010-ep40/transcript.txt\n'
                if args[:3] == ['git', 'branch', '--show-current']: return 'main\n'
                if args[:2] == ['git', 'rev-parse']: return 'a'*40
                if args[:3] == ['git', 'status', '--porcelain']: return ''
                raise AssertionError(args)
            for command in ('readonly', 'prepare'):
                output = io.StringIO()
                with redirect_stdout(output):
                    l.main([command], root=root, run=run, client_factory=Client,
                           now=datetime(2026, 10, 15, tzinfo=timezone.utc))
                self.assertIn('skip=true', output.getvalue())
                self.assertFalse((root / '.git/latest-transcript.txt').exists())
                self.assertEqual(set(p.name for p in (root / 'scripts').iterdir()), {'meeting-project.json'})

    def test_zero_input_new_pending_download_once_preserves_instance_records(self):
        l = self.latest()
        import tempfile, json
        config = {'title': '启发星球，互相赋能', 'lookback_days': 90,
                  'anchor': {'date': '2026-10-10', 'episode': '40', 'meeting_id': 'series'}}
        record = {'record_file_id': 'file', 'meeting_record_id': 'record', 'type': '转写', 'duration': '01:00'}
        # Gap -> pending, not guessed EP42. Source adapter remains strict.
        row = self.row('2026-10-24', records=[record]); calls = []
        class Client:
            def call(self, name, args):
                calls.append(name)
                if name == 'get_user_ended_meetings': return {'meeting_info_list': [row], 'has_more': False}
                if name == 'get_records_list': return {'record_meetings': [dict(meeting_id='series', sub_meeting_id='2026-10-24', meeting_record_id='record', record_files=[{'record_file_id': 'file'}])], 'has_more': False}
                return {'minutes': {'paragraphs': [{'pid': '0', 'start_time': 0, 'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': '合成全文'}]}]}]}, 'more': False}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps(config))
            def run(args):
                if args[:2] == ['git', 'fetch'] or args[:2] == ['git', 'ls-remote']: return ''
                if args[:3] == ['gh', 'api', '--paginate']: return '[[]]'
                if args[:2] == ['git', 'ls-tree']: return 'events/2026/20261010-ep40/transcript.txt\n'
                if args[:3] == ['git', 'branch', '--show-current']: return 'main\n'
                if args[:2] == ['git', 'rev-parse']: return 'a'*40
                if args[:3] == ['git', 'status', '--porcelain']: return ''
                raise AssertionError(args)
            for command in ('prepare', 'fetch'):
                l.main([command], root=root, run=run, client_factory=Client, now=datetime(2026, 10, 25, tzinfo=timezone.utc))
            with self.assertRaises(m.SafeError): l.main(['fetch'], root=root, run=run, client_factory=Client)
            self.assertEqual(calls.count('get_transcripts_details'), 1)
            self.assertEqual(calls.count('get_user_ended_meetings'), 1)
            l.main(['write'], root=root, run=run, client_factory=Client)
            plan = json.loads((root / '.git/latest-plan.json').read_text())
            self.assertIsNone(plan['episode'])
            metadata = json.loads((root / plan['event'] / 'metadata.json').read_text())
            self.assertEqual(metadata['record_files'], [['record', 'file']])
            self.assertFalse((root / 'events/README.md').exists())
            (root / '.git/latest-transcript.txt').unlink()
            def raced(args):
                if args[:2] == ['git', 'ls-remote']: return 'b'*40 + '\trefs/heads/existing'
                return run(args)
            with self.assertRaises(m.SafeError): l.main(['fetch'], root=root, run=raced, client_factory=Client)
            self.assertEqual(calls.count('get_transcripts_details'), 1)


if __name__ == '__main__': unittest.main()
