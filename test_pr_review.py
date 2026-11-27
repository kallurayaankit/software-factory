import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import pr_review as review

ROOT = Path(__file__).resolve().parent


class PRReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'target'
        self.repo.mkdir()
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'Fixture Reviewer')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.source = self.repo / 'greeting.py'
        self.source.write_text('"""A tiny greeting module."""\n\ndef greeting():\n    return "hello"\n')
        self.base = self.commit()
        self.source.write_text('"""A tiny greeting module. REVIEW_REQUIRED: wording."""\n\ndef greeting():\n    return "hello"\n')
        self.head = self.commit()
        self.spec = self.root / 'spec.json'
        self.spec_data = dict(schema_version=1, title='Clarify greeting documentation',
                              approval=dict(approved=True, reviewer='Fixture Reviewer'),
                              allowed_paths=['greeting.py'],
                              requirements=[dict(id='R1', text='Keep greeting behavior unchanged.')])
        self.write_spec()
        self.output = self.root / 'bundle'

    def git(self, *args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.repo), *args],
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def commit(self):
        self.git('add', '--all')
        self.git('commit', '--quiet', '-m', 'Synthetic benign fixture')
        return self.git('rev-parse', 'HEAD')

    def write_spec(self):
        self.spec.write_bytes(review.dump(self.spec_data))
        self.spec_hash = review.digest(self.spec.read_bytes())

    def build(self, replay=None):
        return review.build(self.repo, self.base, self.head, self.spec, self.spec_hash,
                            self.output, replay)

    def candidate(self):
        return dict(path='greeting.py', side='head', line=1,
                    excerpt='"""A tiny greeting module. REVIEW_REQUIRED: wording."""',
                    message='Inspect the documentation marker.')

    def replay(self, finding):
        path = self.root / 'replay.json'
        path.write_bytes(review.dump(dict(schema_version=1, findings=[finding])))
        return path

    def test_real_benign_change_cli_and_self_contained_verification(self):
        before = self.git('status', '--porcelain=v1')
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'pr_review.py'), 'review',
                                 '--repo', str(self.repo), '--base', self.base, '--head', self.head,
                                 '--spec', str(self.spec), '--approved-spec-sha256', self.spec_hash,
                                 '--output', str(self.output)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads((self.output / 'input.json').read_text())
        self.assertEqual((data['requested_base'], data['merge_base'], data['head']),
                         (self.base, self.base, self.head))
        findings = json.loads((self.output / 'findings.json').read_text())
        self.assertEqual(len(findings['findings']), 1)
        self.assertEqual(findings['findings'][0]['line'], 1)
        self.assertIn('benign marker check only', findings['reviewer'])
        self.assertIn('No target code', (self.output / 'report.md').read_text())
        self.assertEqual(self.git('status', '--porcelain=v1'), before)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.head)
        fingerprint = result.stdout.strip().splitlines()[-1].split(': ', 1)[1]
        self.repo.rename(self.root / 'unavailable-target')
        self.assertEqual(review.verify(self.output, fingerprint), fingerprint)

    def test_uncommitted_worktree_change_is_excluded(self):
        self.source.write_text('raise RuntimeError("WORKTREE_ONLY: never execute")\n')
        (self.repo / 'untracked.txt').write_text('UNTRACKED_ONLY')
        before = self.git('status', '--porcelain=v1')
        self.build()
        for path in self.output.iterdir():
            self.assertNotIn(b'WORKTREE_ONLY', path.read_bytes())
            self.assertNotIn(b'UNTRACKED_ONLY', path.read_bytes())
        self.assertEqual(self.source.read_text(), 'raise RuntimeError("WORKTREE_ONLY: never execute")\n')
        self.assertEqual(self.git('status', '--porcelain=v1'), before)

    def test_fabricated_and_unchanged_citations_are_rejected(self):
        for change in (dict(path='missing.py'), dict(line=999), dict(excerpt='invented'),
                       dict(side='base'), dict(line=4, excerpt='    return "hello"')):
            with self.subTest(change=change):
                candidate = dict(self.candidate(), **change)
                with self.assertRaisesRegex(ValueError, 'Citation'):
                    self.build(self.replay(candidate))
                self.assertFalse(self.output.exists())

    def test_deleted_line_replay_is_valid_and_labelled_unverified(self):
        candidate = dict(self.candidate(), side='base',
                         excerpt='"""A tiny greeting module."""')
        token = self.build(self.replay(candidate))
        result = json.loads((self.output / 'findings.json').read_text())
        self.assertIn('semantics unverified', result['reviewer'])
        self.assertEqual(result['findings'][0]['side'], 'base')
        self.assertEqual(review.verify(self.output), token)

    def test_no_marker_does_not_mean_clean_review(self):
        self.source.write_text('"""An ordinary documentation update."""\n\ndef greeting():\n    return "hello"\n')
        self.head = self.commit()
        self.build()
        result = json.loads((self.output / 'findings.json').read_text())
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['decision'], 'HUMAN REVIEW REQUIRED')
        self.assertIn('not a clean bill of health', (self.output / 'report.md').read_text())

    def test_spec_approval_and_version_pin_required(self):
        self.spec_hash = '0' * 64
        with self.assertRaisesRegex(ValueError, 'approved SHA-256'):
            self.build()
        self.spec_data['approval']['approved'] = False
        self.write_spec()
        with self.assertRaisesRegex(ValueError, 'explicitly approved'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_non_sha_revision_and_out_of_scope_paths_rejected(self):
        original = self.base
        for revision in ('HEAD', '--help', 'a' * 39, 'a' * 40):
            self.base = revision
            with self.assertRaises(ValueError):
                self.build()
        self.base = original
        self.spec_data['allowed_paths'] = ['other.py']
        self.write_spec()
        with self.assertRaisesRegex(ValueError, 'out-of-scope'):
            self.build()

    def test_oversized_blob_and_changed_line_limit(self):
        for text, pattern in [('x' * (review.MAX_BLOB + 1), 'byte limit'),
                              ('new line\n' * (review.MAX_CHANGED_LINES + 1), 'line count')]:
            self.source.write_text(text)
            self.head = self.commit()
            with self.assertRaisesRegex(ValueError, pattern):
                self.build()
            self.assertFalse(self.output.exists())

    def test_unsafe_names_symlinks_binary_and_crlf_rejected(self):
        for path in ('../escape', '/absolute', '.git/config', 'a//b', 'a\\b', 'a\nb'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                review.safe_path(path)
        for data in (b'hello\0world', b'hello\r\n', b'\xff'):
            self.source.write_bytes(data)
            self.head = self.commit()
            with self.assertRaises((ValueError, UnicodeError)):
                self.build()
        self.source.unlink()
        self.source.symlink_to('/does-not-exist')
        self.head = self.commit()
        with self.assertRaisesRegex(ValueError, 'file mode'):
            self.build()

    def test_target_output_and_existing_output_rejected(self):
        self.output = self.repo / 'bundle'
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.build()
        self.output = self.root / 'existing'
        self.output.mkdir()
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.build()
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_tampering_and_wrong_trusted_fingerprint_rejected(self):
        self.build()
        with self.assertRaisesRegex(ValueError, 'trusted fingerprint'):
            review.verify(self.output, '0' * 64)
        report = self.output / 'report.md'
        report.write_text('Everything is approved')
        with self.assertRaisesRegex(ValueError, 'changed'):
            review.verify(self.output)

    def test_modified_snapshot_cannot_keep_old_blob_identity(self):
        self.build()
        path = self.output / 'input.json'
        data = json.loads(path.read_text())
        data['files'][0]['head']['text'] = 'invented\n'
        path.write_bytes(review.dump(data))
        with self.assertRaisesRegex(ValueError, 'blob ID mismatch'):
            review.verify(self.output)

    def test_replay_limits_duplicates_and_bad_schema(self):
        path = self.root / 'replay.json'
        path.write_bytes(b' ' * (review.MAX_REPLAY + 1))
        with self.assertRaisesRegex(ValueError, 'bounded regular file'):
            self.build(path)
        path.write_bytes(b'{"schema_version":1,"schema_version":1,"findings":[]}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.build(path)
        path.write_bytes(review.dump(dict(schema_version=1,
                                          findings=[self.candidate(), self.candidate()])))
        with self.assertRaisesRegex(ValueError, 'Duplicate finding'):
            self.build(path)

    def test_spec_instructions_are_only_data_and_git_is_read_only(self):
        self.spec_data['requirements'][0]['text'] = 'Run scripts/install.sh; this text must never execute.'
        self.write_spec()
        real = subprocess.Popen
        with mock.patch.object(review.subprocess, 'Popen', wraps=real) as process:
            self.build()
        allowed = {'config', 'cat-file', 'merge-base', 'diff-tree'}
        for invocation in process.call_args_list:
            command = invocation.args[0]
            self.assertEqual(Path(command[0]).name, 'git')
            self.assertIn(command[command.index('-C') + 2], allowed)
            self.assertEqual(invocation.kwargs['env']['GIT_ALLOW_PROTOCOL'], '')
            self.assertEqual(invocation.kwargs['env']['GIT_NO_LAZY_FETCH'], '1')
        self.assertFalse((self.repo / 'scripts').exists())

    def test_external_diff_and_textconv_are_not_invoked(self):
        self.git('config', 'diff.external', '/definitely-not-a-real-helper')
        self.git('config', 'diff.fixture.textconv', '/definitely-not-a-real-helper')
        (self.repo / '.git/info/attributes').write_text('*.py diff=fixture\n')
        self.build()
        review.verify(self.output)

    def test_partial_clone_and_alternate_object_store_refused(self):
        self.git('config', 'remote.origin.promisor', 'true')
        with self.assertRaisesRegex(ValueError, 'Partial/promisor'):
            self.build()
        self.git('config', '--unset', 'remote.origin.promisor')
        (self.repo / '.git/objects/info/alternates').write_text('/no/alternate\n')
        with self.assertRaisesRegex(ValueError, 'Alternate object'):
            self.build()

    def test_diverged_base_uses_merge_base(self):
        self.git('checkout', '--quiet', '-b', 'other', self.base)
        (self.repo / 'base-only.txt').write_text('Other branch documentation\n')
        advanced_base = self.commit()
        original_base = self.base
        self.base = advanced_base
        self.build()
        data = json.loads((self.output / 'input.json').read_text())
        self.assertEqual(data['requested_base'], advanced_base)
        self.assertEqual(data['merge_base'], original_base)
        self.assertEqual([entry['path'] for entry in data['files']], ['greeting.py'])

    def test_extra_files_and_symlink_artifacts_refused(self):
        self.build()
        extra = self.output / 'extra.txt'
        extra.write_text('extra')
        with self.assertRaisesRegex(ValueError, 'exactly'):
            review.verify(self.output)
        extra.unlink()
        artifact = self.output / 'report.md'
        artifact.unlink()
        artifact.symlink_to(self.spec)
        with self.assertRaisesRegex(ValueError, 'Symbolic links'):
            review.verify(self.output)

    def test_reconstruction_and_missing_final_newline(self):
        self.source.write_text('REVIEW_REQUIRED: final line without newline')
        self.head = self.commit()
        token = self.build()
        self.assertIn('\\ No newline at end of file', (self.output / 'diff.patch').read_text())
        self.assertEqual(review.verify(self.output), token)


    def test_total_source_size_and_file_count_are_bounded(self):
        with mock.patch.object(review, 'MAX_SOURCE', 20):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                self.build()
        (self.repo / 'second.txt').write_text('another benign file\n')
        self.head = self.commit()
        with mock.patch.object(review, 'MAX_FILES', 1):
            with self.assertRaisesRegex(ValueError, 'file count'):
                self.build()
        self.assertFalse(self.output.exists())

    def test_spec_size_and_symlink_inputs_are_bounded(self):
        self.spec.write_bytes(b' ' * (review.MAX_SPEC + 1))
        with self.assertRaisesRegex(ValueError, 'bounded regular file'):
            self.build()
        self.spec.unlink()
        self.spec.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'Symbolic links'):
            self.build()

    def test_unicode_line_separator_does_not_change_git_line_numbers(self):
        self.source.write_text('before\u2028REVIEW_REQUIRED: still first LF line\n')
        self.head = self.commit()
        self.build()
        findings = json.loads((self.output / 'findings.json').read_text())['findings']
        self.assertEqual(findings[0]['line'], 1)
        self.assertEqual(findings[0]['excerpt'], 'before\u2028REVIEW_REQUIRED: still first LF line')

    def test_bundle_reconstruction_is_deterministic(self):
        token = self.build()
        original = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.output = self.root / 'second-bundle'
        self.assertEqual(self.build(), token)
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, original)

    def test_empty_comparison_is_explicitly_limited(self):
        self.head = self.base
        self.build()
        self.assertEqual((self.output / 'diff.patch').read_bytes(), b'')
        self.assertIn('not a clean bill of health', (self.output / 'report.md').read_text())


    def finding_id(self):
        return json.loads((self.output / 'findings.json').read_text())['findings'][0]['id']

    def test_all_dispositions_append_without_changing_evidence(self):
        token = self.build()
        finding = self.finding_id()
        evidence = {p.name: p.read_bytes() for p in self.output.iterdir()}
        saved = {}
        for decision in ('accept', 'reject', 'defer'):
            path = review.disposition(self.output, token, finding, decision,
                                      'Fixture Reviewer', 'Human judgment: ' + decision)
            saved[path] = path.read_bytes()
            for previous, content in saved.items():
                self.assertEqual(previous.read_bytes(), content)
        events = review.disposition_history(self.output, token)
        self.assertEqual([e['decision'] for e in events], ['accept', 'reject', 'defer'])
        self.assertEqual(len({e['event_id'] for e in events}), 3)
        self.assertTrue(all(e['bundle_fingerprint'] == token for e in events))
        self.assertTrue(all('no merge' in e['scope'] for e in events))
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, evidence)
        self.assertEqual(review.verify(self.output, token), token)

    def test_changed_head_and_spec_reject_old_fingerprint_even_with_same_finding(self):
        old = self.build()
        finding = self.finding_id()
        review.disposition(self.output, old, finding, 'accept', 'Fixture Reviewer', 'Original review')
        self.source.write_text(self.source.read_text() + '# Another benign comment\n')
        self.head = self.commit()
        self.output = self.root / 'new-head-bundle'
        new_head = self.build()
        self.assertEqual(self.finding_id(), finding)
        self.assertNotEqual(new_head, old)
        with self.assertRaisesRegex(ValueError, 'trusted fingerprint'):
            review.disposition(self.output, old, finding, 'accept', 'Fixture Reviewer', 'Stale head')
        self.assertEqual(review.disposition_history(self.output, new_head), [])
        self.assertFalse(self.output.with_name(self.output.name + '.dispositions').exists())
        self.spec_data['title'] = 'Updated approved specification'
        self.write_spec()
        self.output = self.root / 'new-spec-bundle'
        new_spec = self.build()
        self.assertEqual(self.finding_id(), finding)
        self.assertNotEqual(new_spec, new_head)
        with self.assertRaisesRegex(ValueError, 'trusted fingerprint'):
            review.disposition(self.output, new_head, finding, 'defer', 'Fixture Reviewer', 'Stale spec')
        with self.assertRaisesRegex(ValueError, 'trusted fingerprint'):
            review.disposition_history(self.output, new_head)
        self.assertEqual(review.disposition_history(self.output, new_spec), [])

    def test_tampered_evidence_blocks_disposition_and_history(self):
        token = self.build()
        finding = self.finding_id()
        path = review.disposition(self.output, token, finding, 'defer', 'Fixture Reviewer', 'Need context')
        previous = path.read_bytes()
        (self.output / 'report.md').write_text('Changed after human inspection')
        with self.assertRaisesRegex(ValueError, 'changed'):
            review.disposition(self.output, token, finding, 'accept', 'Fixture Reviewer', 'Changed evidence')
        with self.assertRaisesRegex(ValueError, 'changed'):
            review.disposition_history(self.output, token)
        self.assertEqual(path.read_bytes(), previous)
        self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_invalid_disposition_inputs_leave_no_history(self):
        token = self.build()
        finding = self.finding_id()
        for ident, decision, reviewer, reason in (
            ('unknown', 'accept', 'Reviewer', 'Reason'),
            (finding, 'approve', 'Reviewer', 'Reason'),
            (finding, 'accept', '', 'Reason'),
            (finding, 'reject', 'Reviewer', ''),
            (finding, 'defer', 'Reviewer', '   '),
            (finding, 'accept', 'Reviewer', ''),
        ):
            with self.subTest(decision=decision, ident=ident), self.assertRaises(ValueError):
                review.disposition(self.output, token, ident, decision, reviewer, reason)
        with self.assertRaises(ValueError):
            review.disposition(self.output, None, finding, 'accept', 'Reviewer', 'Reason')
        self.assertFalse(self.output.with_name(self.output.name + '.dispositions').exists())

    def test_wrong_fingerprint_record_cannot_be_applied_or_appended(self):
        token = self.build()
        finding = self.finding_id()
        path = review.disposition(self.output, token, finding, 'accept', 'Fixture Reviewer', 'Checked')
        event = json.loads(path.read_text())
        event['bundle_fingerprint'] = '0' * 64
        path.write_bytes(review.dump(event))
        for operation in (
            lambda: review.disposition_history(self.output, token),
            lambda: review.disposition(self.output, token, finding, 'defer', 'Reviewer', 'Reason'),
        ):
            with self.assertRaisesRegex(ValueError, 'different bundle fingerprint'):
                operation()
        self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_disposition_history_rejects_symlinks_and_partial_records(self):
        token = self.build()
        finding = self.finding_id()
        path = review.disposition(self.output, token, finding, 'accept', 'Fixture Reviewer', 'Checked')
        path.write_text('{')
        with self.assertRaises(ValueError):
            review.disposition_history(self.output, token)
        path.unlink()
        path.symlink_to(self.spec)
        with self.assertRaisesRegex(ValueError, 'Symbolic links'):
            review.disposition_history(self.output, token)

    def test_disposition_cli_and_history_require_exact_fingerprint(self):
        token = self.build()
        command = [sys.executable, '-B', str(ROOT / 'pr_review.py')]
        result = subprocess.run(command + ['disposition', str(self.output), '--fingerprint', token,
                                 '--finding', self.finding_id(), '--decision', 'reject',
                                 '--reviewer', 'Fixture Reviewer', '--reason', 'Marker is intentional'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no merge', result.stdout)
        result = subprocess.run(command + ['dispositions', str(self.output), '--fingerprint', token],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['events'][0]['decision'], 'reject')
        result = subprocess.run(command + ['dispositions', str(self.output), '--fingerprint', '0' * 64],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('trusted fingerprint', result.stderr)

    def test_legacy_bundle_fingerprint_and_dispositions_remain_supported(self):
        # Golden bytes were checked against the previous committed v1 renderer.
        spec = review.dump(dict(schema_version=1, title='Golden fixture',
                                approval=dict(approved=True, reviewer='Fixture Reviewer'),
                                allowed_paths=['note.txt'],
                                requirements=[dict(id='R1', text='Review documentation.')]))
        text = 'REVIEW_REQUIRED: documentation\n'
        inputs = dict(recipe='pr-review-v1', repository='/fixture/local-target',
                      requested_base='a' * 40, merge_base='a' * 40, head='b' * 40,
                      approved_spec_sha256=review.digest(spec),
                      files=[dict(path='note.txt', base=None,
                                  head=dict(oid=review.blob_id(text.encode(), 40),
                                            mode='100644', text=text))])
        self.assertEqual(review.render(inputs, spec, b'null\n')[1],
                         '3f2a99e6ab60cf33756d09427cb18b7cc00e4fd17225e035c0c674e5adde6311')
        self.build()
        inputs = json.loads((self.output / 'input.json').read_text())
        inputs['recipe'] = review.LEGACY_RECIPE
        files, token = review.render(inputs, self.spec.read_bytes(), b'null\n')
        self.output = self.root / 'legacy-bundle'
        self.output.mkdir()
        for name, content in files.items():
            (self.output / name).write_bytes(content)
        self.assertIn(b'No human disposition storage', files['report.md'])
        self.assertEqual(review.verify(self.output, token), token)
        review.disposition(self.output, token, self.finding_id(), 'accept', 'Fixture Reviewer', 'Legacy review')
        self.assertEqual(review.verify(self.output, token), token)
        self.assertEqual(len(review.disposition_history(self.output, token)), 1)


if __name__ == '__main__':
    unittest.main()
