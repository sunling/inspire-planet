"""Synthetic fixtures only; no live model or GitHub PR integration claimed."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SelectionTests(unittest.TestCase):
    def test_latest_includes_event_with_both_outputs_missing(self):
        spec = importlib.util.spec_from_file_location('content_plan', ROOT / 'scripts/content_plan.py')
        self.assertIsNotNone(spec)
        self.assertTrue(Path(spec.origin).exists(), 'content_plan implementation is missing')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        paths = {'events/2026/20261003-ep39/transcript.txt': {},
                 'events/2026/20261010-ep40/transcript.txt': {}}
        self.assertEqual(module.select_event(paths), 'events/2026/20261010-ep40')


# Entirely invented transcript/response fixture, not real meeting material.
TEXT = '甲(00:00:00):\n我试着先走一小步。\n\n乙(00:01:00):\n我也试过。\n'
EVENT = 'events/2026/20261010-ep40'


def fixture():
    import copy
    fields = {'episode': 'EP40', 'date': '2026-10-10', 'title': '一小步',
              'overview': '甲尝试先走一小步。', 'topics': [
                  {'speaker': '甲', 'title': '一小步', 'context': '甲谈自己的尝试。',
                   'keyPoints': ['甲先尝试行动。'], 'quote': '我试着先走一小步。',
                   'discussion': ''}], 'highlights': []}
    card = {'name': '甲', 'title': '一小步', 'quote': '我试着先走一小步。',
            'detail': '甲在分享时谈到先行动的尝试。', 'episode': 'EP40'}
    evidence = {}
    for pointer in ['/summary.json/title', '/summary.json/overview',
                    '/summary.json/topics/0/title', '/summary.json/topics/0/context',
                    '/summary.json/topics/0/keyPoints/0', '/summary.json/topics/0/quote',
                    '/quote-cards.json/0/title', '/quote-cards.json/0/quote', '/quote-cards.json/0/detail']:
        evidence[pointer] = [{'block_id': 'b0001', 'excerpt': '我试着先走一小步。'}]
    return copy.deepcopy({'outputs': {'summary.json': fields, 'quote-cards.json': [card]}, 'evidence': evidence})


class PlanningTests(unittest.TestCase):
    def test_pr_source_requires_same_repository_and_pinned_sha(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'trusted_pr'), 'PR trust check is missing')
        pr = {'state': 'open', 'base': {'ref': 'main', 'repo': {'full_name': 'sunling/inspire-planet'}},
              'head': {'ref': 'content/transcript', 'sha': 'a' * 40,
                       'repo': {'full_name': 'sunling/inspire-planet'}}}
        self.assertEqual(c.trusted_pr(pr, 'sunling/inspire-planet'), ('content/transcript', 'a' * 40))
        pr['head']['repo']['full_name'] = 'stranger/fork'
        with self.assertRaises(c.SafeError):
            c.trusted_pr(pr, 'sunling/inspire-planet')


    def test_existing_content_branch_skips_before_transcript_download(self):
        import content_plan as c
        api = FixtureGitHub()
        api.files[EVENT + '/transcript.txt'] = TEXT
        api.branches['content/json-2026-ep40'] = 'b' * 40
        api.read = lambda *args: self.fail('skip must not download any data blob')
        self.assertTrue(c.prepare(api)['skip'])

    def test_both_existing_outputs_skip_and_incoming_never_selects(self):
        import content_plan as c
        api = FixtureGitHub()
        api.files = {EVENT + '/transcript.txt': TEXT, EVENT + '/summary.json': '{}',
                     EVENT + '/quote-cards.json': '[]', 'incoming/meetings/' + 'a' * 64 + '/transcript.txt': TEXT}
        self.assertTrue(c.prepare(api)['skip'])
        self.assertEqual(c.prepare(api, target='2026/EP40')['reason'], 'both-outputs-exist')

    def test_year_episode_selection_is_unambiguous(self):
        import content_plan as c
        paths = {EVENT + '/transcript.txt': {}, 'events/2025/20251018-ep40/transcript.txt': {}}
        self.assertEqual(c.select_event(paths, '2025/EP40'), 'events/2025/20251018-ep40')
        for target in ['EP40', '2026/EP41', '2026/ep40']:
            with self.subTest(target=target), self.assertRaises(c.SafeError):
                c.select_event(paths, target)

    def test_duplicate_episode_mapping_stops(self):
        import content_plan as c
        with self.assertRaises(c.SafeError):
            c.select_event({EVENT + '/transcript.txt': {}, 'events/2026/20261017-ep40/transcript.txt': {}}, '2026/EP40')

    def test_prepare_default_is_latest_and_preserves_existing_card(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'prepare'), 'data-only planning path is missing')
        api = FixtureGitHub()
        api.files[EVENT + '/transcript.txt'] = TEXT
        api.files[EVENT + '/quote-cards.json'] = 'human existing bytes'
        plan = c.prepare(api)
        self.assertEqual(plan['event'], EVENT)
        self.assertEqual(plan['wanted'], ['summary.json'])
        self.assertEqual(plan['existing']['quote-cards.json'], 'human existing bytes')


class FixtureGitHub:
    """Invented immutable repository adapter, NOT live GitHub evidence."""
    repo = 'sunling/inspire-planet'
    def __init__(self):
        self.files = {}
        self.prs = []
        self.branches = {'main': 'a' * 40}
        self.writes = []
    def head(self, branch):
        return self.branches.get(branch)
    def tree(self, sha):
        import hashlib
        return {p: {'sha': hashlib.sha1(v.encode()).hexdigest(), 'mode': '100644', 'type': 'blob', 'size': len(v.encode())}
                for p, v in self.files.items()}
    def open_prs(self):
        return self.prs
    def pr(self, number):
        return next(p for p in self.prs if p['number'] == number)
    def branch_prs(self, branch):
        return [p for p in self.prs if p['head']['ref'] == branch]
    def read(self, tree, path):
        return self.files[path]


class PublicationTests(unittest.TestCase):
    def test_main_race_stops_before_any_external_write(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'publish'), 'race-guarded publication is missing')
        api = FixtureGitHub()
        api.files[EVENT + '/transcript.txt'] = TEXT
        plan = c.prepare(api)
        api.branches['main'] = 'b' * 40
        with self.assertRaises(c.SafeError):
            c.publish(api, plan, fixture())
        self.assertEqual(api.writes, [])


class GitHubAdapterTests(unittest.TestCase):
    def test_commit_payload_has_atomic_expected_head_and_only_additions(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'GitHub'), 'gh data-only adapter is missing')
        api = c.GitHub('sunling/inspire-planet')
        captured = []
        def request(path, payload=None, optional=False):
            captured.append((path, payload))
            return {'data': {'createCommitOnBranch': {'commit': {'oid': 'b' * 40}}}}
        api.request = request
        self.assertEqual(api.commit('content/test', 'a' * 40, {EVENT + '/summary.json': '{}'}), 'b' * 40)
        payload = captured[0][1]
        self.assertEqual(payload['variables']['input']['expectedHeadOid'], 'a' * 40)
        self.assertEqual(payload['variables']['input']['fileChanges']['deletions'], [])
        self.assertEqual(payload['variables']['input']['fileChanges']['additions'][0]['path'], EVENT + '/summary.json')


class LocalGit(FixtureGitHub):
    """Real temporary Git object store; PR metadata ONLY is synthetic."""
    def __init__(self, path):
        self.path = path
        self.prs = []
        self.writes = []
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (path / 'README.md').write_text('Synthetic fixture repository\n')
        self.git('add', 'README.md')
        self.git('commit', '-m', 'synthetic baseline')
    def git(self, *args, data=None, env=None):
        import os
        import subprocess
        result = subprocess.run(['git', *args], cwd=self.path, input=data, capture_output=True,
                                text=True, env=dict(os.environ, **(env or {})))
        if result.returncode:
            raise RuntimeError('local Git fixture command failed: ' + result.stderr)
        return result.stdout.strip()
    def head(self, branch):
        try:
            return self.git('rev-parse', '--verify', 'refs/heads/' + branch)
        except RuntimeError:
            return None
    def tree(self, sha):
        result = {}
        for line in self.git('ls-tree', '-rl', sha).splitlines():
            meta, path = line.split('\t', 1)
            mode, kind, oid, size = meta.split()
            result[path] = {'mode': mode, 'type': kind, 'sha': oid, 'size': int(size)}
        return result
    def read(self, tree, path):
        # No strip: byte-for-byte preservation, including terminal newline.
        import subprocess
        return subprocess.check_output(['git', 'cat-file', 'blob', tree[path]['sha']], cwd=self.path).decode()
    def create_branch(self, branch, sha):
        self.git('update-ref', 'refs/heads/' + branch, sha, '0' * 40)
        self.writes.append(('branch', branch))
    def commit(self, branch, expected, additions):
        import content_plan as c
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            env = {'GIT_INDEX_FILE': str(Path(temporary) / 'index')}
            self.git('read-tree', expected, env=env)
            for path, raw in additions.items():
                oid = self.git('hash-object', '-w', '--stdin', data=raw)
                self.git('update-index', '--add', '--cacheinfo', '100644,' + oid + ',' + path, env=env)
            tree = self.git('write-tree', env=env)
            sha = self.git('commit-tree', tree, '-p', expected, data='synthetic content\n')
            try:
                self.git('update-ref', 'refs/heads/' + branch, sha, expected)
            except RuntimeError:
                raise c.SafeError('local atomic CAS rejected stale head') from None
        self.writes.append(('commit', branch))
        return sha
    def create_pr(self, branch, event, body):
        number = len(self.prs) + 1
        self.prs.append({'number': number, 'state': 'open', 'draft': True,
                         'base': {'ref': 'main', 'repo': {'full_name': self.repo}},
                         'head': {'ref': branch, 'sha': self.head(branch), 'repo': {'full_name': self.repo}}})
        self.writes.append(('synthetic_pr_metadata', number))
        return number
    def pr(self, number):
        row = super().pr(number)
        import copy
        row = copy.deepcopy(row)
        row['head']['sha'] = self.head(row['head']['ref'])
        return row
    def open_prs(self):
        return [self.pr(p['number']) for p in self.prs]


class LocalGitIntegrationTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temporary = tempfile.TemporaryDirectory(prefix='content-plan-test-')
        self.addCleanup(self.temporary.cleanup)
        self.api = LocalGit(Path(self.temporary.name))

    def seed_main(self, extra=None):
        files = {EVENT + '/transcript.txt': TEXT}
        files.update(extra or {})
        self.api.commit('main', self.api.head('main'), files)
        self.api.writes.clear()

    def test_real_git_fallback_only_json_and_existing_bytes_preserved(self):
        import content_plan as c
        self.seed_main({EVENT + '/quote-cards.json': 'human untouched\n'})
        before = self.api.head('main')
        plan = c.prepare(self.api)
        packet = fixture()
        packet['outputs'].pop('quote-cards.json')
        packet['evidence'] = {p: e for p, e in packet['evidence'].items() if p.startswith('/summary.json/')}
        pr = c.publish(self.api, plan, packet)
        self.assertTrue(pr['draft'])  # synthetic metadata, not a live GitHub PR test
        self.assertEqual(self.api.head('main'), before)
        tree = self.api.tree(pr['head']['sha'])
        self.assertEqual(self.api.read(tree, EVENT + '/quote-cards.json'), 'human untouched\n')
        self.assertEqual(set(tree) - set(plan['main_tree']), {EVENT + '/summary.json'})
        self.assertTrue(c.prepare(self.api)['skip'])

    def test_real_git_append_same_trusted_transcript_branch(self):
        import content_plan as c
        self.api.create_branch('content/transcript', self.api.head('main'))
        self.api.commit('content/transcript', self.api.head('main'), {EVENT + '/transcript.txt': TEXT})
        self.api.create_pr('content/transcript', EVENT, 'synthetic metadata')
        plan = c.prepare(self.api, pr_number=1)
        self.assertTrue(plan['append'])
        before = self.api.head('main')
        pr = c.publish(self.api, plan, fixture())
        self.assertEqual(pr['number'], 1)
        self.assertEqual(len(self.api.prs), 1)
        self.assertEqual(self.api.head('main'), before)
        self.assertEqual(set(self.api.tree(pr['head']['sha'])) - set(plan['source_tree']),
                         {EVENT + '/' + n for n in c.OUTPUTS})

    def test_actual_check_content_runs_in_temporary_overlay_only(self):
        import content_plan as c
        import shutil
        root = self.api.path
        (root / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/check-content.py', root / 'scripts/check-content.py')
        c.check_payload(root, {'event': EVENT, 'transcript': TEXT, 'wanted': list(c.OUTPUTS), 'existing': {}}, fixture())
        self.assertFalse((root / 'events').exists())

    def test_pr_code_is_never_executed_or_copied_in_fallback(self):
        import content_plan as c
        self.api.create_branch('content/transcript', self.api.head('main'))
        self.api.commit('content/transcript', self.api.head('main'), {
            EVENT + '/transcript.txt': TEXT, 'scripts/untrusted.py': 'raise RuntimeError("must never execute")\n'})
        self.api.create_pr('content/transcript', EVENT, '')
        plan = c.prepare(self.api, pr_number=1)
        self.assertFalse(plan['append'])
        pr = c.publish(self.api, plan, fixture())
        self.assertEqual(pr['number'], 2)
        tree = self.api.tree(pr['head']['sha'])
        self.assertNotIn('scripts/untrusted.py', tree)
        self.assertEqual(set(tree) - set(plan['main_tree']), {EVENT + '/' + n for n in (*c.OUTPUTS, 'transcript.txt')})

    def test_pending_incoming_pr_stops_before_generation(self):
        import content_plan as c
        self.api.create_branch('content/pending', self.api.head('main'))
        self.api.commit('content/pending', self.api.head('main'), {'incoming/meetings/' + 'a' * 64 + '/transcript.txt': TEXT})
        self.api.create_pr('content/pending', EVENT, '')
        self.api.writes.clear()
        with self.assertRaisesRegex(c.SafeError, 'incoming'):
            c.prepare(self.api, pr_number=1)
        self.assertEqual(self.api.writes, [])

    def test_json_added_during_generation_blocks_publication(self):
        import content_plan as c
        self.seed_main()
        plan = c.prepare(self.api)
        self.api.create_branch('content/other-editor', self.api.head('main'))
        self.api.commit('content/other-editor', self.api.head('main'), {EVENT + '/summary.json': '{}'})
        self.api.create_pr('content/other-editor', EVENT, '')
        self.api.writes.clear()
        with self.assertRaises(c.SafeError):
            c.publish(self.api, plan, fixture())
        self.assertEqual(self.api.writes, [])

    def test_source_race_blocks_writes_and_atomic_cas_rejects_stale_head(self):
        import content_plan as c
        self.api.create_branch('content/transcript', self.api.head('main'))
        old = self.api.commit('content/transcript', self.api.head('main'), {EVENT + '/transcript.txt': TEXT})
        self.api.create_pr('content/transcript', EVENT, '')
        plan = c.prepare(self.api, pr_number=1)
        new = self.api.commit('content/transcript', old, {EVENT + '/README.md': 'changed by editor\n'})
        self.api.writes.clear()
        with self.assertRaises(c.SafeError):
            c.publish(self.api, plan, fixture())
        self.assertEqual(self.api.writes, [])
        with self.assertRaises(c.SafeError):
            self.api.commit('content/transcript', old, {EVENT + '/summary.json': '{}'})
        self.assertEqual(self.api.head('content/transcript'), new)


class WorkflowTests(unittest.TestCase):
    def test_actual_precheckout_shell_gate_fails_without_config(self):
        import os
        import subprocess
        data = (ROOT / '.github/workflows/content-plan.yml').read_text()
        block = data.split('        run: |\n', 1)[1].split('      - uses:', 1)[0]
        script = '\n'.join(line[10:] for line in block.splitlines())
        env = dict(os.environ, CONTENT_LLM_BASE_URL='', CONTENT_LLM_MODEL='', CONTENT_LLM_KEY_PRESENT='false')
        result = subprocess.run(['bash', '-eu', '-c', script], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Plan B 未启用', result.stdout)
        env.update(CONTENT_LLM_BASE_URL='https://model.invalid/v1', CONTENT_LLM_MODEL='synthetic', CONTENT_LLM_KEY_PRESENT='true')
        self.assertEqual(subprocess.run(['bash', '-eu', '-c', script], env=env, capture_output=True).returncode, 0)

    def test_manual_main_only_scoped_secrets_and_no_chaining(self):
        path = ROOT / '.github/workflows/content-plan.yml'
        self.assertTrue(path.exists(), 'manual Plan B workflow is missing')
        data = path.read_text()
        self.assertIn('workflow_dispatch:', data)
        self.assertIn('- name: Configuration gate', data, 'missing-config gate must precede checkout/download')
        self.assertLess(data.index('- name: Configuration gate'), data.index('- uses: actions/checkout'))
        self.assertNotIn('schedule:', data)
        self.assertNotIn('pull_request:', data)
        self.assertNotIn('workflow_run:', data)
        self.assertIn("github.ref == 'refs/heads/main'", data)
        self.assertEqual(data.count('CONTENT_LLM_API_KEY: ${{ secrets.CONTENT_LLM_API_KEY }}'), 1)
        generation = data.split('- name: Generate', 1)[1].split('- name:', 1)[0]
        self.assertNotIn('GH_TOKEN:', generation)
        self.assertNotIn('GITHUB_TOKEN:', generation)
        self.assertIn('persist-credentials: false', data)
        self.assertIn('content-plan.json', data)


class CLITests(unittest.TestCase):
    def test_missing_config_cli_precedes_github_and_file_writes(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'main'), 'manual CLI is missing')
        with self.assertRaisesRegex(c.SafeError, 'Plan B 未启用'):
            c.main(['prepare'], env={})


class TransportTests(unittest.TestCase):
    @staticmethod
    def env():
        return {'CONTENT_LLM_BASE_URL': 'https://model.example.invalid/v1',
                'CONTENT_LLM_MODEL': 'synthetic-model-not-real', 'CONTENT_LLM_API_KEY': 'synthetic-not-a-key'}

    @staticmethod
    def plan():
        return {'transcript': TEXT, 'event': EVENT, 'wanted': ['summary.json', 'quote-cards.json'],
                'rules': 'synthetic trusted fixture rules', 'existing': {}}

    def test_synthetic_transport_exercises_protocol_and_prompt_boundary(self):
        import content_plan as c
        import json
        calls = []
        def send(url, payload, key):
            calls.append((url, payload, key))
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(fixture())}}]}
        self.assertEqual(c.generate(self.plan(), self.env(), send), fixture())
        self.assertEqual(len(calls), 1)
        url, payload, _ = calls[0]
        self.assertTrue(url.endswith('/v1/chat/completions'))
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(payload['max_completion_tokens'], 12000)
        self.assertNotIn('tools', payload)
        self.assertIn('不可信', payload['messages'][0]['content'].replace('未信任', '不可信'))
        self.assertIn('b0001', payload['messages'][1]['content'])
        self.assertNotIn(TEXT, payload['messages'][0]['content'])

    def test_truncation_rejected_without_paid_retry(self):
        import content_plan as c
        calls = []
        def send(*args):
            calls.append(args)
            return {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}
        with self.assertRaisesRegex(c.SafeError, '截断'):
            c.generate(self.plan(), self.env(), send)
        self.assertEqual(len(calls), 1)

    def test_tools_and_non_json_rejected(self):
        import content_plan as c
        for message in [{'tool_calls': [{'function': {}}], 'content': '{}'}, {'content': 'not json'}]:
            with self.subTest(message=message), self.assertRaises(c.SafeError):
                c.generate(self.plan(), self.env(), lambda *args: {'choices': [{'finish_reason': 'stop', 'message': message}]})

    def test_overlong_full_prompt_makes_zero_requests(self):
        import content_plan as c
        plan = self.plan()
        plan['rules'] = 'x' * c.MAX_INPUT_BYTES
        calls = []
        with self.assertRaises(c.SafeError):
            c.generate(plan, self.env(), lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_no_github_token_in_generation_step(self):
        import content_plan as c
        with self.assertRaises(c.SafeError):
            c.generate(self.plan(), dict(self.env(), GH_TOKEN='synthetic'), lambda *args: self.fail('must not call'))

    def test_https_only_and_no_redirects(self):
        import content_plan as c
        for base in ['http://model.invalid/v1', 'https://user:key@model.invalid/v1', 'https://model.invalid/v1?key=x']:
            with self.subTest(base=base), self.assertRaises(c.SafeError):
                c.preflight(dict(self.env(), CONTENT_LLM_BASE_URL=base))
        with self.assertRaises(c.SafeError):
            c.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.invalid')

    def test_http_error_body_and_key_never_in_safe_error(self):
        import content_plan as c
        import io
        import urllib.error
        class SyntheticOpener:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(request.full_url, 401, 'sensitive error', {}, io.BytesIO(b'private transcript sentinel'))
        with self.assertRaises(c.SafeError) as caught:
            c.transport('https://model.invalid/v1/chat/completions', {}, 'secret-sentinel', SyntheticOpener())
        self.assertNotIn('sentinel', str(caught.exception))
        self.assertNotIn('sensitive', str(caught.exception))

    def test_response_size_bound_rejects_without_truncation(self):
        import content_plan as c
        import io
        class SyntheticOpener:
            def open(self, request, timeout):
                return io.BytesIO(b'x' * (c.MAX_REPLY_BYTES + 1))
        with self.assertRaises(c.SafeError):
            c.transport('https://model.invalid/v1/chat/completions', {}, 'synthetic', SyntheticOpener())

    def test_missing_configuration_makes_zero_network_calls(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'generate'), 'bounded generation path is missing')
        calls = []
        with self.assertRaises(c.SafeError):
            c.generate({}, {}, lambda *args: calls.append(args))
        self.assertEqual(calls, [])


class ValidationTests(unittest.TestCase):
    def test_malformed_summary_schema_rejected(self):
        import content_plan as c
        packet = fixture()
        packet['outputs']['summary.json']['unexpected'] = 'no'
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_unknown_speaker_rejected(self):
        import content_plan as c
        packet = fixture()
        packet['outputs']['summary.json']['topics'][0]['speaker'] = '未知名字'
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_evidence_attribution_must_match_speaker(self):
        import content_plan as c
        packet = fixture()
        packet['evidence']['/summary.json/topics/0/quote'] = [{'block_id': 'b0002', 'excerpt': '我也试过。'}]
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_evidence_must_be_continuous_excerpt_not_combined_fragments(self):
        import content_plan as c
        packet = fixture()
        packet['evidence']['/summary.json/overview'][0]['excerpt'] = '我试着走一小步。'
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_invented_quote_rejected_even_when_evidence_exists(self):
        import content_plan as c
        packet = fixture()
        packet['outputs']['quote-cards.json'][0]['quote'] = '行动就一定成功。'
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_missing_evidence_rejected(self):
        import content_plan as c
        packet = fixture()
        packet['evidence'].pop('/summary.json/overview')
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_no_empty_cards_placeholder(self):
        import content_plan as c
        packet = fixture()
        packet['outputs']['quote-cards.json'] = []
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_wrong_year_episode_date_and_display_source_notes_rejected(self):
        import content_plan as c
        for key, bad in [('date', '2025-10-10'), ('episode', 'EP39')]:
            packet = fixture()
            packet['outputs']['summary.json'][key] = bad
            with self.subTest(key=key), self.assertRaises(c.SafeError):
                c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))
        packet = fixture()
        packet['outputs']['quote-cards.json'][0]['detail'] = '出处：00:00:00'
        with self.assertRaises(c.SafeError):
            c.validate(packet, EVENT, TEXT, list(c.OUTPUTS))

    def test_duplicate_json_keys_rejected(self):
        import content_plan as c
        with self.assertRaises(c.SafeError):
            c.strict_json('{"outputs":{},"outputs":{}}')

    def test_overlong_transcript_rejected_whole(self):
        import content_plan as c
        with self.assertRaises(c.SafeError):
            c.validate(fixture(), EVENT, TEXT + '长' * 300001, list(c.OUTPUTS))

    def test_exact_contract_evidence_and_empty_discussion(self):
        import content_plan as c
        self.assertTrue(hasattr(c, 'validate'), 'strict validator is missing')
        self.assertEqual(set(c.validate(fixture(), EVENT, TEXT, list(c.OUTPUTS))), set(c.OUTPUTS))


if __name__ == '__main__':
    unittest.main()
