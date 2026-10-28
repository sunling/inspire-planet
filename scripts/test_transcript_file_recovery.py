"""Synthetic file failures; no real service or meeting data."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import meeting_content as m


SHORT = '合成甲(00:00):\n简短对话。\n'
LONG = '合成甲(00:00):\n' + '会议真实讨论' * 200 + '\n'


class RecoveryTests(unittest.TestCase):
    def run_files(self, native, selected, responses, typed=True):
        calls, output = [], io.StringIO()
        def read(client, meeting_id, file_id):
            self.assertEqual(meeting_id, 'series')
            calls.append(file_id)
            value = responses[file_id]
            if isinstance(value, Exception):
                raise value
            return value
        with patch.object(m, 'occurrence_files', return_value=(native, selected, typed)), \
                patch.object(m, 'read_file_transcript', side_effect=read), redirect_stdout(output):
            result = m.fetch_occurrence(object(), {'meeting_id': 'series'})
        return result, calls, output.getvalue()

    def test_four_failed_typed_files_do_not_block_complete_candidates_and_native_fallback(self):
        selected = [('group', str(i)) for i in range(5)]
        native = selected + [('group', 'native-good'), ('group', 'native-bad')]
        responses = {str(i): m.UpstreamHTTPError(500, 'private-error') for i in range(4)}
        responses.update({'4': SHORT, 'native-good': LONG,
                          'native-bad': m.UpstreamHTTPError(500, 'private-error')})
        result, calls, log = self.run_files(native, selected, responses)
        self.assertEqual(result, LONG)
        self.assertEqual(len(calls), 7)
        self.assertEqual(len(set(calls)), 7)
        self.assertIn('读取失败文件=5', log)
        self.assertIn('不能确认所选稿比失败文件更长', log)
        self.assertNotIn('private', log)
        self.assertNotIn('会议真实讨论', log)

    def test_all_server_failures_are_not_classified_as_empty(self):
        files = [('group', 'one'), ('group', 'two')]
        with self.assertRaises(m.SafeError) as caught:
            self.run_files(files, files, {f: m.UpstreamHTTPError(500, 'failure') for _, f in files})
        self.assertNotIsInstance(caught.exception, m.NoTranscript)
        self.assertIn('读取失败文件=2', str(caught.exception))

    def test_permission_and_format_errors_still_stop(self):
        files = [('group', 'bad'), ('group', 'good')]
        for error in (m.UpstreamHTTPError(403, 'denied'), m.SafeError('invalid pagination')):
            with self.subTest(error=type(error).__name__), self.assertRaises(m.SafeError):
                self.run_files(files, files, {'bad': error, 'good': LONG})

    def test_success_without_failures_does_not_probe_unneeded_native_files(self):
        selected = [('group', 'text')]
        native = [('group', 'video')]
        result, calls, _ = self.run_files(native, selected, {'text': LONG})
        self.assertEqual(result, LONG)
        self.assertEqual(calls, ['text'])

    def test_conflicting_successful_ties_still_stop(self):
        files = [('group', 'bad'), ('group', 'one'), ('group', 'two')]
        with self.assertRaisesRegex(m.SafeError, '并列'):
            self.run_files(files, files, {'bad': m.UpstreamHTTPError(500, 'failure'),
                                          'one': '合成甲(00:00):\n甲乙\n',
                                          'two': '合成甲(00:00):\n丙丁\n'})

    def test_partial_failed_file_is_discarded_and_other_file_is_read_to_its_end(self):
        calls = []
        def paragraph(pid, text):
            return {'pid': str(pid), 'start_time': pid * 1000,
                    'speaker': {'user_name': '合成'}, 'sentences': [{'words': [{'text': text}]}]}
        class Client:
            def call(self, name, args):
                calls.append((args['record_file_id'], args['pid']))
                if args['record_file_id'] == 'bad':
                    if args['pid'] == '0':
                        return {'minutes': {'paragraphs': [paragraph(0, '不可使用的半份稿')]}, 'more': True}
                    raise m.UpstreamHTTPError(500, 'failed next page')
                pid = int(args['pid'])
                return {'minutes': {'paragraphs': [paragraph(pid, '完整稿的开头' if pid == 0 else '完整稿的结尾')]},
                        'more': pid == 0}
        files = [('group', 'bad'), ('group', 'good')]
        with patch.object(m, 'occurrence_files', return_value=(files, files, True)), redirect_stdout(io.StringIO()):
            text = m.fetch_occurrence(Client(), {'meeting_id': 'series'})
        self.assertNotIn('半份稿', text)
        self.assertIn('完整稿的结尾', text)
        self.assertEqual(calls, [('bad', '0'), ('bad', '1'), ('good', '0'), ('good', '1')])


if __name__ == '__main__':
    unittest.main()
