"""Synthetic fixtures only: these are NOT real meeting outputs."""
import importlib.util
from pathlib import Path
import re
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
    def test_transcript_upstream_retry_is_bounded_and_preserves_request(self):
        import json
        import io
        from contextlib import redirect_stdout
        from unittest.mock import patch
        for statuses, name, expected_calls, success in (
            ([500, 503, 200], 'get_transcripts_details', 3, True),
            ([500, 500, 500], 'get_transcripts_details', 3, False),
            ([403], 'get_transcripts_details', 1, False),
            ([500], 'get_records_list', 1, False),
        ):
            with self.subTest(statuses=statuses, name=name):
                calls = []
                def transport(packet):
                    if packet['method'] == 'tools/list':
                        return {'id': 1, 'result': {'tools': [
                            {'name': n, 'inputSchema': {'type': 'object', 'properties': {k: {'type': t} for k, t in f.items()}}}
                            for n, f in m.TOOL_FIELDS.items()]}}
                    calls.append(packet['params'])
                    status = statuses[len(calls) - 1]
                    body = {'code': 0, 'more': False, 'minutes': {'paragraphs': []}} if status == 200 else 'private-response'
                    return {'id': 1, 'result': {'structuredContent': {
                        'status_code': status, 'body': json.dumps(body)}}}
                client = m.MCP(transport)
                args = {'meeting_id': 'private-meeting', 'record_file_id': 'private-file', 'pid': '101', 'limit': 100} if name == 'get_transcripts_details' else {'meeting_id': 'private-meeting'}
                log = io.StringIO()
                with patch.object(m.time, 'sleep') as sleep, redirect_stdout(log):
                    if success:
                        self.assertFalse(client.call(name, args)['more'])
                    else:
                        with self.assertRaises(m.SafeError) as caught:
                            client.call(name, args)
                        self.assertNotIn('private', str(caught.exception))
                        if expected_calls == 3:
                            self.assertIn('连续 3 次失败', str(caught.exception))
                self.assertEqual(len(calls), expected_calls)
                self.assertTrue(all(call == calls[0] for call in calls))
                self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4] if expected_calls == 3 else [])
                self.assertNotIn('private', log.getvalue())

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
                self.assertIn(args['record_file_id'], {'short', 'long'})
                pid = int(args['pid'])
                spoken = '这是一份更长的合成转写' if args['record_file_id'] == 'short' else '短'
                data = {'code': 0, 'more': pid == 0, 'minutes': {'paragraphs': [{'pid': str(pid), 'start_time': 4400 if pid == 0 else 3723999, 'speaker': {'user_name': '合成甲'}, 'sentences': [{'words': [{'text': spoken}]}]}]}}
                envelope = {'status_code': 200, 'headers': {}, 'body': json.dumps(data)}
            return {'id': 1, 'result': {'content': [{'type': 'text', 'text': json.dumps(envelope)}]}}
        text = m.fetch_transcript(m.MCP(transport), '2026-10-10', 'Synthetic', 'recurring')
        self.assertEqual(text, '合成甲(00:00:04):\n这是一份更长的合成转写\n\n合成甲(01:02:03):\n这是一份更长的合成转写\n')
        read_calls = [a for n, a in calls if n == 'get_transcripts_details']
        self.assertEqual({a['record_file_id'] for a in read_calls}, {'short', 'long'})
        self.assertEqual([a['pid'] for a in read_calls], ['0', '1', '0', '1'])

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

    def test_stale_meeting_summary_uses_only_verified_native_occurrence(self):
        from unittest.mock import patch
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'this-week',
                   'records': [{'record_file_id': 'stale', 'meeting_record_id': 'old'},
                               {'record_file_id': 'shared', 'meeting_record_id': 'group'}]}
        class Client:
            def call(self, name, args):
                self_test.assertEqual(name, 'get_records_list')
                return {'record_meetings': [
                    {'meeting_id': 'series', 'sub_meeting_id': 'this-week',
                     'meeting_record_id': 'group', 'record_files': [
                         {'record_file_id': f} for f in ('shared', 'audio', 'new')]},
                    {'meeting_id': 'series', 'sub_meeting_id': 'last-week',
                     'meeting_record_id': 'other', 'record_files': [{'record_file_id': 'stale'}]}
                ], 'has_more': False}
        self_test = self
        def read(client, meeting_id, file_id):
            self.assertEqual(meeting_id, 'series')
            return {'shared': '合成甲(00:00):\n短。\n', 'audio': None,
                    'new': '合成甲(00:00):\n同一场新生成的完整转写。\n'}[file_id]
        with patch.object(m, 'read_file_transcript', side_effect=read) as reader:
            text = m.fetch_occurrence(Client(), meeting)
        self.assertIn('完整转写', text)
        self.assertEqual({call.args[2] for call in reader.call_args_list}, {'shared', 'audio', 'new'})

    def test_explicit_transcript_artifact_can_differ_from_native_media_id(self):
        from unittest.mock import patch
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'this-week',
                   'records': [{'record_file_id': 'transcript', 'meeting_record_id': 'text', 'type': '转写'}]}
        class Client:
            def call(self, name, args):
                return {'record_meetings': [{'meeting_id': 'series', 'sub_meeting_id': 'this-week',
                    'meeting_record_id': 'media', 'record_files': [{'record_file_id': 'video'}]}], 'has_more': False}
        with patch.object(m, 'read_file_transcript', return_value='合成甲(00:00):\n全文。\n') as read:
            m.fetch_occurrence(Client(), meeting)
        read.assert_called_once_with(unittest.mock.ANY, 'series', 'transcript')

    def test_empty_meeting_records_falls_back_to_same_occurrence_native_files(self):
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                   'start_time': '2026-10-10T00:00:00Z', 'records': []}
        paragraph = {'pid': '0', 'start_time': 1000, 'speaker': {'user_name': '合成甲'},
                     'sentences': [{'words': [{'text': '该场完整转写'}]}]}
        calls = []
        class Client:
            def call(self, name, args):
                calls.append((name, args))
                if name == 'get_records_list':
                    return {'record_meetings': [
                        {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                         'meeting_record_id': 'group1', 'record_files': [{'record_file_id': 'empty'}]},
                        {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                         'meeting_record_id': 'group2', 'record_files': [{'record_file_id': 'full'}]},
                        {'meeting_id': 'series', 'sub_meeting_id': 'different-week',
                         'meeting_record_id': 'other', 'record_files': [{'record_file_id': 'other-week'}]}
                    ], 'has_more': False}
                if name == 'get_transcripts_details':
                    if args['record_file_id'] == 'empty':
                        return {'empty_transcript': True}
                    if args['record_file_id'] == 'full':
                        return {'minutes': {'paragraphs': [paragraph]}, 'more': False}
                raise AssertionError('Must never request a different occurrence')
        result = m.fetch_occurrence(Client(), meeting)
        self.assertIn('该场完整转写', result)
        self.assertEqual({x['record_file_id'] for name, x in calls if name == 'get_transcripts_details'},
                         {'empty', 'full'})

    def test_empty_meeting_records_selects_longest_spoken_transcript(self):
        # Two valid but different transcripts in one occurrence: select the
        # longest spoken content even when it comes from the second recording.
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                   'start_time': '2026-10-10T00:00:00Z', 'records': []}
        calls = []
        class Client:
            def call(self, name, args):
                calls.append(name)
                if name == 'get_records_list':
                    return {'record_meetings': [
                        {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                         'meeting_record_id': 'group',
                         'record_files': [{'record_file_id': 'a-short'},
                                          {'record_file_id': 'z-long'}]},
                        {'meeting_id': 'series', 'sub_meeting_id': 'other-week',
                         'meeting_record_id': 'other',
                         'record_files': [{'record_file_id': 'cross-week'}]}
                    ], 'has_more': False}
                if name == 'get_transcripts_details':
                    if args['record_file_id'] == 'cross-week':
                        raise AssertionError('Must not read another occurrence')
                    content = '短' if args['record_file_id'] == 'a-short' else '这是一份更长更完整的会议文字转写'
                    p = {'pid': '0', 'start_time': 0,
                         'speaker': {'user_name': '合成甲'},
                         'sentences': [{'words': [{'text': content}]}]}
                    return {'minutes': {'paragraphs': [p]}, 'more': False}
                raise AssertionError('Unexpected API')
        result = m.fetch_occurrence(Client(), meeting)
        self.assertIn('这是一份更长更完整的会议文字转写', result)
        self.assertNotIn('短', result)
        self.assertEqual(calls.count('get_transcripts_details'), 2)

    def test_empty_meeting_records_rejects_equal_length_distinct_transcripts(self):
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                   'start_time': '2026-10-10T00:00:00Z', 'records': []}
        class Client:
            def call(self, name, args):
                if name == 'get_records_list':
                    return {'record_meetings': [{
                        'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                        'meeting_record_id': 'group',
                        'record_files': [{'record_file_id': 'first'},
                                         {'record_file_id': 'second'}]
                    }], 'has_more': False}
                if name == 'get_transcripts_details':
                    content = '私密甲' if args['record_file_id'] == 'first' else '私密乙'
                    p = {'pid': '0', 'start_time': 0, 'speaker': {'user_name': '合成甲'},
                         'sentences': [{'words': [{'text': content}]}]}
                    return {'minutes': {'paragraphs': [p]}, 'more': False}
                raise AssertionError('Unexpected API')
        with self.assertRaises(m.SafeError) as caught:
            m.fetch_occurrence(Client(), meeting)
        self.assertIn('最长文字转写出现并列', str(caught.exception))
        self.assertNotIn('私密', str(caught.exception))

    def test_empty_meeting_records_rejects_ambiguous_native_scope(self):
        meeting = {'meeting_id': 'series', 'sub_meeting_id': 'correct-week',
                   'start_time': '2026-10-10T00:00:00Z', 'records': []}
        for case in ('other-week', 'duplicate', 'too-many'):
            with self.subTest(case=case):
                class Client:
                    def call(self, name, args):
                        if name == 'get_records_list':
                            ids = (['a', 'a'] if case == 'duplicate' else
                                   [str(i) for i in range(9)] if case == 'too-many' else ['a'])
                            return {'record_meetings': [{
                                'meeting_id': 'series',
                                'sub_meeting_id': 'different-week' if case == 'other-week' else 'correct-week',
                                'meeting_record_id': 'group',
                                'record_files': [{'record_file_id': i} for i in ids]
                            }], 'has_more': False}
                        raise AssertionError('Must fail before reading any transcript')
                with self.assertRaises(m.SafeError):
                    m.fetch_occurrence(Client(), meeting)

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
            (root / 'events/README.md').write_text(
                '# 合成索引\n\n| 期次与日期 | 转写 | 纪要 | 金句 | 发布文案 | 封面 |\n'
                '|---|---|---|---|---|---|\n'
                '| 20261010-ep40 | — | [纪要](2026/20261010-ep40/recap.md) | — | — | — |\n'
                '\n<details>\n<summary>2025 年归档</summary>\n</details>\n')
            event, _ = m.event_identity('2026-10-17', '41')
            text = '合成甲(00:01):\n合成测试\n'
            paths = m.write_draft(root, event, text)
            self.assertEqual(set(paths), {event + '/transcript.txt', 'events/README.md'})
            self.assertEqual([p.name for p in (root / event).iterdir()], ['transcript.txt'])
            self.assertEqual((root / event / 'transcript.txt').read_text(), text)
            index = (root / 'events/README.md').read_text()
            self.assertIn(event.removeprefix('events/') + '/transcript.txt', index)
            self.assertEqual(index.count('| 期次与日期 |'), 1)
            self.assertLess(index.index('20261017-ep41'), index.index('<details>'))
            self.assertIn('[纪要](2026/20261010-ep40/recap.md)', index)
            self.assertNotIn('summary.json', index)
            with self.assertRaises(m.SafeError):
                m.write_draft(root, event, '合成甲(00:01):\nchanged\n')
            self.assertEqual((root / event / 'transcript.txt').read_text(), text)
            self.assertEqual((root / 'events/README.md').read_text(), index)


    def test_index_insert_is_ordered_and_preserves_archive(self):
        original = (
            '# 合成索引\n\n'
            '| 期次与日期 | 转写 | 纪要 | 金句 | 发布文案 | 封面 |\n'
            '|---|---|---|---|---|---|\n'
            '| 20261010-ep40 | [转写](old.txt) | — | — | — | — |\n'
            '| 20261031-ep43 | — | — | — | — | — |\n\n'
            '手写说明保持不动。\n\n<details>\n<summary>2025 金句</summary>\n'
            '| 20251227-ep50 | [卡片 JSON](somewhere.json) |\n</details>\n'
        )
        result = m.update_transcript_index(original, 'events/2026/20261017-ep41')
        self.assertLess(result.index('20261010-ep40'), result.index('20261017-ep41'))
        self.assertLess(result.index('20261017-ep41'), result.index('20261031-ep43'))
        self.assertEqual(result.count('| 期次与日期 |'), 1)
        self.assertIn('手写说明保持不动。', result)
        self.assertEqual(result.split('手写说明保持不动。', 1)[1], original.split('手写说明保持不动。', 1)[1])

    def test_index_existing_row_preserves_other_columns(self):
        original = (
            '# 合成索引\n\n| 期次与日期 | 转写 | 纪要 | 金句 | 发布文案 | 封面 |\n'
            '|---|---|---|---|---|---|\n'
            '| 20261017-ep41 | — | [纪要](recap.md) | [金句](quotes.json) | — | — |\n'
        )
        result = m.update_transcript_index(original, 'events/2026/20261017-ep41')
        self.assertIn('| [转写](2026/20261017-ep41/transcript.txt) | [纪要](recap.md) |', result)
        self.assertEqual(result.count('20261017-ep41 |'), 1)
        with self.assertRaisesRegex(m.SafeError, '已有索引转写'):
            m.update_transcript_index(result, 'events/2026/20261017-ep41')

    def test_index_rejects_orphan_or_broken_schema_before_writing(self):
        import tempfile
        header = '| 期次与日期 | 转写 | 纪要 | 金句 | 发布文案 | 封面 |\n'
        sep = '|---|---|---|---|---|---|\n'
        for content in (
            '# Missing primary table\n',
            '# Broken primary table\n' + header + '| bad | separator |\n',
            '# Orphan row\n' + header + sep + '\n'
            '<details>\n</details>\n'
            '| 20261017-ep41 | [转写](outside/transcript.txt) | — | — | — | — |\n',
            '# Duplicated row\n' + header + sep +
            '| 20261017-ep41 | — | — | — | — | — |\n' +
            '| 20261017-ep41 | — | — | — | — | — |\n',
        ):
            with self.subTest(case=content[:25]), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'events').mkdir()
                (root / 'events/README.md').write_text(content)
                with self.assertRaises(m.SafeError):
                    m.write_draft(root, 'events/2026/20261017-ep41',
                                  '合成甲(00:01):\n合成测试\n')
                self.assertFalse((root / 'events/2026/20261017-ep41/transcript.txt').exists())
                self.assertEqual((root / 'events/README.md').read_text(), content)


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
        self.assertIn("if: failure() && steps.fetchcheck.outcome == 'failure'", probe)
        self.assertIn('scripts/diagnose_transcript.py --date', probe)
        latest_probe = ci.split('  latest-readonly:', 1)[1].split('  check:', 1)[0]
        self.assertIn("if: github.event_name == 'workflow_dispatch'", latest_probe)
        self.assertIn('ref: ${{ github.sha }}', latest_probe)
        self.assertIn('run: python3 scripts/latest_transcript.py readonly', latest_probe)
        self.assertNotIn('contents: write', latest_probe)
        self.assertNotIn('pull-requests: write', latest_probe)
        self.assertIn("CONTENT_DATE: ${{ inputs.check_date || '2026-10-10' }}", probe)
        self.assertNotIn('CONTENT_EPISODE', probe)
        self.assertIn('run: python3 scripts/latest_transcript.py fetch-check --date "$CONTENT_DATE"', probe)
        self.assertIn('run: test -z "$(git status --porcelain)"', probe)
        self.assertIn('if: always()', probe)
        self.assertIn('rm -f .git/meeting-content-fetch-check.txt', probe)
        self.assertNotIn('CONTENT_PUBLISH_ALLOWED', probe)
        self.assertIn('check-content.py', ci)
        self.assertNotIn("CONTENT_AUTOMATION_ENABLED", flow)
        self.assertIn('name: Transcript download', flow)
        self.assertIn('inputs.date', flow)
        self.assertIn('inputs.timezone', flow)
        self.assertNotIn('CONTENT_EPISODE', flow)
        self.assertNotIn('CONTENT_MEETING_', flow)
        self.assertIn('python3 scripts/latest_transcript.py prepare', flow)
        for stage in ('fetch', 'write', 'publish'):
            self.assertIn('run: python3 scripts/latest_transcript.py ' + stage, flow)
        self.assertFalse((root / '.github/workflows/meeting-history.yml').exists())
        self.assertNotIn('CONTENT_LLM_', flow)
        self.assertNotIn('CONTENT_SOURCE', flow)
        self.assertNotIn('generate', (root / 'scripts/meeting_content.py').read_text())
        self.assertNotIn('cron:', flow)
        self.assertIn('github.event.repository.default_branch', flow)
        self.assertNotIn('pull_request', flow.split('permissions:')[0])
        self.assertIn('persist-credentials: false', flow)
        self.assertIn('cancel-in-progress: false', flow)
        self.assertIn('TENCENT_MEETING_TOKEN: ${{ secrets.TENCENT_MEETING_TOKEN }}', flow)
        self.assertNotIn('run: ${{', flow)
        self.assertNotIn('pull_request_target', flow)
        self.assertNotIn('pull-requests: write', flow)
        self.assertIn('pull-requests: read', flow)
        self.assertIn('CONTENT_MAIN_WRITE_ALLOWED', flow)
        self.assertNotIn('pull-requests: write', flow)
        self.assertIn('CONTENT_MAIN_WRITE_ALLOWED', flow)

    def test_download_is_manual_only(self):
        root = Path(__file__).resolve().parents[1]
        flow = (root / '.github/workflows/meeting-content.yml').read_text()
        self.assertIn('workflow_dispatch:', flow)
        self.assertNotIn('schedule:', flow)
        self.assertIn("github.event_name == 'workflow_dispatch'", flow)


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
            (root / 'events/README.md').write_text(
                '# 合成索引\n\n| 期次与日期 | 转写 | 纪要 | 金句 | 发布文案 | 封面 |\n'
                '|---|---|---|---|---|---|\n'
                '| 20261010-ep40 | — | — | — | — | — |\n')
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
            for filename in ('check-content.py', 'validate_publication.py'):
                shutil.copy(Path(__file__).with_name(filename), root / 'scripts' / filename)
            checked = subprocess.run(['python3', 'scripts/check-content.py'], cwd=root, capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn('Content check passed: 1 episodes', checked.stdout)
            # The validator imports a helper, which may also create __pycache__.
            shutil.rmtree(root / 'scripts')
            result = m.publish(root, plan, run)
            self.assertTrue(result['isDraft'])
            self.assertEqual(len(created), 1)
            self.assertEqual(set(git(['diff', '--name-only', 'main...HEAD']).splitlines()), {event + '/transcript.txt', 'events/README.md'})
            self.assertEqual(git(['rev-parse', 'HEAD']).strip(), git(['ls-remote', '--heads', 'origin', 'refs/heads/' + branch]).split()[0])
            git(['switch', 'main'])
            self.assertTrue(m.prepare(root, '2026-10-17', '41', 'main', run)['skip'])


if __name__ == '__main__':
    unittest.main()
