# Offline PR review slice

`pr_review.py` is a separate dependency-free Python 3.10+ CLI. It requires local Git and a POSIX filesystem (tested on Linux). The existing `factory.py` release-readiness commands are unchanged.

This is a deterministic evidence pipeline, not an AI code reviewer. Its default reviewer reports an added line containing the literal `REVIEW_REQUIRED`. That is a benign request for human inspection, not a bug or vulnerability assertion. An optional replay accepts operator-supplied findings and checks their citations; it does not establish their semantic truth. Neither mode calls a model, executes target code, changes the target, or contacts a service.

## Inputs and approval

The target must be an ordinary local checkout with a `.git` directory. Linked worktrees, bare repositories, partial/promisor clones and alternate object stores are not supported. Use a repository with locally present objects. Base and head must be full lowercase commit IDs, not branch names, short IDs or revision expressions. The review compares the unique merge base of those commits with head, as a PR-style comparison. Dirty and untracked working-tree files are never ingested.

Copy `examples/pr-review-spec.json` and fill every field. `allowed_paths` contains exact paths, not globs. Requirements are numbered explanatory text, never commands. `approval.approved` must be the Boolean `true` and `approval.reviewer` must be a nonempty name. This is self-attestation, not authenticated approval. Read and approve the exact bytes before supplying their SHA-256 with `--approved-spec-sha256`; any byte change requires a new approved hash.

## Disposable benign example

From this project's root, the following script creates synthetic commits and a bundle in a fresh temporary directory. Git commits here are fixture setup; the review CLI itself never creates commits or executes the target. The script prints the retained output location.

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, subprocess, sys, tempfile
factory_root = Path.cwd()
fixture_root = Path(tempfile.mkdtemp(prefix='factory-review-demo-'))
repo = fixture_root / 'target'
repo.mkdir()
def git(*args):
    return subprocess.check_output([
        'git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
        '-c', 'user.name=Synthetic Reviewer',
        '-c', 'user.email=fixture@example.invalid', '-C', str(repo), *args
    ], text=True).strip()
