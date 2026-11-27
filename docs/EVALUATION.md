# Review quality evaluation protocol

## Status: protocol, not a performance claim

The current product slice is a local evidence pipeline with a benign marker checker and optional replay. It has no semantic reviewer. It cannot establish Qodo parity, state-of-the-art review quality, or runtime correctness. Citation validation is a mechanical capability and must not be counted as semantic precision.

Measured on 2026-11-27 in the local development environment: 38 Python tests passed (6 existing release-readiness tests and 32 PR-review tests); 3 existing Node demo tests passed. These tests use synthetic local repositories and fixtures. They include actual Git reads of benign committed changes, citation rejection, worktree exclusion, local accept/reject/defer history, stale head/spec fingerprints, tampered evidence and legacy bundle compatibility. No external model calls, target-code execution, private repository access or remote benchmark runs were performed. Model precision, defect recall, human review time, comparative quality and production latency are **not measured**. No external model spend occurred; local compute cost was not metered.

The targets below are proposed preregistered pilot criteria. They are not achieved results. The marker checker is an evidence-plumbing baseline only, not an entrant claiming semantic review quality.

## 1. Freeze a task and evaluation contract

Evaluate an actionable review of the exact merge-base/head diff against requirements available at review time. An actionable finding identifies a concrete incorrect behavior, trigger, consequence and useful location; style preferences and ungrounded speculation are not defects unless an explicit requirement makes them relevant.

Each item records dataset version, repository lineage, language, source license or permission, requested base, merge base, head, spec hash, eligible context, diff size, known defects and severity rationale. Fix commits may establish labels, but their contents and subsequent reviewer discussions must not be sent to the system under test.

Before running the locked set, freeze model/provider/version, prompts, context selection, decoding settings, retry policy, tool permissions, token/spend/time limits, required output fields, matcher rules, deduplication rules and scorer implementation. Store the run configuration hash. Do not browse, execute target code or allow extra context for one comparator unless that capability is explicitly part of a separate comparison track.

## 2. Construct development and held-out sets

Initial proposal:

- 40 labeled development changes for prompt, parser and workflow iteration.
- 120 locked pilot changes across at least 12 repository lineages, approximately half defect-containing and half clean.
- No repository lineage shared between development and locked sets. Treat forks and near-duplicate code as one lineage; deduplicate related changes and issue families across splits.
- Stratify by supported language, diff size, requirement quality, cross-file dependency, defect category and severity. Include benign documentation/refactoring changes, plausible false-positive traps and incomplete requirements.
- Prefer natural historical defects with defensible labels. Add synthetic defects only as a separately identified and separately reported stratum, never silently pooling them into a headline real-world score.
- A clean label requires active inspection, not merely the absence of reported bugs. Retain uncertainty and exclude genuinely unresolvable labels from the primary scored population under a predefined rule; report all exclusions.

Use authorized, licensed sources. Avoid credentials, identifying customer data, malicious payloads and exploit chains. This is a defensive review evaluation; safe local fixtures are sufficient for ingestion and evidence tests. Private-source inclusion requires a separately established handling policy and authorization.

Do not tune after seeing locked-set outcomes. Findings from pilot failures may inform the next system, but its confirmatory score must come from a new untouched set. Public datasets may have training contamination; record that risk and include newly curated, temporally held-out or authorized nonpublic cases before making broad claims.

## 3. Establish labels and blinded adjudication

Two experienced reviewers independently inspect each pre-fix snapshot and its contemporaneous specification. They record root cause, trigger, expected/actual behavior, affected paths/lines, severity and evidence. A third reviewer resolves disagreement. Report initial agreement and unresolved labels; do not hide ambiguous examples.

System outputs are anonymized and shuffled before scoring. Two blinded graders classify each distinct claim as valid/actionable, incorrect, insufficiently grounded, duplicate or non-defect. They also score localization separately. A novel finding absent from the original labels is adjudicated before being counted as false: the gold set is not presumed exhaustive.

One root cause counts as one matched defect, even when several comments cite it. Duplicate comments do not increase recall. Define matching by behavior and root cause, not exact wording or exact line equality. If a comment combines multiple distinct claims, split them before scoring under a consistent rule. Valid findings outside the eligible change/scope are reported separately and do not inflate the primary diff-review score.

## 4. Metrics and denominators

