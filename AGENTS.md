# Software Factory contributor instructions

Start every change with a filled copy of SPEC_TEMPLATE.md. Keep changes
within the approved paths and run the exact documented checks. Never treat
a green simulation or model confidence as proof that a real change is safe
to merge. Default to read-only analysis and explicit human approval.
Run `python3 -m unittest -v` and `node --test tests/demo.test.mjs`. Do not
add dependencies, external access, or deployment behaviour without approval.
Do not store credentials, customer code, or identifying test data in fixtures.
