# Feature / Task: Review a fictional release-readiness brief

## 1. Objective & Context
- **Goal:** Produce a reviewable report from a fictional release checklist and bind local approval to the reviewed fingerprint.
- **Target Files / Modules:** `factory.py`, `test_factory.py`, `examples/ready.json`, `examples/blocked.json`.
- **Reference Patterns:** Python standard library; see commands in `README.md`.

## 2. Explicit Non-Goals
- Do not open or merge any PR, access external services, or deploy software.
- Do not treat supplied example check statuses as tests executed against a real product.

## 3. Functional & Interface Requirements
- **Inputs / Triggers:** Structured JSON brief; output folder; explicit reviewer name and verified fingerprint for approval.
- **Business Rules:** Reject failed/pending required checks and fingerprints that no longer match. Do not overwrite an existing output folder or approval.
- **Outputs / Side Effects:** Write the local report and evidence; only successful explicit approval records the reviewer-supplied name and fingerprint.

## 4. Acceptance Criteria & Verification
- [ ] `python -m unittest -v` exercises positive and negative CLI cases.
- [ ] Build and verify the ready example, approve the verified fingerprint, then confirm `approval.json` exists. Confirm the blocked example cannot write an approval.
- [ ] `python -m compileall -q factory.py test_factory.py` checks syntax. A standalone linter and type checker are not part of this dependency-free prototype.
