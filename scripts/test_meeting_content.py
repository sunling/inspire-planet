"""Synthetic fixtures only: these are NOT real meeting outputs."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('meeting_content', Path(__file__).with_name('meeting_content.py'))
m = importlib.util.module_from_spec(spec)
if spec.loader and spec.origin and Path(spec.origin).exists():
    spec.loader.exec_module(m)


class IdentityTests(unittest.TestCase):
    def test_explicit_identity_and_mixed_timestamps(self):
        self.assertEqual(m.event_identity('2026-10-17', '41'), ('events/2026/20261017-ep41', 'content/20261017-ep41'))
        self.assertEqual(m.utc_day('2026-10-16T17:00:00-07:00'), '2026-10-17')
        self.assertEqual(m.norm_time('12:34'), '00:12:34')
        self.assertEqual(m.norm_time('1:02:03'), '01:02:03')
        for date, ep in [('2026-02-30', '1'), ('2026-10-17', '../41'), ('2026-10-17', '0')]:
            with self.assertRaises(m.SafeError):
                m.event_identity(date, ep)
        with self.assertRaises(m.SafeError):
            m.norm_time('broken')


class TranscriptTests(unittest.TestCase):
    def test_observed_http_body_envelopes_decode_and_check_inner_business_code(self):
        # Sanitized structure from live runs 38784249250 / 38784551270;
        # all values below are synthetic, never copied meeting content.
        import json
        for wrapped in (True, False):
            for code in (0, 30002, 999):
                with self.subTest(wrapped=wrapped, code=code):
                    def transport(packet):
                        if packet['method'] == 'tools/list':
                            return {'id': 1, 'result': {'tools': [
                                {'name': n, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in f.items()}}}
                                for n, f in m.TOOL_FIELDS.items()]}}
                        body = {'code': code, 'more': False, 'minutes': {'paragraphs': []}}
                        data = {'status_code': 200, 'headers': {}, 'body': json.dumps(body)}
                        return {'id': 1, 'result': {'content': [{'type': 'text', 'text': json.dumps({'_meta': {}, 'data': data} if wrapped else data)}]}}
                    client = m.MCP(transport)
                    args = {'meeting_id': 'synthetic', 'record_file_id': 'synthetic', 'pid': '0', 'limit': 100}
                    if code == 999:
                        with self.assertRaises(m.SafeError): client.call('get_transcripts_details', args)
                    else:
                        actual = client.call('get_transcripts_details', args)
                        self.assertEqual(actual, {'empty_transcript': True} if code == 30002 else {'code': 0, 'more': False, 'minutes': {'paragraphs': []}})

    def test_http_body_envelopes_fail_closed_without_leaking_payload(self):
        import json
        for data in (
            {'status_code': 403, 'body': 'private-server-error'},
            {'status_code': 200, 'body': 'private-not-json'},
            {'status_code': 200, 'body': '[]'},
            {'status_code': 200, 'body': {'code': 0}},
            {'data': {'data': {'data': {'data': {'data': {'data': {'code': 999}}}}}}},
        ):
            with self.subTest(shape=type(data).__name__):
                def transport(packet):
                    if packet['method'] == 'tools/list':
                        return {'id': 1, 'result': {'tools': [
                            {'name': n, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in f.items()}}}
                            for n, f in m.TOOL_FIELDS.items()]}}
                    return {'id': 1, 'result': {'content': [{'type': 'text', 'text': json.dumps(data)}]}}
                with self.assertRaises(m.SafeError) as caught:
                    m.MCP(transport).call('get_transcripts_details', {'meeting_id': 'synthetic', 'record_file_id': 'synthetic', 'pid': '0', 'limit': 100})
                self.assertNotIn('private', str(caught.exception))

    def test_full_mode_is_requested_and_required_by_live_schema(self):
        calls = []
        def transport(packet):
            if packet['method'] == 'tools/list':
                tools = [{'name': n, 'inputSchema': {'type': 'object', 'properties': dict({k: {'type': t} for k, t in f.items()}, is_compact={'type': 'boolean'})}} for n, f in m.TOOL_FIELDS.items()]
                return {'id': 1, 'result': {'tools': tools}}
            calls.append(packet['params']['arguments'])
            return {'id': 1, 'result': {'structuredContent': {'meeting_info_list': [], 'has_more': False}}}
        client = m.MCP(transport)
        client.call('get_user_ended_meetings', {'start_time': 'synthetic', 'end_time': 'synthetic', 'page_size': 100, 'page_token': ''})
        self.assertIs(calls[0].get('is_compact'), False)
        with self.assertRaises(m.SafeError):
            client.call('get_user_ended_meetings', {'is_compact': True})

    def test_observed_occurrence_records_full_transcript_pages_and_millisecond_times(self):
        import json
        calls = []
        records = [{'record_file_id': 'short', 'meeting_record_id': 'short-group', 'type': '转写', 'duration': '00:01'},
                   {'record_file_id': 'long', 'meeting_record_id': 'long-group', 'type': '转写', 'duration': '01:02:03'}]
        def transport(packet):
            if packet['method'] == 'tools/list':
                return {'id': 1, 'result': {'tools': [
                    {'name': n, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in f.items()}}}
                    for n, f in m.TOOL_FIELDS.items()]}}
            name, args = packet['params']['name'], packet['params']['arguments']
            calls.append((name, args))
            self.assertIs(args['is_compact'], False)
            if name == 'get_user_ended_meetings':
                data = {'has_more': False, 'meeting_info_list': [{'meeting_id': 'recurring', 'sub_meeting_id': 'occurrence', 'subject': 'Synthetic', 'start_time': '2026-10-10T00:00:00Z', 'records': records, 'records_total_count': 115}]}
                envelope = {'_meta': {}, 'data': {'status_code': 200, 'headers': {}, 'body': json.dumps(data)}}
            elif name == 'get_records_list':
                groups = [{'meeting_id': 'recurring', 'sub_meeting_id': 'occurrence', 'meeting_record_id': r['meeting_record_id'], 'record_files': [{'record_file_id': r['record_file_id']}]} for r in records]
                groups.append({'meeting_id': 'recurring', 'sub_meeting_id': 'other-week', 'meeting_record_id': 'unrelated', 'record_files': [{'record_file_id': 'unrelated'}]})
                first = not args['page_token']
                data = {'record_meetings': groups[:1] if first else groups[1:], 'has_more': first, 'next_page_token': 'synthetic-next' if first else '', 'total_count': 3}
                envelope = {'data': {'status_code': 200, 'body': json.dumps(data)}}
            else:
                self.assertEqual(name, 'get_transcripts_details')
                self.assertEqual(args['record_file_id'], 'long')
                pid = int(args['pid'])
                data = {'code': 0, 'more': pid == 0, 'minutes': {'paragraphs': [{'pid': str(pid), 'start_time': 4400 if pid == 0 else 3723999, 'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': '合成文本'}]}]}]}}
                envelope = {'status_code': 200, 'headers': {}, 'body': json.dumps(data)}
            return {'id': 1, 'result': {'content': [{'type': 'text', 'text': json.dumps(envelope)}]}}
        text = m.fetch_transcript(m.MCP(transport), '2026-10-10', 'Synthetic', 'recurring')
        self.assertEqual(text, '合成甲(00:00:04):\n合成文本\n\n合成甲(01:02:03):\n合成文本\n')
        self.assertEqual([a['pid'] for n, a in calls if n == 'get_transcripts_details'], ['0', '1'])

    def test_occurrence_coverage_and_transcript_paging_fail_closed(self):
        from unittest.mock import patch
        record = {'record_file_id': 'file', 'meeting_record_id': 'group', 'type': '转写', 'duration': '01:00'}
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'occurrence', 'start_time': '2026-10-10T00:00:00Z', 'records': [record]}
        group = {'meeting_id': 'series', 'sub_meeting_id': 'occurrence', 'meeting_record_id': 'group', 'record_files': [{'record_file_id': 'file'}]}
        paragraph = {'pid': '0', 'start_time': 0, 'speaker': {'user_name': '合成'}, 'sentences': [{'words': [{'text': '合成'}]}]}
        for case in ('missing_sub', 'missing_metadata', 'duplicate_file', 'missing_more', 'empty_more', 'duplicate_pid', 'midstream_empty', 'page_bound'):
            with self.subTest(case=case):
                class Client:
                    def __init__(self): self.pages = 0
                    def call(self, name, args):
                        if name == 'get_user_ended_meetings':
                            row = dict(meeting)
                            if case == 'missing_sub': row.pop('sub_meeting_id')
                            if case == 'missing_metadata': row['records'] = []
                            return {'meeting_info_list': [row], 'has_more': False}
                        if name == 'get_records_list':
                            return {'record_meetings': [group, group] if case == 'duplicate_file' else [group], 'has_more': False}
                        self.pages += 1
                        if case == 'midstream_empty' and self.pages > 1: return {'empty_transcript': True}
                        if case == 'missing_more': return {'minutes': {'paragraphs': [paragraph]}}
                        if case == 'empty_more': return {'minutes': {'paragraphs': []}, 'more': True}
                        row = dict(paragraph, pid=str(self.pages - 1)) if case == 'page_bound' else paragraph
                        return {'minutes': {'paragraphs': [row]}, 'more': True}
                with patch.object(m, 'MAX_PAGES', 2), self.assertRaises(m.SafeError):
                    m.fetch_transcript(Client(), '2026-10-10', '', 'series')
        for value in (-1, True, 4.5):
            with self.assertRaises(m.SafeError): m.norm_time(value)

    def test_runtime_schema_changes_fail_before_any_tool_call(self):
        import copy
        tools = [{'name': name, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in fields.items()}, 'required': list(fields)}} for name, fields in m.TOOL_FIELDS.items()]
        for change in ('missing_tool', 'wrong_type', 'new_required'):
            with self.subTest(change=change):
                changed = copy.deepcopy(tools)
                if change == 'missing_tool': changed.pop()
                elif change == 'wrong_type': changed[0]['inputSchema']['properties']['start_time']['type'] = 'integer'
                else: changed[0]['inputSchema']['required'].append('unexpected')
                def transport(packet):
                    self.assertEqual(packet['method'], 'tools/list')
                    return {'jsonrpc': '2.0', 'id': 1, 'result': {'tools': changed}}
                with self.assertRaises(m.SafeError):
                    m.MCP(transport)

    def test_read_only_runtime_schema_full_pagination_and_empty_fallback(self):
        calls = []
        def transport(payload):
            calls.append(payload)
            if payload['method'] == 'tools/list':
                return {'jsonrpc': '2.0', 'id': 1, 'result': {'tools': [
                    {'name': name, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in fields.items()}, 'required': list(fields)}}
                    for name, fields in m.TOOL_FIELDS.items()]}}
            name, args = payload['params']['name'], payload['params']['arguments']
            if name == 'get_user_ended_meetings':
                data = {'meeting_info_list': [{'meeting_id': 'synthetic-id', 'sub_meeting_id': 'occurrence', 'subject': 'Synthetic Planet', 'start_time': '2026-10-16T17:00:00-07:00', 'records': [{'record_file_id': 'empty', 'meeting_record_id': 'empty-group', 'type': '转写', 'duration': '02:00:00'}, {'record_file_id': 'full', 'meeting_record_id': 'full-group', 'type': '转写', 'duration': '01:00:00'}]}], 'has_more': False}
            elif name == 'get_records_list':
                data = {'record_meetings': [{'meeting_id': 'synthetic-id', 'sub_meeting_id': 'occurrence', 'meeting_record_id': f + '-group', 'record_files': [{'record_file_id': f}]} for f in ('empty', 'full')], 'has_more': False}
            elif args['record_file_id'] == 'empty':
                data = {'code': 30002}  # documented empty-shell recording, not transport failure
            else:
                pid = int(args['pid'])
                data = {'minutes': {'paragraphs': [{'pid': str(pid), 'start_time': '12:34' if pid == 0 else '1:02:03', 'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': '合成文本，不是真实会议。'}]}]}]}, 'more': pid == 0}
            return {'jsonrpc': '2.0', 'id': 1, 'result': {'content': [{'type': 'text', 'text': __import__('json').dumps({'data': data})}]}}
        client = m.MCP(transport)
        text = m.fetch_transcript(client, '2026-10-17', 'Synthetic Planet', '')
        self.assertIn('合成甲(00:12:34):', text)
        self.assertIn('合成甲(01:02:03):', text)
        self.assertEqual(len([c for c in calls if c['method'] == 'tools/call' and c['params']['name'] == 'get_transcripts_details']), 3)
        with self.assertRaises(m.SafeError):
            client.call('cancel_meeting', {})

    def test_fail_closed_for_ambiguity_missing_filter_and_stalled_page(self):
        with self.assertRaises(m.SafeError):
            m.select_meeting([], '2026-10-17', '', '')
        row = {'meeting_id': 'synthetic', 'subject': 'Synthetic Planet', 'start_time': '2026-10-17T00:00:00Z'}
        with self.assertRaises(m.SafeError):
            m.select_meeting([row, dict(row, meeting_id='second')], '2026-10-17', 'Synthetic Planet', '')
        class Stalled:
            def call(self, name, args):
                return {'rows': [], 'has_more': True, 'next_page_token': ''}
        with self.assertRaises(m.SafeError):
            m.token_pages(Stalled(), 'get_records_list', {}, 'rows')


class DraftTests(unittest.TestCase):
    def test_any_prior_pr_skips_even_when_remote_branch_was_deleted(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmp:
            for state in ('OPEN', 'CLOSED', 'MERGED'):
                with self.subTest(state=state):
                    def run(args):
                        if args[:3] == ['git', 'branch', '--show-current']: return 'main\n'
                        if args[:3] == ['git', 'status', '--porcelain']: return ''
                        if args[:2] == ['git', 'ls-remote']: return ''
                        if args[:3] == ['gh', 'pr', 'list']:
                            self.assertIn('all', args)
                            return json.dumps([{'number': 1, 'state': state, 'isDraft': state == 'OPEN'}])
                        raise AssertionError(args)
                    self.assertTrue(m.prepare(Path(tmp), '2026-10-17', '41', 'main', run)['skip'])

    def test_prepare_idempotency_uses_transcript_not_generated_content(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event, _ = m.event_identity('2026-10-17', '41')
            target = root / event; target.mkdir(parents=True)
            def run(args):
                if args[:3] == ['git', 'branch', '--show-current']: return 'main\n'
                if args[:3] == ['git', 'status', '--porcelain']: return ''
                if args[:2] == ['git', 'ls-remote']: return ''
                if args[:3] == ['gh', 'pr', 'list']: return '[]'
                if args[:3] == ['git', 'rev-parse', 'HEAD']: return 'synthetic-head\n'
                raise AssertionError(args)
            for name in ('summary.json', 'quote-cards.json', 'README.md'):
                (target / name).write_text('synthetic existing editorial content')
            self.assertFalse(m.prepare(root, '2026-10-17', '41', 'main', run)['skip'])
            (target / 'transcript.txt').write_text('synthetic existing transcript')
            self.assertTrue(m.prepare(root, '2026-10-17', '41', 'main', run)['skip'])

    def test_remote_branch_skips_before_fetch(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = []
            def run(args):
                commands.append(args)
                if args[:3] == ['git', 'branch', '--show-current']: return 'main\n'
                if args[:3] == ['git', 'status', '--porcelain']: return ''
                if args[:2] == ['git', 'ls-remote']: return 'abc\trefs/heads/content/20261017-ep41\n'
                if args[:3] == ['gh', 'pr', 'list']: return '[]'
                raise AssertionError(args)
            plan = m.prepare(root, '2026-10-17', '41', 'main', run)
            self.assertTrue(plan['skip'])
            self.assertTrue(any(c[:2] == ['git', 'ls-remote'] for c in commands))
            with self.assertRaises(m.SafeError):
                m.prepare(root, '2026-10-17', '41', 'other-base', run)

    def test_only_transcript_and_index_written_no_overwrite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'events').mkdir()
            (root / 'events/README.md').write_text('# 合成索引\n')
            event, _ = m.event_identity('2026-10-17', '41')
            text = '合成甲(00:01):\n合成测试\n'
            paths = m.write_draft(root, event, text)
            self.assertEqual(set(paths), {event + '/transcript.txt', 'events/README.md'})
            self.assertEqual([p.name for p in (root / event).iterdir()], ['transcript.txt'])
            self.assertEqual((root / event / 'transcript.txt').read_text(), text)
            index = (root / 'events/README.md').read_text()
            self.assertIn(event.removeprefix('events/') + '/transcript.txt', index)
            self.assertNotIn('summary.json', index)
            with self.assertRaises(m.SafeError):
                m.write_draft(root, event, '合成甲(00:01):\nchanged\n')
            self.assertEqual((root / event / 'transcript.txt').read_text(), text)
            self.assertEqual((root / 'events/README.md').read_text(), index)


class RuntimeTests(unittest.TestCase):
    def test_http_is_https_bounded_and_sanitizes_server_errors(self):
        import urllib.error
        for url in ['http://example.com/v1', 'https://user:secret@example.com/v1', 'https://example.com/v1?key=secret']:
            with self.assertRaises(m.SafeError):
                m.https_url(url)
        class Broken:
            def open(self, req, timeout):
                raise urllib.error.HTTPError(req.full_url, 401, 'secret-token-should-never-appear', {}, None)
        with self.assertRaises(m.SafeError) as caught:
            m.send_json('https://example.com/v1', {}, {'Authorization': 'secret-token-should-never-appear'}, opener=Broken())
        self.assertNotIn('secret-token', str(caught.exception))

    def test_publish_rejects_unscoped_files_before_any_push(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = []
            def run(args):
                calls.append(args)
                if args[:3] == ['git', 'branch', '--show-current']: return 'main\n'
                if args[:3] == ['git', 'rev-parse', 'HEAD']: return 'synthetic-head\n'
                if args[:3] == ['git', 'diff', '--name-only']: return 'scripts/evil.py\n'
                if args[:3] == ['git', 'ls-files', '--others']: return ''
                raise AssertionError(args)
            plan = {'base': 'main', 'head': 'synthetic-head', 'event': 'events/2026/20261017-ep41', 'branch': 'content/20261017-ep41', 'episode': '41', 'date': '2026-10-17'}
            with self.assertRaises(m.SafeError):
                m.publish(root, plan, run)
            self.assertFalse(any(c[:2] == ['git', 'push'] for c in calls))


class CLITests(unittest.TestCase):
    def test_prepare_invalidates_previous_draft_cache(self):
        import tempfile
        import os
        import subprocess
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir()
            cache = root / '.git/meeting-content-transcript.txt'
            cache.write_text('previous synthetic event')
            def synthetic_run(args, **kwargs):
                if args[:3] == ['git', 'branch', '--show-current']: text = 'main\n'
                elif args[:3] == ['git', 'status', '--porcelain']: text = ''
                elif args[:2] == ['git', 'ls-remote']: text = ''
                elif args[:3] == ['gh', 'pr', 'list']: text = '[]'
                elif args[:3] == ['git', 'rev-parse', 'HEAD']: text = 'synthetic-head\n'
                else: raise AssertionError(args)
                return subprocess.CompletedProcess(args, 0, stdout=text, stderr='')
            env = {'CONTENT_DATE': '2026-10-17', 'CONTENT_EPISODE': '41', 'CONTENT_BASE_BRANCH': 'main', 'CONTENT_MEETING_ID': 'synthetic-id'}
            with patch.dict(os.environ, env, clear=True), patch('subprocess.run', side_effect=synthetic_run):
                m.main(['prepare'], root=root)
            self.assertFalse(cache.exists())
            with patch.dict(os.environ, env, clear=True), patch('subprocess.run', side_effect=synthetic_run):
                with self.assertRaisesRegex(m.SafeError, 'fetch'):
                    m.main(['write'], root=root)

    def test_synthetic_fetch_check_forces_remote_even_with_existing_transcript(self):
        import tempfile
        import os
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.git').mkdir()
            event, _ = m.event_identity('2026-10-17', '41')
            target = root / event; target.mkdir(parents=True)
            local = target / 'transcript.txt'; local.write_text('已有原稿，不得替换')
            calls = []
            def synthetic_transport(url, packet, headers):
                self.assertEqual(url, m.MCP_URL)
                calls.append(packet)
                if packet['method'] == 'tools/list':
                    result = {'tools': [{'name': name, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in fields.items()}, 'required': list(fields)}} for name, fields in m.TOOL_FIELDS.items()]}
                else:
                    name = packet['params']['name']
                    data = {
                        'get_user_ended_meetings': {'meeting_info_list': [{'meeting_id': 'synthetic-id', 'sub_meeting_id': 'occurrence', 'subject': 'Synthetic Planet', 'start_time': '2026-10-17T00:00:00Z', 'records': [{'record_file_id': 'synthetic-file', 'meeting_record_id': 'group', 'type': '转写', 'duration': '01:00:00'}]}], 'has_more': False},
                        'get_records_list': {'record_meetings': [{'meeting_id': 'synthetic-id', 'sub_meeting_id': 'occurrence', 'meeting_record_id': 'group', 'record_files': [{'record_file_id': 'synthetic-file'}]}], 'has_more': False},
                        'get_transcripts_details': {'minutes': {'paragraphs': [{'pid': '0', 'start_time': '00:01', 'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': '仅合成远程正文'}]}]}]}, 'more': False},
                    }[name]
                    result = {'structuredContent': {'data': data}}
                return {'jsonrpc': '2.0', 'id': 1, 'result': result}
            env = {'CONTENT_DATE': '2026-10-17', 'CONTENT_EPISODE': '41', 'CONTENT_MEETING_SUBJECT': 'Synthetic Planet', 'TENCENT_MEETING_TOKEN': 'synthetic-not-real'}
            output = io.StringIO()
            with patch.dict(os.environ, env, clear=True), patch.object(m, 'send_json', side_effect=synthetic_transport), redirect_stdout(output):
                m.main(['fetch-check'], root=root)
            self.assertEqual(local.read_text(), '已有原稿，不得替换')
            self.assertEqual([p.name for p in target.iterdir()], ['transcript.txt'])
            self.assertEqual({p['params']['name'] for p in calls if p['method'] == 'tools/call'}, set(m.TOOL_FIELDS))
            self.assertIn('1 段', output.getvalue())
            self.assertNotIn('仅合成远程正文', output.getvalue())
            self.assertNotIn('合成甲', output.getvalue())
            self.assertEqual((root / '.git/meeting-content-fetch-check.txt').read_text(), '合成甲(00:00:01):\n仅合成远程正文\n')
            self.assertFalse((root / '.git/meeting-content-transcript.txt').exists())

    def test_local_validate_executes_without_credentials_or_writes(self):
        import tempfile
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event, _ = m.event_identity('2026-10-17', '41')
            target = root / event; target.mkdir(parents=True)
            (target / 'transcript.txt').write_text('合成甲(00:01):\n合成验证文本。\n')
            env = {'CONTENT_DATE': '2026-10-17', 'CONTENT_EPISODE': '41'}
            with patch.dict(os.environ, env, clear=True):
                m.main(['validate'], root=root)
            self.assertEqual([p.name for p in target.iterdir()], ['transcript.txt'])
            with patch.dict(os.environ, dict(env, CONTENT_DATE='bad'), clear=True):
                with self.assertRaises(m.SafeError):
                    m.main(['validate'], root=root)


class WorkflowTests(unittest.TestCase):
    def test_workflows_are_secretless_ci_and_gated_default_branch_automation(self):
        root = Path(__file__).parents[1]
        ci = (root / '.github/workflows/content-ci.yml').read_text()
        flow = (root / '.github/workflows/meeting-content.yml').read_text()
        self.assertIn('pull_request:', ci)
        self.assertIn('push:', ci)
        check = ci.split('  check:', 1)[1]
        self.assertNotIn('secrets.', check)
        probe = ci.split('  ep40-readonly:', 1)[1].split('  check:', 1)[0]
        self.assertIn("if: github.event_name == 'workflow_dispatch'", probe)
        self.assertIn('ref: ${{ github.sha }}', probe)
        self.assertIn('contents: read', probe)
        self.assertNotIn('write', probe)
        self.assertNotIn('upload-artifact', ci)
        self.assertEqual(ci.count('secrets.'), 4)
        latest_probe = ci.split('  latest-readonly:', 1)[1].split('  check:', 1)[0]
        self.assertIn("if: github.event_name == 'workflow_dispatch'", latest_probe)
        self.assertIn('ref: ${{ github.sha }}', latest_probe)
        self.assertIn('run: python3 scripts/latest_transcript.py readonly', latest_probe)
        self.assertNotIn('contents: write', latest_probe)
        self.assertNotIn('pull-requests: write', latest_probe)
        self.assertIn('CONTENT_DATE: \'2026-10-10\'', probe)
        self.assertNotIn('CONTENT_EPISODE', probe)
        self.assertIn('run: python3 scripts/latest_transcript.py fetch-check --date "$CONTENT_DATE"', probe)
        self.assertIn('run: test -z "$(git status --porcelain)"', probe)
        self.assertIn('if: always()', probe)
        self.assertIn('rm -f .git/meeting-content-fetch-check.txt', probe)
        self.assertNotIn('CONTENT_PUBLISH_ALLOWED', probe)
        self.assertIn('check-content.py', ci)
        self.assertIn("vars.CONTENT_AUTOMATION_ENABLED == 'true'", flow)
        self.assertIn('name: Transcript draft', flow)
        self.assertNotIn('inputs:', flow)
        self.assertNotIn('CONTENT_DATE', flow)
        self.assertNotIn('CONTENT_EPISODE', flow)
        self.assertNotIn('CONTENT_MEETING_', flow)
        for stage in ('prepare', 'fetch', 'write', 'publish'):
            self.assertIn('run: python3 scripts/latest_transcript.py ' + stage, flow)
        history = (root / '.github/workflows/meeting-history.yml').read_text()
        self.assertIn('options: [draft, fetch-check, connectivity]', history)
        self.assertNotIn('schedule:', history)
        self.assertIn('run: python3 scripts/latest_transcript.py fetch-check --episode "$CONTENT_EPISODE" --year "$CONTENT_YEAR" --date "$CONTENT_DATE"', history)
        self.assertIn('run: python3 scripts/latest_transcript.py scan', history)
        self.assertIn('run: python3 scripts/latest_transcript.py write', history)
        self.assertNotIn('CONTENT_LLM_', flow)
        self.assertNotIn('CONTENT_SOURCE', flow)
        self.assertNotIn('generate', (root / 'scripts/meeting_content.py').read_text())
        self.assertEqual(flow.count('cron:'), 1)
        self.assertIn('github.event.repository.default_branch', flow)
        self.assertNotIn('pull_request', flow.split('permissions:')[0])
        self.assertIn('persist-credentials: false', flow)
        self.assertIn('cancel-in-progress: false', flow)
        self.assertIn('TENCENT_MEETING_TOKEN: ${{ secrets.TENCENT_MEETING_TOKEN }}', flow)
        self.assertNotIn('run: ${{', flow)
        self.assertNotIn('pull_request_target', flow)


class EndToEndTests(unittest.TestCase):
    def test_synthetic_transcript_draft_real_local_git_stubbed_github(self):
        import tempfile
        import subprocess
        import json
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); root = parent / 'repo'; root.mkdir()
            remote = parent / 'remote.git'
            def git(args, cwd=root):
                return subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=True, check=True).stdout
            git(['init', '--bare', str(remote)])
            git(['init', '-b', 'main'])
            git(['config', 'user.email', 'synthetic@example.invalid']); git(['config', 'user.name', 'Synthetic Test'])
            git(['remote', 'add', 'origin', str(remote)])
            event, branch = m.event_identity('2026-10-17', '41')
            (root / 'events').mkdir()
            text = '合成甲(00:01):\n我开始记录。这是合成测试。\n'
            (root / 'events/README.md').write_text('# 合成索引\n')
            git(['add', '.']); git(['commit', '-m', 'synthetic baseline'])
            git(['push', 'origin', 'main'])
            created = []
            def run(args):
                if args[0] == 'git': return git(args[1:])
                if args[:3] == ['gh', 'pr', 'list']: return '[]'
                if args[:3] == ['gh', 'pr', 'create']:
                    self.assertIn('--draft', args)
                    body = args[args.index('--body') + 1]
                    self.assertIn('仅逐字稿', body)
                    self.assertIn('没有生成', body)
                    created.append(args)
                    return 'synthetic-pr'
                if args[:3] == ['gh', 'pr', 'view']:
                    return json.dumps({'state': 'OPEN', 'isDraft': True, 'headRefName': branch, 'baseRefName': 'main', 'files': [{'path': p} for p in m.allowed_paths(event)]})
                raise AssertionError(args)
            plan = m.prepare(root, '2026-10-17', '41', 'main', run)
            self.assertFalse(plan['skip'])
            import os
            from unittest.mock import patch
            (root / '.git/meeting-content-plan.json').write_text(json.dumps(plan))
            (root / '.git/meeting-content-transcript.txt').write_text(text)
            with patch.dict(os.environ, {'CONTENT_DATE': '2026-10-17', 'CONTENT_EPISODE': '41'}, clear=True):
                m.main(['write'], root=root)
            (root / 'scripts').mkdir()
            shutil.copy(Path(__file__).with_name('check-content.py'), root / 'scripts/check-content.py')
            checked = subprocess.run(['python3', 'scripts/check-content.py'], cwd=root, capture_output=True, text=True, check=True)
            self.assertIn('Content check passed: 1 episodes', checked.stdout)
            (root / 'scripts/check-content.py').unlink(); (root / 'scripts').rmdir()
            result = m.publish(root, plan, run)
            self.assertTrue(result['isDraft'])
            self.assertEqual(len(created), 1)
            self.assertEqual(set(git(['diff', '--name-only', 'main...HEAD']).splitlines()), {event + '/transcript.txt', 'events/README.md'})
            self.assertEqual(git(['rev-parse', 'HEAD']).strip(), git(['ls-remote', '--heads', 'origin', 'refs/heads/' + branch]).split()[0])
            git(['switch', 'main'])
            self.assertTrue(m.prepare(root, '2026-10-17', '41', 'main', run)['skip'])


if __name__ == '__main__':
    unittest.main()
