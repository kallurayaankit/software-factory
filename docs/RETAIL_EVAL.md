# Retail data contract review: public development benchmark

## What inspired it
- [Jonathan Gomez's public posts](https://au.linkedin.com/in/jonathanbgomez) describe bringing data checks earlier, self-service enablement, and domain-owned data products. The implementation here is our interpretation: the data producer specifies the unit, grain and coverage, and a reviewer can check the contract before changes ship.
- [Wesfarmers FY2026 results briefing, slide 11](https://www3.wesfarmers.com.au/docs/default-source/asx-announcements/2026-full-year-results-briefing-presentation-20260826214549.pdf) supplies six disclosed divisional sales values (Bunnings Group, Kmart Group and Officeworks, FY2025 and FY2026, AUD millions). These are published aggregates, not internal data. All mutations and judgments are original synthetic exercises. This does not represent Wesfarmers' internal systems and neither Wesfarmers nor Gomez is affiliated with this project.

## Run
From repository root:

```text
python -m benchmarks.retail_eval
python -m benchmarks.retail_eval --review-inputs
python -m benchmarks.retail_eval --score reviewed.json
```

The contract checks two clean controls and seven synthetic regressions covering units, metric identity, duplicate and missing keys, malformed rows, and mismatches against published values. Scores count misses, false findings, duplicate findings, and abstentions. The built-in checker sees the reference and enforces explicit rules: it is a fixture self-check, not an AI reviewer or a competitive result.

## Qodo head-to-head procedure
[Qodo's local Reviewer documentation](https://docs.qodo.ai/agentic-toolbox/agentic-toolbox-codebase-review-skill) describes reviewing local committed diffs. For a development run, use a disposable local Git repository for each case: start with the same clean public reference, commit only the candidate data-product change, keep the adjudication labels and scorer out of the checkout, and supply identical contract/context to each reviewer. A reorder-only case may exercise noise sensitivity. The unchanged control has no diff; report it separately as a no-change control if a tool cannot review it. Log the exact input hashes, model/tool versions, review modes, elapsed time, and unsupported cases. Do not mix local and hosted PR results, compare different minimum contexts, or turn silence into a pass.

Blind adjudicators to vendor and score whether each finding identifies the right root cause and supports it with accurate evidence. Supply a JSON object with a reviewer name and a cases mapping: each case ID maps to a list of adjudicated rule IDs, an empty list for an actual review with no findings, or null for an abstention. Use the literal `unmatched` for an unrelated finding. The scorer requires every case, keeps abstentions in recall, and counts duplicate findings as extra noise. Store raw vendor results separately. No vendor review has been run for this suite.

This published suite is suitable for development only. To test for a credible lead, use a separate unpublished corpus of benign changes across several domains, report precision and recall with confidence intervals plus false findings on clean changes, and measure how long a human takes to verify each finding. Test offline evidence verification separately from defect discovery. No state-of-the-art result is claimed.
