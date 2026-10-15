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
                data = {'meeting_info_list': [{'meeting_id': 'synthetic-id', 'subject': 'Synthetic Planet', 'start_time': '2026-10-16T17:00:00-07:00'}], 'has_more': False}
            elif name == 'get_records_list':
                data = {'records': [{'record_file_id': 'empty', 'type': '转写', 'duration': '02:00:00'}, {'record_file_id': 'full', 'type': '转写', 'duration': '01:00:00'}], 'has_more': False}
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


class ModelTests(unittest.TestCase):
    def test_generate_validated_json_with_evidence_and_reject_bad_output(self):
        import copy
        text = '合成甲(00:00:01):\n这是合成测试。我开始记录。\n'
        summary = {'episode': 'EP41', 'date': '2026-10-17', 'title': '合成记录', 'overview': '合成测试里的记录。', 'topics': [{'speaker': '合成甲', 'title': '开始记录', 'context': '记录的开始。', 'keyPoints': ['开始记录。'], 'quote': '我开始记录。', 'discussion': ''}], 'highlights': []}
        cards = [{'name': '合成甲', 'title': '开始记录', 'quote': '我开始记录。', 'detail': '合成测试中谈到开始记录。', 'episode': 'EP41'}]
        payload = {'summary': summary, 'cards': cards}
        payload['evidence'] = [{'path': p, 'block': 0, 'excerpt': '我开始记录。'} for p in m.evidence_paths(payload)]
        seen = []
        def model(request):
            seen.append(request)
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': __import__('json').dumps(payload, ensure_ascii=False)}}]}
        result = m.generate(Path(__file__).parents[1], text, '2026-10-17', '41', 'synthetic-model', model)
        self.assertEqual(result['cards'], cards)
        self.assertIn('UNTRUSTED_TRANSCRIPT', seen[0]['messages'][1]['content'])
        self.assertIn('inspireplanet-summary', seen[0]['messages'][0]['content'])
        for mutate in [lambda p: p['cards'][0].update(name='不存在'), lambda p: p['summary']['topics'][0].update(quote='不存在的原话'), lambda p: p.update(evidence=[]), lambda p: p.update(extra='bad')]:
            bad = copy.deepcopy(payload); mutate(bad)
            with self.assertRaises(m.SafeError):
                m.validate_bundle(bad, m.parse_transcript(text), '2026-10-17', '41')
        with self.assertRaises(m.SafeError):
            m.generate(Path(__file__).parents[1], text, '2026-10-17', '41', 'synthetic-model', lambda r: {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]})


class DraftTests(unittest.TestCase):
    def test_remote_branch_or_existing_content_skips_before_generation(self):
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
            plan = m.prepare(root, '2026-10-17', '41', 'main', 'local', run)
            self.assertTrue(plan['skip'])
            self.assertTrue(any(c[:2] == ['git', 'ls-remote'] for c in commands))
            with self.assertRaises(m.SafeError):
                m.prepare(root, '2026-10-17', '41', 'other-base', 'local', run)

    def test_only_allowlisted_draft_files_written_no_overwrite(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / 'events').mkdir()
            (root / 'events/README.md').write_text('# 合成索引\n')
            event, _ = m.event_identity('2026-10-17', '41')
            payload = {'summary': {'title': '合成'}, 'cards': [], 'evidence': []}
            paths = m.write_draft(root, event, '合成甲(00:01):\n合成测试\n', payload)
            self.assertEqual(set(paths), {event + '/' + p for p in ['transcript.txt', 'summary.json', 'quote-cards.json', 'README.md']} | {'events/README.md'})
            self.assertEqual(json.loads((root / event / 'summary.json').read_text()), payload['summary'])
            self.assertIn(event.removeprefix('events/'), (root / 'events/README.md').read_text())
            with self.assertRaises(m.SafeError):
                m.write_draft(root, event, 'changed', payload)


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
    def test_local_validate_executes_without_credentials_or_writes(self):
        import tempfile
        import os
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event, _ = m.event_identity('2026-10-17', '41')
            target = root / event; target.mkdir(parents=True)
            (target / 'transcript.txt').write_text('合成甲(00:01):\n合成验证文本。\n')
            env = {'CONTENT_DATE': '2026-10-17', 'CONTENT_EPISODE': '41', 'CONTENT_SOURCE': 'local'}
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
        self.assertNotIn('secrets.', ci)
        self.assertIn('check-content.py', ci)
        self.assertIn("vars.CONTENT_AUTOMATION_ENABLED == 'true'", flow)
        self.assertIn('github.event.repository.default_branch', flow)
        self.assertNotIn('pull_request', flow.split('permissions:')[0])
        self.assertIn('persist-credentials: false', flow)
        self.assertIn('cancel-in-progress: false', flow)
        self.assertIn('TENCENT_MEETING_TOKEN: ${{ secrets.TENCENT_MEETING_TOKEN }}', flow)
        self.assertNotIn('run: ${{', flow)
        self.assertNotIn('pull_request_target', flow)


