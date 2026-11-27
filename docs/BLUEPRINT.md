# Software Factory blueprint

## Default: Tier 1, human-reviewed pull requests

The production target is a spec approved before coding, an isolated implementation, and independent review of the exact proposed diff and CI evidence. Only a human merges. The bundled offline demo already verifies and approves a local report. It does not run model agents, provision sandboxes, open PRs, or run a deployment.

## Five layers

| Layer | Initial decision | Evidence to retain |
| --- | --- | --- |
| Compute and isolation | Use one disposable environment per task, with no production credentials and outbound access denied by default. Install only approved dependencies. | Base revision, environment identity, dependency manifest |
| Orchestration | Move from spec approval to implementation, independent verification, then human review. Use separate roles for the implementer and reviewer. | Role outcomes, transitions, failures and retries |
| Model routing | Use a higher-reasoning model for planning and review and a faster one for bounded implementation. Keep provider selection configurable; cap retries and spend per run. | Provider/model identifiers, token count and spend where available |
| Verification | Run the approved checks outside the coder's control. Enforce allowed paths and diff size, then run the exact applicable type, lint, test and secret-scanning gates. A failure or missing required check blocks progression. | Diff, commands, exit codes, logs and a revision fingerprint |
| Observability and state | Start with structured per-run records and Git revisions; adopt OpenTelemetry when multiple services need correlated traces. Store durable repository guidance in `AGENTS.md`. Redact secrets and personal data. | Run ID, approved spec hash, base/head revisions, gate outcomes, review outcome |

State flow: `draft spec → approved spec → implement → verify → human review → merged by human`. Rework creates new evidence tied to the new revision. A green run never authorises shipping by itself. The local CLI must never treat free-form spec text as executable commands.

## Stack playbooks

- **Service/API:** establish the contract first (OpenAPI or GraphQL and migration plan), cover it with contract tests, then run handlers against a disposable test database.
- **Web/mobile:** define interfaces and key component states; verify rendered behaviour and relevant console output in browser/device tests. Use Playwright where web end-to-end coverage fits.
- **Existing or legacy:** map affected files and dependencies, capture baseline behaviour with characterisation tests, then restrict changes to agreed paths.

## Automation tiers

1. **Human-reviewed PR (default):** prepare the implementation, evidence and draft PR; a human decides what merges.
2. **Gated low-risk merge (future):** only for explicitly approved, tightly bounded changes after deterministic checks and independent review. Escalate auth, billing, schema, sensitive data and large diffs. No auto-merge is configured here.
3. **Autonomous release (future):** canary, monitor and roll back with pre-agreed thresholds and production controls. Not part of the starter.

## First real pilot

Use a small CLI or test-only change in a disposable repository. Copy `SPEC_TEMPLATE.md`, name the allowed files and exact tests, review the spec, implement, and gather the actual diff and test results for a human. A starter workflow is included for GitHub Actions if that is the eventual host; it tests **this project only**, has read-only repository permissions, and does not publish, deploy or merge. It has not been run on GitHub. No hosted provider or target repository has been configured.
