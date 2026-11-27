# Software Factory v0.1

A small, offline prototype of a software delivery workflow. The first recipe turns a structured brief into a release-readiness report and a review bundle. It verifies that the bundle matches the recipe and records a human's approval for the exact version they reviewed.

It runs one fixed recipe. It does not write general-purpose code, run a real project's checks, authenticate the reviewer, or touch a repository or deployment. Check statuses are fictional in the samples and otherwise supplied by the operator. The hashes detect changes relative to a reviewed copy; they are not digital signatures.

## Windows quickstart (PowerShell)

Extract the ZIP, open its folder in File Explorer, type `powershell` in the address bar and press Enter. Use Python 3.10+; if `py -3` is unavailable but Python is on your PATH, use `python` instead. No packages or credentials are needed.

```powershell
py -3 -m unittest -v
py -3 factory.py build examples/ready.json review-ready
Get-Content review-ready/report.md
Get-Content review-ready/evidence.json
py -3 factory.py verify review-ready
```

After reading the report and evidence, copy the review fingerprint from the verified bundle and substitute it for `PASTE_FINGERPRINT_HERE`.

```powershell
py -3 factory.py approve review-ready --reviewer "Your Name" --fingerprint PASTE_FINGERPRINT_HERE
Get-Content review-ready/approval.json
```

On macOS/Linux use `python3` instead of `py -3` and `cat` instead of `Get-Content`.

To see a blocked run, build `examples/blocked.json` to a different output directory and try to approve it. If a required check is failed or pending, approval is denied. Output directories and approval records are never overwritten; pick a new directory to build again.

## Start a task from a spec

Copy `SPEC_TEMPLATE.md` before implementation. `examples/RELEASE_READINESS_SPEC.md` shows a filled example for the bundled CLI. See `docs/BLUEPRINT.md` for the five production layers, three stack playbooks and automation tiers. Tier 1 is the proposed default; there is no automatic merge or deployment.

## Next milestone

Use one small change in a disposable repository: produce a patch, run the repository's agreed tests in isolation, and attach real test output and the diff to the review bundle. Keep opening a pull request and merging separate from local review approval.

## Browser Review Lab

Run `python3 -m http.server 8000 --directory dist` and open
`http://localhost:8000`. On Windows, replace `python3` with `py -3`.
Choose a ready, failed, or pending fictional brief. The lab shows evidence,
gates local approval, and lets you download a JSON snapshot. It does not
run CI, call external services, or open GitHub pull requests.

Checks: `python3 -m unittest -v` and `node --test tests/demo.test.mjs`.
Runtime dependencies for the lab: a current browser. Node is only needed
to run the JavaScript tests. See [Qodo parity and evaluation](docs/ROADMAP.md)
for product scope, test protocol, and the distinction between goals and shipped work.

## Local PR review slice

This separate checkout adds `pr_review.py`, a dependency-free, read-only local Git review CLI. It pins base/head commits and an approved spec hash, exports committed source/diff evidence, and validates changed-line citations. The default reviewer only flags a benign `REVIEW_REQUIRED` marker; optional replay findings have unverified semantics. No external model or target code is executed, and every successful run still requires human review.

See [the runnable local example and evidence contract](docs/PR_REVIEW.md), [the implementation spec](docs/PR_REVIEW_SPEC.md), and [the evaluation protocol and measured results](docs/EVALUATION.md). The original `factory.py` commands and browser simulation are unchanged. This local repository has no remote or hosting configuration; it is independent of the published Review Lab.

Human `accept`/`reject`/`defer` dispositions are now available through `pr_review.py disposition`, with validated history via `pr_review.py dispositions`. Both require the exact retained bundle fingerprint; records remain local and separate from immutable evidence. See [the disposition commands and limits](docs/PR_REVIEW.md#human-acceptrejectdefer-dispositions).

## Retail data-contract evaluation

See [Retail data contract review](docs/RETAIL_EVAL.md) for the public development fixture, scoring and Qodo comparison protocol.
