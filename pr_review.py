"""Offline, read-only Git review bundles. No target code or model is executed."""
import argparse
import difflib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import threading
import uuid

LEGACY_RECIPE = 'pr-review-v1'
RECIPE = 'pr-review-v2'
DISPOSITION_SCOPE = 'finding disposition only; no merge, release or deployment approval'
MAX_EVENTS = 1000
MAX_FILES = 50
MAX_BLOB = 128 * 1024
MAX_SOURCE = 1024 * 1024
MAX_CHANGED_LINES = 2000
MAX_SPEC = 64 * 1024
MAX_REPLAY = 256 * 1024
MAX_ARTIFACT = 4 * 1024 * 1024
MAX_FINDINGS = 100
MARKER = 'REVIEW_REQUIRED'
FILES = ('input.json', 'spec.json', 'replay.json', 'diff.patch', 'findings.json', 'report.md', 'manifest.json')
LEGACY_LIMITATIONS = [
    'Deterministic marker/replay demonstration; no semantic defect detection or quality claim.',
    'Citation validity proves location and exact text, not the truth of a finding.',
    'No target code, tests, hooks, CI, external models or network calls are executed.',
    'Only bounded UTF-8 LF text in ordinary local Git repositories is supported; renames are delete/add.',
    'Only changed lines are eligible citations; binary files, symlinks and submodules are refused.',
    'Specification approval is self-attested; reviewer identity is not authenticated.',
    'Hashes are not signatures. Retain a trusted fingerprint separately to detect complete bundle replacement.',
    'No human disposition storage or merge/deployment approval is implemented. Human review remains required.',
]

LIMITATIONS = LEGACY_LIMITATIONS[:-1] + [
    'Human dispositions are separate local sidecar records, self-attested and bound to this exact fingerprint; never merge/deployment approval.',
]


