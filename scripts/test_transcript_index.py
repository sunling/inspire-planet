"""Synthetic index fixtures only; no real meeting data or network."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import meeting_content as m


class IndexTests(unittest.TestCase):
    def client(self, index, include=True, compatible=True):
        calls = []
        def transport(packet):
            if packet['method'] == 'tools/list':
                fields = dict(m.TOOL_FIELDS)
                if include:
                    fields.update(m.OPTIONAL_TOOL_FIELDS)
                tools = [{'name': n, 'inputSchema': {'type': 'object',
                          'properties': {k: {'type': t} for k, t in f.items()}}}
                         for n, f in fields.items()]
                if include and not compatible:
                    tools[-1]['inputSchema']['required'] = ['unsupported']
                return {'id': 1, 'result': {'tools': tools}}
            name = packet['params']['name']
            calls.append(packet['params'])
            if name == 'get_transcripts_paragraphs':
                if isinstance(index, Exception):
                    raise index
                return {'id': 1, 'result': {'structuredContent': index}}
            return {'id': 1, 'result': {'structuredContent': {
                'status_code': 500, 'body': 'private-response'}}}
        return m.MCP(transport), calls

    def test_first_page_500_can_be_empty_only_with_explicit_completed_zero_index(self):
        client, calls = self.client({'total': 0, 'pids': [], 'audio_detect': 1})
        out = io.StringIO()
        with patch.object(m.time, 'sleep'), redirect_stdout(out):
            self.assertIsNone(m.read_file_transcript(client, 'private-meeting', 'private-file'))
        self.assertEqual([c['name'] for c in calls], ['get_transcripts_details'] * 3 + ['get_transcripts_paragraphs'])
        self.assertIn('confirmed_empty', out.getvalue())
        self.assertNotIn('private', out.getvalue())
        self.assertTrue(all(c['arguments']['is_compact'] is False for c in calls))

    def test_nonempty_missing_incomplete_or_failed_index_cannot_hide_500(self):
        for index in (
            {'total': 10, 'pids': [], 'audio_detect': 1},
            {'total': 0, 'audio_detect': 1},
            {'total': 0, 'pids': [], 'audio_detect': 0},
            {'total': False, 'pids': [], 'audio_detect': 1},
            {'total': 0, 'pids': [], 'audio_detect': 1, 'more': True},
            {'total': 0, 'pids': [{'pid': '0'}], 'audio_detect': 1},
            m.SafeError('private-error'),
        ):
            with self.subTest(index=index):
                client, _ = self.client(index)
                with patch.object(m.time, 'sleep'), redirect_stdout(io.StringIO()):
                    with self.assertRaises(m.UpstreamHTTPError):
                        m.read_file_transcript(client, 'meeting', 'file')

    def test_missing_or_incompatible_optional_tool_preserves_original_failure(self):
        for include, compatible in ((False, True), (True, False)):
            client, calls = self.client({}, include, compatible)
            self.assertFalse(client.supports('get_transcripts_paragraphs'))
            with patch.object(m.time, 'sleep'), redirect_stdout(io.StringIO()):
                with self.assertRaises(m.UpstreamHTTPError):
                    m.read_file_transcript(client, 'meeting', 'file')
            self.assertEqual(len(calls), 3)

    def test_mid_pagination_failure_never_uses_empty_index(self):
        class Client:
            def supports(self, name):
                raise AssertionError('must not probe an index after a partial read')
            def call(self, name, args):
                if args['pid'] == '0':
                    return {'minutes': {'paragraphs': [{'pid': '0'}]}, 'more': True}
                raise m.UpstreamHTTPError(500, 'synthetic failure')
        with self.assertRaises(m.UpstreamHTTPError):
            m.read_file_transcript(Client(), 'meeting', 'file')

    def test_occurrence_continues_past_proven_empty_and_reads_later_file_fully(self):
        client, _ = self.client({'total': 0, 'pids': [], 'audio_detect': 1})
        original = client.call
        def call(name, args):
            if name == 'get_transcripts_details' and args['record_file_id'] == 'good':
                return {'more': False, 'minutes': {'paragraphs': [{
                    'pid': '0', 'start_time': 0, 'speaker': {'user_name': '合成'},
                    'sentences': [{'words': [{'text': '后续真实对话'}]}]}]}}
            return original(name, args)
        client.call = call
        files = [('group', 'empty'), ('group', 'good')]
        with patch.object(m, 'occurrence_files', return_value=(files, files, True)), \
                patch.object(m.time, 'sleep'), redirect_stdout(io.StringIO()):
            self.assertIn('后续真实对话', m.fetch_occurrence(client, {'meeting_id': 'meeting'}))


if __name__ == '__main__':
    unittest.main()