class EndToEndTests(unittest.TestCase):
    def test_synthetic_draft_with_real_local_git_and_stubbed_github_only(self):
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
            target = root / event; target.mkdir(parents=True)
            text = '合成甲(00:01):\n我开始记录。这是合成测试。\n'
            (target / 'transcript.txt').write_text(text)
            (root / 'events/README.md').write_text(f'# 索引\n\n| 期次 | 转写 | 纪要 | 卡片 | 文案 | 封面 |\n|---|---|---|---|---|---|\n| 20261017-ep41 | [转写]({event.removeprefix("events/")}/transcript.txt) | — | — | — | — |\n')
            git(['add', '.']); git(['commit', '-m', 'synthetic baseline'])
            git(['push', 'origin', 'main'])
            def run(args):
                if args[0] == 'git': return git(args[1:])
                if args[:3] == ['gh', 'pr', 'list']: return '[]'
                if args[:3] == ['gh', 'pr', 'create']:
                    self.assertIn('--draft', args); return 'synthetic-pr'
                if args[:3] == ['gh', 'pr', 'view']:
                    return json.dumps({'state': 'OPEN', 'isDraft': True, 'headRefName': branch, 'baseRefName': 'main', 'files': [{'path': p} for p in m.allowed_paths(event) if p != event + '/transcript.txt']})
                raise AssertionError(args)
            plan = m.prepare(root, '2026-10-17', '41', 'main', 'local', run)
            self.assertFalse(plan['skip'])
            summary = {'episode': 'EP41', 'date': '2026-10-17', 'title': '合成记录', 'overview': '合成记录测试。', 'topics': [{'speaker': '合成甲', 'title': '记录', 'context': '开始记录。', 'keyPoints': ['开始记录。'], 'quote': '我开始记录。', 'discussion': ''}], 'highlights': []}
            payload = {'summary': summary, 'cards': [{'name': '合成甲', 'title': '记录', 'quote': '我开始记录。', 'detail': '合成的记录场景。', 'episode': 'EP41'}]}
            payload['evidence'] = [{'path': p, 'block': 0, 'excerpt': '我开始记录。'} for p in m.evidence_paths(payload)]
            m.validate_bundle(payload, m.parse_transcript(text), '2026-10-17', '41')
            m.write_draft(root, event, text, payload)
            index = (root / 'events/README.md').read_text()
            self.assertIn('/summary.json', index)
            self.assertIn('/quote-cards.json', index)
            # Run the real repository checker against the isolated synthetic tree.
            (root / 'scripts').mkdir()
            shutil.copy(Path(__file__).with_name('check-content.py'), root / 'scripts/check-content.py')
            checked = subprocess.run(['python3', 'scripts/check-content.py'], cwd=root, capture_output=True, text=True, check=True)
            self.assertIn('Content check passed: 1 episodes', checked.stdout)
            (root / 'scripts/check-content.py').unlink(); (root / 'scripts').rmdir()
            result = m.publish(root, plan, run)
            self.assertTrue(result['isDraft'])
            self.assertEqual(git(['rev-parse', 'HEAD']).strip(), git(['ls-remote', '--heads', 'origin', 'refs/heads/' + branch]).split()[0])
            git(['switch', 'main'])
            self.assertTrue(m.prepare(root, '2026-10-17', '41', 'main', 'local', run)['skip'])


if __name__ == '__main__':
    unittest.main()
