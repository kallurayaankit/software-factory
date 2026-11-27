# Feature: offline, read-only PR review bundle

## 1. Objective & Context
Build a dependency-free Python CLI that reads a local Git merge-base/head comparison and a version-pinned, self-attested approved specification. Export immutable evidence and citation-validated findings from a deterministic, explicitly limited reviewer. Keep the release-readiness CLI unchanged.

Target paths: `pr_review.py`, `test_pr_review.py`, `README.md`, `docs/PR_REVIEW_SPEC.md`, `docs/PR_REVIEW.md`, `docs/EVALUATION.md`, `examples/pr-review-spec.json`, `.gitignore`, `STARTER_SNAPSHOT.json`.
Reference patterns: `factory.py` JSON canonicalization, exclusive output creation and clear error exits; `test_factory.py` disposable fixture repositories.

## 2. Non-goals
No target-code execution, dependencies, network/model calls, GitHub integration, publication, target writes, deployment, merge, offensive workflows, semantic-quality claims, authenticated approvals, or modification of the starter/hosted site. No changes to `factory.py` or `dist/`.

## 3. Requirements
- Accept only local ordinary Git repositories, explicit base/head full commit IDs, an approved-spec SHA-256, and a bounded structured spec.
- Compute the unique merge base and read committed blobs; exclude dirty worktrees.
- Reject unsupported modes, unsafe paths, invalid encodings, NUL/CR text, oversized inputs, ambiguous ancestry, missing objects, and partial clones.
- Disable Git replacement objects, external diff/textconv behavior, lazy fetch and interactive prompts. Never invoke repository scripts or hooks.
- Use a benign literal `REVIEW_REQUIRED` marker check on added lines, or replay supplied structured findings; label both as deterministic and not semantic review.
- Validate every citation's path, side, changed-line number and exact excerpt before exporting.
- Export a self-contained local bundle outside the target with source snapshots, diff, approved spec, reviewer input/output, hashes, revisions, coverage and limitations. Never overwrite.
- Verify hashes and deterministically reconstruct diff/findings from bounded bundle inputs; offer a trusted fingerprint comparison.
- No approval/disposition implementation in this slice; always require human review.

## 4. Acceptance and verification
Run `python3 -m unittest -v` and `node --test tests/demo.test.mjs` in this checkout. Tests must cover a real benign Git change, fabricated citations, dirty worktree exclusion, deleted-line evidence, invalid approvals, unsafe/oversized source and replay, bundle tampering, stale fingerprint and output isolation. No target code is executed by review; tests may create and commit synthetic fixture data in disposable repositories. Existing tests must pass. Document measured test results separately from prospective evaluation targets.
