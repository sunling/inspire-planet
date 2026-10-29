"""Synthetic fixtures only; no credentials or network."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import diagnose_transcript as d
import meeting_content as m


class DiagnosticsTests(unittest.TestCase):
    def test_probes_alternate_ids_and_reports_errors_without_exposing_payload(self):
        row = {'meeting_id': 'private-series', 'sub_meeting_id': 'private-instance',
               'start_time': '2026-10-24T00:00:00Z'}
        calls = []
        class Client:
            def _call_once(self, name, args):
                calls.append((name, args))
                if args['record_file_id'] == 'private-transcript':
                    raise m.UpstreamHTTPError(500, 'private-response')
                return {'minutes': {'paragraphs': [{'text': 'private-text'}]}, 'more': True}
        output = io.StringIO()
        with patch.object(d.latest, 'historical_candidates', return_value=[row]), \
                patch.object(m, 'occurrence_files', return_value=(
                    [('group', 'private-native')], [('group', 'private-transcript')], True)), \
                redirect_stdout(output):
            d.diagnose(Client(), {}, '2026-10-24')
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(args['pid'] == '0' and args['limit'] == 1 for _, args in calls))
        self.assertIn('upstream_http=500', output.getvalue())
        self.assertIn('page_ok paragraphs=1 more=True', output.getvalue())
        self.assertIn('native-only', output.getvalue())
        self.assertNotIn('private', output.getvalue())

    def test_shared_ids_are_not_probed_twice_and_safe_errors_stay_hidden(self):
        row = {'meeting_id': 'series', 'sub_meeting_id': 'instance',
               'start_time': '2026-10-24T00:00:00Z'}
        from unittest.mock import Mock
        client = Mock()
        client._call_once.side_effect = m.SafeError('private-error')
        files = [('group', 'file')]
        output = io.StringIO()
        with patch.object(d.latest, 'historical_candidates', return_value=[row, row]), \
                patch.object(m, 'occurrence_files', return_value=(files, files, True)), \
                redirect_stdout(output):
            d.diagnose(client, {}, '2026-10-24')
        self.assertEqual(client._call_once.call_count, 1)
        self.assertIn('source=shared', output.getvalue())
        self.assertIn('rpc_business_or_format_error', output.getvalue())
        self.assertNotIn('private', output.getvalue())

    def test_global_probe_cap_never_silently_claims_complete(self):
        rows = [{'meeting_id': 'series', 'sub_meeting_id': str(i),
                 'start_time': '2026-10-24T00:00:00Z'} for i in range(3)]
        from unittest.mock import Mock
        client = Mock()
        client._call_once.return_value = {'empty_transcript': True}
        files = [('group', str(i)) for i in range(8)]
        output = io.StringIO()
        with patch.object(d.latest, 'historical_candidates', return_value=rows), \
                patch.object(m, 'occurrence_files', return_value=(files, files, False)), \
                redirect_stdout(output):
            d.diagnose(client, {}, '2026-10-24')
        self.assertEqual(client._call_once.call_count, 16)
        self.assertIn('诊断不完整', output.getvalue())


if __name__ == '__main__':
    unittest.main()