def dump(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field: ' + key)
        result[key] = value
    return result


def parse(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda value: fail('Non-finite JSON value'))


def fail(message):
    raise ValueError(message)


def shape(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        fail('Invalid ' + label + ' fields')


def short(value, label, maximum=500):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or not value.isprintable():
        fail('Invalid ' + label)
    return value


def safe_path(value):
    short(value, 'source path', 240)
    if not re.fullmatch(r'[A-Za-z0-9_. /-]+', value) or value.startswith('/'):
        fail('Unsafe source path')
    if any(part in ('', '.', '..') or part.casefold() == '.git' for part in value.split('/')):
        fail('Unsafe source path')
    if str(PurePosixPath(value)) != value:
        fail('Non-canonical source path')
    return value


def ordinary_path(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink():
            fail('Symbolic links are not accepted: ' + str(item))
    return path


def read_file(path, limit):
    path = ordinary_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            fail('Input is not a bounded regular file: ' + str(path))
        data = handle.read(limit + 1)
    if len(data) > limit:
        fail('Input exceeds size limit')
    return data


def oid(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', value):
        fail(label + ' must be a full lowercase Git object ID')
    return value


def sha256(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        fail('Expected lowercase SHA-256')
    return value


def git(repo, *args, limit=65536, allow_missing=False):
    # Never inherit Git overrides, credentials, config, replacement objects or network helpers.
    executable = shutil.which('git')
    if not executable:
        fail('Git is required')
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_ALLOW_PROTOCOL='',
               LC_ALL='C')
    command = [executable, '--no-optional-locks', '-c', 'core.hooksPath=' + os.devnull,
               '-c', 'core.fsmonitor=false', '-c', 'core.attributesFile=' + os.devnull,
               '-c', 'diff.external=', '-c', 'core.pager=cat', '-C', str(repo), *args]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env) as process:
        timer = threading.Timer(10, process.kill)
        timer.start()
        try:
            data = process.stdout.read(limit + 1)
            if len(data) > limit:
                process.kill()
                process.wait()
                fail('Git output exceeds size limit')
            status = process.wait()
        finally:
            timer.cancel()
        if status and not (allow_missing and status == 1):
            fail('Local Git read failed or timed out (' + args[0] + ')')
    return b'' if allow_missing and status == 1 else data


def spec_value(raw, approved_hash):
    if len(raw) > MAX_SPEC or digest(raw) != sha256(approved_hash):
        fail('Specification does not match the approved SHA-256 or exceeds limit')
    spec = parse(raw)
    shape(spec, ('schema_version', 'title', 'approval', 'allowed_paths', 'requirements'), 'specification')
    if type(spec['schema_version']) is not int or spec['schema_version'] != 1:
        fail('Unsupported specification version')
    short(spec['title'], 'specification title')
    shape(spec['approval'], ('approved', 'reviewer'), 'approval')
    if spec['approval']['approved'] is not True:
        fail('Specification must be explicitly approved')
    short(spec['approval']['reviewer'], 'approval reviewer', 160)
    paths = spec['allowed_paths']
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_FILES:
        fail('Specification needs 1-50 exact allowed paths')
    if len(set(safe_path(path) for path in paths)) != len(paths):
        fail('Duplicate allowed path')
    requirements = spec['requirements']
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= 50:
        fail('Specification needs 1-50 requirements')
    seen = set()
    for requirement in requirements:
        shape(requirement, ('id', 'text'), 'requirement')
        ident = short(requirement['id'], 'requirement ID', 80)
        short(requirement['text'], 'requirement text', 2000)
        if ident in seen:
            fail('Duplicate requirement ID')
        seen.add(ident)
    return spec


def source_text(value):
    if not isinstance(value, str):
        fail('Source must be text')
    data = value.encode('utf-8')
    if len(data) > MAX_BLOB or any(ord(c) < 32 and c not in '\n\t' for c in value) or '\x7f' in value:
        fail('Unsupported or oversized source: require UTF-8 LF text without control characters')
    return data


def blob_id(data, length):
    header = b'blob ' + str(len(data)).encode('ascii') + b'\0'
    return hashlib.new('sha1' if length == 40 else 'sha256', header + data).hexdigest()


def snapshot(repo, base, head, approved_hash):
    repo = ordinary_path(repo)
    if not repo.is_dir() or not (repo / '.git').is_dir() or (repo / '.git').is_symlink():
        fail('Require an ordinary local Git checkout with a .git directory')
    config = git(repo, 'config', '--local', '--get-regexp',
                 r'^(extensions\.partialclone|remote\..*\.promisor)$', allow_missing=True)
    if config:
        fail('Partial/promisor clones are unsupported; no object fetching is permitted')
    for name in ('alternates', 'http-alternates'):
        if (repo / '.git/objects/info' / name).exists():
            fail('Alternate object stores are unsupported')
    base, head = oid(base, 'Base'), oid(head, 'Head')
    if len(base) != len(head):
        fail('Mismatched Git object formats')
    for revision in (base, head):
        if git(repo, 'cat-file', '-t', revision).strip() != b'commit':
            fail('Base and head must identify commits directly')
    ancestors = git(repo, 'merge-base', '--all', base, head).decode('ascii').splitlines()
    if len(ancestors) != 1:
        fail('Require one unambiguous merge base')
    merge_base = oid(ancestors[0], 'Merge base')
    raw = git(repo, 'diff-tree', '--no-commit-id', '--raw', '-z', '-r', '--no-renames',
              '--no-ext-diff', '--no-textconv', '--no-abbrev', merge_base, head, '--')
    parts = raw.split(b'\0')
    if parts[-1] != b'' or (len(parts) - 1) % 2:
        fail('Malformed Git change list')
    if (len(parts) - 1) // 2 > MAX_FILES:
        fail('Changed file count exceeds limit')
    files = []
    total = 0
    for index in range(0, len(parts) - 1, 2):
        metadata = parts[index].decode('ascii').split()
        if len(metadata) != 5 or not metadata[0].startswith(':'):
            fail('Unsupported Git change entry')
        old_mode, new_mode, old_oid, new_oid, status_code = metadata
        old_mode = old_mode[1:]
        if status_code not in ('A', 'D', 'M', 'T'):
            fail('Unsupported change type')
        path = safe_path(parts[index + 1].decode('utf-8'))
        entry = {'path': path}
        for side, mode, object_id in (('base', old_mode, old_oid), ('head', new_mode, new_oid)):
            if mode == '000000':
                entry[side] = None
                continue
            if mode not in ('100644', '100755'):
                fail('Unsupported file mode for ' + path + ': ' + mode)
            oid(object_id, 'Blob')
            size = int(git(repo, 'cat-file', '-s', object_id).strip())
            if size > MAX_BLOB or total + size > MAX_SOURCE:
                fail('Source byte limit exceeded')
            data = git(repo, 'cat-file', 'blob', object_id, limit=MAX_BLOB)
            total += len(data)
            text = data.decode('utf-8')
            source_text(text)
            entry[side] = {'oid': object_id, 'mode': mode, 'text': text}
        files.append(entry)
    return {'recipe': RECIPE, 'repository': str(repo), 'requested_base': base,
            'merge_base': merge_base, 'head': head, 'approved_spec_sha256': approved_hash,
            'files': files}


def diff_and_lines(inputs, spec):
    shape(inputs, ('recipe', 'repository', 'requested_base', 'merge_base', 'head',
                   'approved_spec_sha256', 'files'), 'review input')
    if inputs['recipe'] not in (RECIPE, LEGACY_RECIPE):
        fail('Unsupported recipe')
    short(inputs['repository'], 'repository identity', 4096)
    revisions = [oid(inputs[key], key) for key in ('requested_base', 'merge_base', 'head')]
    if len({len(value) for value in revisions}) != 1:
        fail('Mismatched object formats')
    files = inputs['files']
    if not isinstance(files, list) or len(files) > MAX_FILES:
        fail('Changed file count exceeds limit')
    seen, anchors, chunks = set(), {}, []
    total = 0
    for entry in files:
        shape(entry, ('path', 'base', 'head'), 'source entry')
        path = safe_path(entry['path'])
        if path in seen or path not in spec['allowed_paths']:
            fail('Duplicate or out-of-scope path: ' + path)
        seen.add(path)
        if entry['base'] is None and entry['head'] is None:
            fail('Empty source entry')
        lines = {}
        for side in ('base', 'head'):
            blob = entry[side]
            if blob is None:
                lines[side] = []
                continue
            shape(blob, ('oid', 'mode', 'text'), 'blob')
            if blob['mode'] not in ('100644', '100755'):
                fail('Unsupported file mode')
            object_id = oid(blob['oid'], 'Blob')
            data = source_text(blob['text'])
            total += len(data)
            if total > MAX_SOURCE:
                fail('Source byte limit exceeded')
            if len(object_id) != len(revisions[0]) or blob_id(data, len(object_id)) != object_id:
                fail('Source blob ID mismatch')
            pieces = blob['text'].split('\n')
            lines[side] = [piece + '\n' for piece in pieces[:-1]]
            if pieces[-1]:
                lines[side].append(pieces[-1])
        before, after = lines['base'], lines['head']
        # autojunk=True bounds common repetitive input; citations use these exact same opcodes.
        matcher = difflib.SequenceMatcher(None, before, after)
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag == 'equal':
                continue
            for side, start, end in (('base', a, b), ('head', c, d)):
                for number in range(start, end):
                    anchors[(path, side, number + 1)] = lines[side][number].removesuffix('\n')
                    if len(anchors) > MAX_CHANGED_LINES:
                        fail('Changed line count exceeds limit')
        fromfile = 'a/' + path if entry['base'] else '/dev/null'
        tofile = 'b/' + path if entry['head'] else '/dev/null'
        for line in difflib.unified_diff(before, after, fromfile=fromfile, tofile=tofile, n=3):
            chunks.append(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n')
    return ''.join(chunks).encode('utf-8'), anchors


def reviewer_findings(replay, anchors, recipe=RECIPE):
    if replay is None:
        candidates = [dict(path=path, side=side, line=line, excerpt=excerpt,
                           message='Added line contains the REVIEW_REQUIRED marker; a human should inspect it.')
                      for (path, side, line), excerpt in sorted(anchors.items())
                      if side == 'head' and MARKER in excerpt]
        reviewer = 'deterministic-marker-v1 (benign marker check only)'
    else:
        shape(replay, ('schema_version', 'findings'), 'replay')
        if type(replay['schema_version']) is not int or replay['schema_version'] != 1:
            fail('Unsupported replay version')
        candidates = replay['findings']
        reviewer = 'deterministic-replay-v1 (operator-supplied claims; semantics unverified)'
    if not isinstance(candidates, list) or len(candidates) > MAX_FINDINGS:
        fail('Finding count exceeds limit')
    findings, seen = [], set()
    for candidate in candidates:
        shape(candidate, ('path', 'side', 'line', 'excerpt', 'message'), 'finding')
        path = safe_path(candidate['path'])
        side, line = candidate['side'], candidate['line']
        if side not in ('base', 'head') or type(line) is not int or line < 1:
            fail('Invalid citation coordinate')
        excerpt = candidate['excerpt']
        if not isinstance(excerpt, str) or len(excerpt.encode('utf-8')) > MAX_BLOB:
            fail('Invalid citation excerpt')
        key = path, side, line
        if key not in anchors or anchors[key] != excerpt:
            fail('Citation does not match a changed line in the pinned diff')
        short(candidate['message'], 'finding message', 2000)
        if key in seen:
            fail('Duplicate finding anchor')
        seen.add(key)
        findings.append(dict(candidate, id='F-' + digest(dump(candidate))[:16],
                             validation='citation-valid; semantic truth unverified', severity='informational'))
    return {'reviewer': reviewer, 'findings': findings, 'decision': 'HUMAN REVIEW REQUIRED',
            'limitations': LEGACY_LIMITATIONS if recipe == LEGACY_RECIPE else LIMITATIONS}


def markdown(text):
    return ''.join('\\' + c if c in '\\`*_{}[]()#+-.!|<>&' else c for c in text)


def render(inputs, spec_raw, replay_raw):
    if len(replay_raw) > MAX_REPLAY:
        fail('Replay exceeds size limit')
    if not isinstance(inputs, dict) or 'approved_spec_sha256' not in inputs:
        fail('Missing approved spec fingerprint')
    spec = spec_value(spec_raw, inputs['approved_spec_sha256'])
    patch, anchors = diff_and_lines(inputs, spec)
    review = reviewer_findings(parse(replay_raw), anchors, inputs['recipe'])
    report = ['# Local PR review', '', '**HUMAN REVIEW REQUIRED**', '',
              'Reviewer: ' + review['reviewer'], '',
              'Requested base: ' + inputs['requested_base'],
              'Comparison base (merge base): ' + inputs['merge_base'],
              'Head: ' + inputs['head'], '',
              'Spec: ' + markdown(spec['title']),
              'Approved spec SHA-256: ' + inputs['approved_spec_sha256'], '',
              'Files captured: ' + str(len(inputs['files'])),
              'Changed lines eligible for citation: ' + str(len(anchors)), '',
              '## Findings', '']
    for finding in review['findings']:
        report.extend([finding['id'] + ': ' + markdown(finding['message']),
                       'Citation: ' + markdown(finding['path']) + ' (' + finding['side'] +
                       ':' + str(finding['line']) + ')',
                       'Excerpt: ' + markdown(finding['excerpt']), ''])
    if not review['findings']:
        report.extend(['No findings from this limited reviewer. This is not a clean bill of health.', ''])
    report.extend(['## Limitations', '', *['- ' + item for item in review['limitations']], ''])
    files = {'input.json': dump(inputs), 'spec.json': spec_raw, 'replay.json': replay_raw,
             'diff.patch': patch, 'findings.json': dump(review),
             'report.md': '\n'.join(report).encode('utf-8')}
    if any(len(value) > MAX_ARTIFACT for value in files.values()):
        fail('Rendered artifact exceeds size limit')
    manifest = {'recipe': inputs['recipe'], 'sha256': {key: digest(value) for key, value in files.items()}}
    files['manifest.json'] = dump(manifest)
    fingerprint = digest(files['manifest.json'])
    return files, fingerprint


def build(repo, base, head, spec_path, approved_hash, output, replay_path=None):
    repo, output = ordinary_path(repo), ordinary_path(output)
    if output == repo or repo in output.parents:
        fail('Output must be outside the target repository')
    if output.exists():
        fail('Output already exists; nothing was overwritten')
    spec_raw = read_file(spec_path, MAX_SPEC)
    spec_value(spec_raw, approved_hash)
    replay_raw = read_file(replay_path, MAX_REPLAY) if replay_path else b'null\n'
    inputs = snapshot(repo, base, head, approved_hash)
    files, fingerprint = render(inputs, spec_raw, replay_raw)
    output.mkdir()  # Parent must already exist; never modify a target directory.
    for name, data in files.items():
        with (output / name).open('xb') as handle:
            handle.write(data)
    return fingerprint


def load_verified(output, expected_fingerprint=None):
    output = ordinary_path(output)
    if not output.is_dir() or set(item.name for item in output.iterdir()) != set(FILES):
        fail('Bundle must contain exactly the expected artifact files')
    actual = {name: read_file(output / name, MAX_ARTIFACT) for name in FILES}
    expected, fingerprint = render(parse(actual['input.json']), actual['spec.json'], actual['replay.json'])
    if actual != expected:
        fail('Bundle content changed or failed deterministic reconstruction')
    if expected_fingerprint is not None and sha256(expected_fingerprint) != fingerprint:
        fail('Bundle does not match the trusted fingerprint')
    return actual, fingerprint


def verify(output, expected_fingerprint=None):
    return load_verified(output, expected_fingerprint)[1]


def history_path(bundle, fingerprint, inputs):
    bundle = ordinary_path(bundle)
    folder = ordinary_path(bundle.with_name(bundle.name + '.dispositions') / fingerprint)
    target = Path(inputs['repository']).resolve()
    if folder == target or target in folder.parents:
        fail('Disposition storage must be outside the target repository')
    return folder


def validate_event(event, fingerprint, findings):
    shape(event, ('schema_version', 'event_id', 'bundle_fingerprint', 'finding_id',
                  'decision', 'reviewer', 'reason', 'recorded_utc', 'scope'), 'disposition')
    if type(event['schema_version']) is not int or event['schema_version'] != 1:
        fail('Unsupported disposition version')
    if not isinstance(event['event_id'], str) or not re.fullmatch('[0-9a-f]{32}', event['event_id']):
        fail('Invalid disposition event ID')
    if event['bundle_fingerprint'] != fingerprint:
        fail('Disposition belongs to a different bundle fingerprint')
    short(event['finding_id'], 'finding ID', 80)
    if event['finding_id'] not in findings:
        fail('Unknown finding ID')
    if event['decision'] not in ('accept', 'reject', 'defer'):
        fail('Decision must be accept, reject or defer')
    short(event['reviewer'], 'reviewer', 160)
    short(event['reason'], 'disposition reason', 2000)
    short(event['recorded_utc'], 'recorded UTC time', 80)
    try:
        timestamp = dt.datetime.fromisoformat(event['recorded_utc'])
    except ValueError:
        fail('Invalid disposition timestamp')
    if timestamp.tzinfo is None or timestamp.utcoffset() != dt.timedelta(0):
        fail('Disposition timestamp must use UTC')
    if event['scope'] != DISPOSITION_SCOPE:
        fail('Invalid disposition scope')


def read_history(folder, fingerprint, findings):
    if not folder.exists():
        return []
    if not folder.is_dir():
        fail('Disposition history must be a directory')
    events = []
    for path in folder.iterdir():
        if len(events) >= MAX_EVENTS:
            fail('Disposition event limit exceeded')
        if not re.fullmatch(r'[0-9a-f]{32}\.json', path.name):
            fail('Unexpected disposition history file')
        event = parse(read_file(path, 16 * 1024))
        validate_event(event, fingerprint, findings)
        if path.stem != event['event_id']:
            fail('Disposition event filename mismatch')
        events.append(event)
    return sorted(events, key=lambda event: (event['recorded_utc'], event['event_id']))


def disposition_history(bundle, fingerprint):
    sha256(fingerprint)  # Unlike verify, a retained fingerprint is mandatory here.
    actual, current = load_verified(bundle, fingerprint)
    inputs = parse(actual['input.json'])
    findings = {item['id'] for item in parse(actual['findings.json'])['findings']}
    folder = history_path(bundle, current, inputs)
    return read_history(folder, current, findings)


def disposition(bundle, fingerprint, finding_id, decision, reviewer, reason):
    sha256(fingerprint)
    actual, current = load_verified(bundle, fingerprint)
    inputs = parse(actual['input.json'])
    findings = {item['id'] for item in parse(actual['findings.json'])['findings']}
    folder = history_path(bundle, current, inputs)
    event = dict(schema_version=1, event_id=uuid.uuid4().hex,
                 bundle_fingerprint=current, finding_id=finding_id, decision=decision,
                 reviewer=reviewer, reason=reason,
                 recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                 scope=DISPOSITION_SCOPE)
    validate_event(event, current, findings)
    if len(read_history(folder, current, findings)) >= MAX_EVENTS:
        fail('Disposition event limit reached')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (event['event_id'] + '.json')
    with path.open('xb') as handle:
        handle.write(dump(event))
        handle.flush()
        os.fsync(handle.fileno())
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('review', help='Read pinned local commits and export a review bundle')
    for flag in ('repo', 'spec', 'output'):
        create.add_argument('--' + flag, required=True, type=Path)
    for flag in ('base', 'head', 'approved-spec-sha256'):
        create.add_argument('--' + flag, required=True)
    create.add_argument('--replay', type=Path, help='Optional bounded JSON finding replay (not a model)')
    check = sub.add_parser('verify', help='Verify a self-contained bundle without accessing its repository')
    check.add_argument('bundle', type=Path)
    check.add_argument('--fingerprint', help='Compare with a separately retained trusted fingerprint')
    record = sub.add_parser('disposition', help='Append a human disposition for exact reviewed evidence')
    record.add_argument('bundle', type=Path)
    record.add_argument('--fingerprint', required=True)
    record.add_argument('--finding', required=True)
    record.add_argument('--decision', choices=('accept', 'reject', 'defer'), required=True)
    record.add_argument('--reviewer', required=True)
    record.add_argument('--reason', required=True)
    history = sub.add_parser('dispositions', help='Read history for an exact bundle fingerprint')
    history.add_argument('bundle', type=Path)
    history.add_argument('--fingerprint', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'disposition':
            path = disposition(args.bundle, args.fingerprint, args.finding, args.decision,
                               args.reviewer, args.reason)
            print('Local human disposition recorded: ' + str(path))
            print(DISPOSITION_SCOPE)
            return
        if args.command == 'dispositions':
            events = disposition_history(args.bundle, args.fingerprint)
            print(dump(dict(bundle_fingerprint=args.fingerprint, events=events,
                            scope=DISPOSITION_SCOPE)).decode('utf-8'), end='')
            return
        if args.command == 'review':
            result = build(args.repo, args.base, args.head, args.spec,
                           args.approved_spec_sha256, args.output, args.replay)
        else:
            result = verify(args.bundle, args.fingerprint)
        print('HUMAN REVIEW REQUIRED; deterministic evidence only')
        print('Bundle fingerprint: ' + result)
    except (ValueError, OSError, UnicodeError, RecursionError) as error:
        parser.exit(2, 'error: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
