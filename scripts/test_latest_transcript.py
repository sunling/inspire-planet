"""Synthetic fixtures; never real Tencent payloads."""
import unittest
from datetime import datetime, timezone
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

    def test_history_date_only_exact_config_filter_and_forced_remote_check(self):
        l = self.latest()
        import tempfile, json
        from unittest.mock import patch
        day = '2025-10-11'
        row = self.row(day, records=[{'record_file_id': 'f', 'meeting_record_id': 'r',
                                    'type': '转写', 'duration': '01:00'}])
        calls = []
        class Client:
            def call(self, name, args):
                calls.append((name, args))
                if name == 'get_user_ended_meetings':
                    return {'meeting_info_list': [dict(row, subject='Other'), row], 'has_more': False}
                if name == 'get_records_list':
                    return {'record_meetings': [dict(meeting_id='series', sub_meeting_id=day,
                        meeting_record_id='r', record_files=[{'record_file_id': 'f'}])], 'has_more': False}
                return {'minutes': {'paragraphs': [{'pid': '0', 'start_time': 0,
                    'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': '合成全文'}]}]}]}, 'more': False}
        with tempfile.TemporaryDirectory(dir='/data/cache/scratch') as tmp:
            root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': row['subject']}))
            existing = root / 'events/2025/20251011-ep48/transcript.txt'
            existing.parent.mkdir(parents=True); existing.write_text('unchanged')
            with patch.object(m, 'event_identity', side_effect=AssertionError('EP must not gate check')):
                l.main(['fetch-check', '--date', day], root=root, client_factory=Client,
                       run=lambda args: self.fail('fetch-check must not need GitHub'))
            self.assertEqual(existing.read_text(), 'unchanged')
            self.assertIn('合成全文', (root / '.git/meeting-content-fetch-check.txt').read_text())
            self.assertEqual([n for n, _ in calls], ['get_user_ended_meetings', 'get_records_list', 'get_transcripts_details'])
            self.assertEqual(calls[0][1]['start_time'], day + 'T00:00:00Z')
            self.assertEqual(calls[0][1]['end_time'], day + 'T23:59:59Z')

    def test_history_mapped_directory_and_unmapped_pending_reuse_pipeline(self):
        l = self.latest()
        import tempfile, json
        from unittest.mock import patch
        day = '2025-10-11'
        row = self.row(day, records=[{'record_file_id': 'f', 'meeting_record_id': 'r',
                                    'type': '转写', 'duration': '01:00'}])
        for mapped in (True, False):
            with self.subTest(mapped=mapped), tempfile.TemporaryDirectory(dir='/data/cache/scratch') as tmp:
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
        with tempfile.TemporaryDirectory(dir='/data/cache/scratch') as tmp:
            root = Path(tmp); (root / '.git').mkdir(); (root / 'scripts').mkdir()
            (root / 'scripts/meeting-project.json').write_text(json.dumps({'title': 'project'}))
            for day in ('', '2025-02-30', '2025-1-1'):
                with self.subTest(day=day), patch.object(l, 'discover', side_effect=AssertionError('must not select latest')):
                    with self.assertRaises(m.SafeError):
                        l.main(['prepare', '--date', day], root=root, run=lambda args: self.fail('invalid date must not run Git/GitHub'),
                               client_factory=lambda: self.fail('invalid date must not read remote'))

    def test_history_ci_uses_date_only_readonly_entry(self):
        workflow = (Path(__file__).parents[1] / '.github/workflows/content-ci.yml').read_text()
        self.assertNotIn('CONTENT_EPISODE', workflow)
        self.assertNotIn('CONTENT_MEETING_ID', workflow)
        self.assertIn('scripts/latest_transcript.py fetch-check --date "$CONTENT_DATE"', workflow)

    def test_history_workflow_date_only_shared_commands(self):
        workflow = (Path(__file__).parents[1] / '.github/workflows/meeting-history.yml').read_text()
        for forbidden in ('episode:', 'inputs.episode', 'CONTENT_EPISODE', 'inputs.subject',
                          'inputs.meeting_id', 'CONTENT_MEETING_SUBJECT', 'CONTENT_MEETING_ID',
                          'scripts/meeting_content.py prepare', 'scripts/meeting_content.py fetch-check',
                          'validate'):
            self.assertNotIn(forbidden, workflow)
        for required in ('default: draft', 'scripts/latest_transcript.py prepare --date',
                         'scripts/latest_transcript.py fetch-check --date',
                         'scripts/latest_transcript.py fetch', 'scripts/latest_transcript.py write',
                         'scripts/latest_transcript.py publish', 'scripts/meeting_content.py connectivity',
                         "if: always()", 'rm -f .git/'):
            self.assertIn(required, workflow)

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
