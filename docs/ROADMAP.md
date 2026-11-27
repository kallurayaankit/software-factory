# Qodo parity and a credible SOTA bar

**Status:** Review Lab and CLI are functional simulations. No real pull
request ingestion, model reviewer, cross-repo index, or performance result
exists yet. Qodo parity is a roadmap, not a release claim.

| Capability | Target | Status |
| --- | --- | --- |
| Pull request review | Findings with file, line, reason and actionable suggestion; summaries and reruns on new revisions | First GitHub, read-only pilot |
| Context | Repository-aware review, dependency context across authorised repos, PR history with retention and permission controls | Planned |
| Rules and compliance | Repository and organisation policies, check scope, exceptions, and auditable enforcement | Planned |
| Developer workflows | CLI/CI, comments and GitHub Checks, then GitLab, Bitbucket and Azure DevOps | Local simulation only |
| Team governance | Feedback and dismissals, analytics, RBAC, audit/export, data controls | Planned |
| Beyond parity | Requirement-to-change-to-test evidence, independently verified and pinned to the exact commit; stale or missing evidence blocks approval | Demonstrated only for local sample workflow |

Do not count retired integrations as current parity. Qodo's current
product page reports that its IDE plugin was retired in October 2026.
Verify integrations and plan entitlements again before any formal comparison.

## Pilot and evaluation

Start with a GitHub pull request from a repository the operator has
authorised. Ingest only the diff, the approved spec and allowed repository
context. Produce deduplicated findings with precise locations and a verifiable
evidence reference. An independent verifier rejects stale and unsupported
claims. Do not post, merge, or run pull-request code in the first read-only pilot.

Pre-register an equal-input head-to-head against a dated, fixed configuration
of Qodo and at least two strong baselines. Compare on an external benchmark
and a blinded holdout of unseen repositories containing authentic defects and
clean PRs. Use reviewers unaware of the tool identity, one-to-one issue
matching, and adjudication of disagreements. Report repository-clustered
confidence intervals for precision, recall, F1, high-severity misses, false
findings per clean PR, location accuracy, time, cost and human disposition.
Track the incidence of unsupported findings and stale approvals separately.
Keep tuned and held-out cases disjoint; publish misses, abstentions and
ambiguous labels, not just the leaderboard. Real-world adoption is useful
but is not interchangeable with ground-truth recall.

Only claim a lead on a named benchmark, scope and date after reproducible
results show it. An initial goal is better high-severity recall at matched
precision without increasing false findings on clean PRs. Do not claim a
general state-of-the-art result from a small internal demo or a single metric.

## Source material
- [Qodo product and integrations](https://www.qodo.ai/)
- [Qodo repository configuration](https://docs.qodo.ai/qodo-documentation/code-review/get-started/configuration-overview/configuration-file)
- [Qodo's vendor-run code review benchmark](https://www.qodo.ai/ai-code-review-benchmark/)
- [Martian CodeReviewBench paper](https://arxiv.org/abs/2611.26942)