git('init', '--quiet')
source = repo / 'greeting.py'
source.write_text('def greeting():\n    return "hello"\n')
git('add', 'greeting.py')
git('commit', '--quiet', '-m', 'Synthetic base')
base = git('rev-parse', 'HEAD')
source.write_text('# REVIEW_REQUIRED: clarify greeting wording\ndef greeting():\n    return "hello"\n')
git('add', 'greeting.py')
git('commit', '--quiet', '-m', 'Benign documentation change')
head = git('rev-parse', 'HEAD')
spec = factory_root / 'examples/pr-review-spec.json'
approved_hash = hashlib.sha256(spec.read_bytes()).hexdigest()
bundle = fixture_root / 'review-bundle'
subprocess.run([
    sys.executable, str(factory_root / 'pr_review.py'), 'review',
    '--repo', str(repo), '--base', base, '--head', head,
    '--spec', str(spec), '--approved-spec-sha256', approved_hash,
    '--output', str(bundle)
], check=True)
subprocess.run([sys.executable, str(factory_root / 'pr_review.py'), 'verify', str(bundle)], check=True)
print('Retained synthetic demo:', fixture_root)
PY
```

The example spec is already self-attested for synthetic data only. For a real authorized local change, record the reviewed spec hash independently rather than automatically accepting a changed spec.

Retain the printed bundle fingerprint separately. Later verify against it:

```text
python3 pr_review.py verify /path/to/review-bundle --fingerprint RETAINED_SHA256
```

Verification is self-contained: it does not open the original repository or call Git. It validates blob hashes, reconstructs the diff, revalidates citations, and reproduces every expected artifact. Without a separately trusted fingerprint, it proves internal consistency only; an actor able to replace all files can create another internally consistent bundle.

## Replay schema

Pass `--replay /path/to/replay.json` to use this strict schema:

```json
{
  "schema_version": 1,
  "findings": [
    {
      "path": "greeting.py",
      "side": "head",
      "line": 1,
      "excerpt": "# REVIEW_REQUIRED: clarify greeting wording",
      "message": "Inspect the documentation marker."
    }
  ]
}
```

Every citation must match a changed line and exact excerpt. Lines are 1-based LF-delimited lines; excerpts omit only the final LF. `base` denotes the comparison's merge base, not necessarily the requested base tip. Deletions may cite `base`; additions may cite `head`. Unchanged context lines cannot be cited. Unknown paths, mismatched text, invalid coordinates, duplicate anchors and unknown schema fields fail the entire run before export. Messages are operator-supplied claims and are escaped in the Markdown report. All findings are informational, with semantic truth explicitly unverified. Replay does not assess spec compliance.

## Evidence contract

A successful run creates exactly seven files in a new output directory outside the target:

- `input.json`: recipe version, local repository identity, requested base, merge base, head, approved spec hash, changed paths, modes, blob IDs and before/after source snapshots.
- `spec.json`: the exact approved specification bytes.
- `replay.json`: exact replay bytes, or JSON `null` for marker mode.
- `diff.patch`: a unified diff reconstructed from committed blobs. Rename detection is disabled; renames appear as delete/add. It is an evidence view, not a patch application API. Mode-only and empty-file changes remain visible in the snapshot but have no textual changed-line citations.
- `findings.json`: labeled reviewer, validated locations, finding IDs, informational severity, limitations and `HUMAN REVIEW REQUIRED`.
- `report.md`: readable revisions, spec, coverage counts, findings and limitations.
- `manifest.json`: SHA-256 digests of the preceding six files. The printed fingerprint is the SHA-256 of this canonical manifest.

The diff uses Python's standard-library line matcher, so hunk choices can differ from Git's default diff algorithm. Both generation and citation validation use the same committed content and matching rules. Matching a citation does not prove a reported defect.

Output is never overwritten. Invalid inputs do not create an output directory. A filesystem failure during writing can leave a partial directory; verification refuses it, and a new output path is required. Evidence files are not OS-immutable or signed. Always retain the trusted fingerprint elsewhere.

## Boundaries and limits

| Input | Limit / policy |
| --- | --- |
| Changed files | 50 |
| Single source blob | 128 KiB |
| Total before/after source bytes | 1 MiB |
| Added plus removed lines | 2,000 |
| Specification | 64 KiB, 1–50 exact allowed paths and 1–50 requirements |
| Replay | 256 KiB, at most 100 findings |
| Exported or read artifact | 4 MiB per file |
| Git subprocess | 10-second timeout and bounded captured output |
| Source names | Relative ASCII letters/digits, spaces, `_`, `-`, `.`, `/`; no empty, dot, dot-dot or `.git` path components |
| File kinds | Ordinary UTF-8 LF text blobs with Git mode 100644 or 100755; no binary, CRLF, symlink or submodule blobs |
| External input paths | Ordinary bounded regular files; symlink paths and special files refused |

An unsupported or oversized input is a hard failure (exit 2), not a partial success or clean verdict. Exit 0 means a bundle was created or internally verified, never that a change is safe to merge. Requiring full before/after blobs deliberately refuses large files even for small changes.

Git reads use explicit object IDs and read-only commands: `config`, `cat-file`, `merge-base`, `diff-tree`. Replacement objects, external diff/textconv, hooks, filesystem monitor helpers, optional locks, lazy fetching, allowed network protocols and inherited Git environment overrides are disabled. No checkout, status, fetch, filter, target test or dependency installation is part of review. The implementation assumes a trusted local Git executable and a stable local filesystem; it is not a sandbox for a malicious Git installation or concurrent filesystem attacker.

The bundle contains source excerpts/full changed-file snapshots, the local repository path, and the self-attested reviewer name. Keep it local and handle it as source material. No automatic redaction, encryption, access control or retention service is implemented.

## Verification and next steps

```text
python3 -m unittest -v
node --test tests/demo.test.mjs
```

The Python suite includes a benign real Git comparison, fabricated citation rejection, dirty-worktree exclusion, deleted-line replay, diverged merge-base handling, approved-spec mismatch, unsupported/oversized inputs, target-output isolation, deterministic reconstruction and tampering. The original release-readiness tests remain intact.

Not yet implemented: semantic/model review, independent semantic verification, CI provenance, authenticated approvals, browser integration, GitHub ingestion/comments, multi-user persistence or parity with other reviewers. See `EVALUATION.md` for prospective quality gates and the narrow results actually measured.


## Human accept/reject/defer dispositions

Read the report and retain its exact fingerprint before recording a decision. Use a finding ID from `findings.json`:

```text
python3 pr_review.py disposition /path/to/review-bundle --fingerprint RETAINED_SHA256 --finding F_FINDING_ID --decision accept --reviewer "Reviewer name" --reason "I checked the cited change and agree with this finding."
python3 pr_review.py dispositions /path/to/review-bundle --fingerprint RETAINED_SHA256
```

Replace `F_FINDING_ID` with the complete ID, including its `F-` prefix. The decision is `accept`, `reject`, or `defer`. Every decision requires a nonempty reviewer and reason. Accept means the human considers the finding valid; reject means they disagree; defer means it remains unresolved. None approves the PR, merge, release or deployment. Recording a disposition does not make the deterministic finding semantically proven.

Each call reconstructs and verifies the bundle against the required fingerprint and checks the finding exists. It then creates one exclusive JSON event under:

```text
/path/to/review-bundle.dispositions/EXACT_FINGERPRINT/EVENT_ID.json
```

Events contain schema version, random event ID, exact fingerprint, finding ID, decision, reviewer, reason, UTC timestamp and restricted scope. The CLI never overwrites events or changes evidence. To reconsider a decision, append another event with a reason. `dispositions` validates and returns all events for that exact fingerprint in timestamp/event-ID order. It does not elect an authoritative final reviewer or calculate merge readiness.

Changing a head revision, spec, source snapshot, finding or other evidence requires a new bundle and fingerprint. A stale fingerprint fails even if the finding ID happens to remain identical. History is partitioned by fingerprint and never transfers automatically. The history command also refuses tampered evidence, malformed records and records carrying a different fingerprint. An unchanged historical bundle remains reviewable; the tool does not monitor whether an external branch has advanced.

New bundles use `pr-review-v2` to describe this feature accurately. Previously exported `pr-review-v1` bundles retain their original rendered text and fingerprints, including their historical limitation statement; they can also receive sidecar dispositions without rewriting their evidence.

Reviewers and timestamps are self-attested. The sidecar is local append-only behavior enforced by the CLI, not authenticated or tamper-proof storage: a filesystem owner can alter or delete records, and structural validation cannot detect all such changes. No network or target-code execution is involved. The supported operating model is a trusted local filesystem, not a concurrent hostile writer. At most 1,000 events per fingerprint and 16 KiB per event are read. A failed/interrupted write can leave a partial event; reads and further appends fail closed until it is inspected and repaired manually. No previous event is silently discarded.
