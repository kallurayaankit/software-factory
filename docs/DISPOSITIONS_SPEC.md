# Feature: human dispositions bound to reviewed evidence

## Objective and scope
Add local accept/reject/defer events for individual findings in the independent PR-review checkout. Allowed paths: pr_review.py, test_pr_review.py, README.md, docs/PR_REVIEW.md, docs/EVALUATION.md, docs/DISPOSITIONS_SPEC.md. Keep factory.py, hosted UI and original starter unchanged.

## Requirements
Require the exact trusted bundle fingerprint, an existing finding ID, a decision, a reviewer name and a nonempty reason. Verify and reconstruct the complete evidence before writing. Accept means the finding is valid, never approval to merge or deploy. Defer leaves it unresolved. Record UTC time, event ID, fingerprint, finding, reviewer, reason and explicit scope. Append individual exclusive event files to a sidecar directory partitioned by fingerprint; never rewrite evidence or previous events. Provide a command to read validated history for the exact fingerprint. Missing history is empty. Stale evidence or malformed history must fail closed. The current interface is local/self-attested, not identity authentication or tamper-proof storage.

## Compatibility
Retain verification of existing pr-review-v1 bundles without changing their fingerprints. New v2 reports explain sidecar dispositions. No history automatically transfers between versions, changed specs, source revisions or findings.

## Non-goals
No network, models, target-code execution, GitHub changes, publication, automated approval, merge or deployment. No global latest-state arbitration or authenticated audit service.

## Acceptance
Run python3 -m unittest -v and node --test tests/demo.test.mjs. Cover all decisions, preserved event/evidence bytes, changed head/spec with stable finding ID, tampered evidence, stale fingerprint, unknown finding, empty identity/reason, malformed/wrong-fingerprint history, CLI behavior, and v1 compatibility. Update usage and measured results separately from prospective quality targets.