- **Actionable finding precision:** valid, distinct, in-scope defect findings / all distinct defect claims. Incorrect and insufficiently supported claims count against precision; report non-defect noise separately. No findings means precision is undefined, not 100%.
- **Defect recall:** labeled in-scope defects matched by at least one valid finding / all labeled in-scope defects, including those in eligible reviews that timed out, failed or abstained.
- **Severity/category recall:** the same denominator discipline within each stratum. Publish counts; do not summarize tiny high-severity samples as reliable percentages.
- **Clean-PR noise:** false or unsupported findings / adjudicated clean PRs; also report the fraction of clean PRs receiving any false finding.
- **Citation validity:** citations whose path, revision side, line and quoted text match the captured evidence / all citations. This is distinct from truth and usefulness.
- **Duplicate rate:** duplicate comments / total comments before deduplication.
- **Coverage:** completed, incomplete, errored and abstained reviews / all eligible reviews. Report unsupported cases separately alongside the predeclared eligibility rule.
- **Human effort:** time to disposition findings and total review time in a randomized or counterbalanced study. Include false-positive handling and onboarding costs.
- **Operational measures:** median/p95 wall time, tokens, provider cost, retries and failure rate per attempted PR. Report missing telemetry explicitly rather than imputing zero.

Treat missing/invalid structured output as a failed review. Retain its incurred time and cost. Do not selectively retry examples to improve quality. A syntactically valid zero-finding output remains an attempted review and can have zero recall on a defective case.

## 5. Pilot gates (targets only)

Freeze these thresholds before the first locked run:

- 100% citation validity after validation. Also report how many generated candidates were rejected so output filtering cannot conceal poor grounding.
- Precision point estimate at least 85%, with a 95% confidence lower bound at least 75%.
- Defect recall at least 60% across the eligible defective set.
- At most 0.2 false findings per clean PR.
- Every revision mismatch and missing/failed required check remains visibly blocking; no output grants merge/deploy authority.
- Pre-register actual dollar and wall-time caps once the semantic reviewer and available provider are selected. Until then, these budgets and operational gates are undecided; they cannot be reported as passed.

A system with too few findings for a defensible precision interval fails to demonstrate the precision gate; it does not pass through abstention. The 120-item pilot is for diagnosing feasibility, not an automatic sufficient sample size for superiority claims.

## 6. Baselines, parity and uncertainty

Compare on the same eligible changes and contemporaneous context against:

1. A deterministic-check baseline with declared rule coverage.
2. A single-pass semantic reviewer using a frozen model and budget.
3. The full proposed review pipeline, including independent checks.
4. The then-current Qodo product/configuration only once authorized access and equivalent input delivery are available.

Track feature parity separately from quality: ingestion/provider support, repository context, inline evidence, spec handling, workflow integration, independent checks, human dispositions, auditability, privacy controls and operational behavior. A missing feature cannot be compensated for by a benchmark score. Record exact tested product versions/settings and evidence for each capability rather than assuming a marketing claim represents available behavior.

Run three frozen-configuration repetitions per eligible item to expose stochastic variability. Do not treat repetitions or multiple findings within one PR as independent samples. Report per-run metrics and variation. Use paired repository-cluster bootstrap intervals for system differences, with PR resampling within repository where appropriate; preserve pairing across systems. Fix the bootstrap seed and report the resampling procedure and sample counts. With only 12 repository clusters, intervals can be unstable; disclose that limitation and enlarge the confirmatory set based on the effect size and power analysis.

Predeclare primary endpoints and superiority/non-inferiority margins before comparison. Correct or clearly label exploratory multiple comparisons. For a superiority claim, require a confidence interval supporting the predefined improvement on primary endpoints without violating safety/noise/cost gates. A point estimate alone, an unpaired comparison or selective wins are insufficient.

## 7. Independent checks and human outcomes

Evaluate citation/schema validation separately from semantic checking. A second model agreeing with the first is not statistically independent evidence; shared training, prompts and provider can create correlated errors. Ablate the second pass, context retrieval and deterministic checks one at a time to measure their contribution and cost.

The local CLI now collects self-attested accept/reject/defer reasons tied to the exact bundle fingerprint. For a human-outcomes evaluation, collect these records under a predeclared study protocol. Acceptance indicates reviewer judgment, not automatically ground truth or production safety. Reconcile dispositions with blinded adjudication and, where available, safe tests or subsequent corrective changes. Never treat a human merge as proof that all findings were correct or that none were missed.

## 8. Reproducible release evidence

Publish or retain, as permissions permit: dataset manifest and hashes, eligibility/exclusion rules, frozen configs, raw outputs, rejection logs, adjudications, metric code, exact denominators, confidence intervals, costs, failure cases and capability matrix. Keep test fixtures separate from benchmark labels and avoid source disclosure without permission.

Do not claim parity or state-of-the-art quality until the relevant capabilities are implemented, the comparison is run against named contemporary systems, an untouched confirmatory evaluation supports the claim, and limitations/generalization boundaries are stated. This checkout provides the evidence substrate and protocol only.
