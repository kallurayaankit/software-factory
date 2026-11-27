"""Offline development benchmark. Publishes no data and calls no reviewer."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEGMENTS = {"bunnings_group", "kmart_group", "officeworks"}
KEYS = {(segment, year) for segment in SEGMENTS for year in (2025, 2026)}
PUBLIC_UNIT = "AUD_million"
CHECKS = {"metric", "unit", "unique_segment_year", "full_coverage", "valid_row", "source_amount"}

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def check(candidate, trusted):
    """Return applicable contract violations, independent of presentation order."""
    errors = set()
    if candidate.get("metric") != "divisional_sales":
        errors.add("metric")
    if candidate.get("unit") != PUBLIC_UNIT:
        errors.add("unit")
    seen = set()
    for row in candidate["rows"]:
        if (not isinstance(row, dict) or set(row) != {"segment", "year", "value"}
                or not isinstance(row["segment"], str) or type(row["year"]) is not int
                or type(row["value"]) is not int or row["value"] < 0):
            errors.add("valid_row")
            continue
        key = row["segment"], row["year"]
        if key in seen:
            errors.add("unique_segment_year")
        seen.add(key)
        if key in trusted and row["value"] != trusted[key]:
            errors.add("source_amount")
    if seen != KEYS:
        errors.add("full_coverage")
    return sorted(errors)

def suite(reference):
    cases = []
    def add(identifier, expected, edit):
        payload = deepcopy(reference)
        edit(payload)
        cases.append({"case": identifier, "expected": sorted(expected), "candidate": payload})
    add("r01", [], lambda c: None)
    add("r02", [], lambda c: c["rows"].reverse())
    add("r03", ["metric"], lambda c: c.update(metric="group_revenue"))
    add("r04", ["unit"], lambda c: c.update(unit="AUD"))
    add("r05", ["unique_segment_year"], lambda c: c["rows"].append(dict(c["rows"][0])))
    add("r06", ["full_coverage"], lambda c: c["rows"].pop())
    add("r07", ["source_amount"], lambda c: c["rows"][1].update(value=20330))
    add("r08", ["valid_row", "full_coverage"], lambda c: c["rows"][2].update(value=True))
    add("r09", ["source_amount"], lambda c: c["rows"][2].update(value=11655))
    return cases

def score(cases, report):
    """Score adjudicated findings, not free-form mention of a rule name."""
    if not isinstance(report, dict) or set(report) != {"reviewer", "cases"}:
        raise ValueError("report must contain reviewer and cases")
    if not isinstance(report["reviewer"], str) or not report["reviewer"].strip():
        raise ValueError("reviewer must be named")
    if not isinstance(report["cases"], dict) or set(report["cases"]) != {c["case"] for c in cases}:
        raise ValueError("report must cover every benchmark case; use null for an abstention")
    tp = fp = fn = duplicate = abstentions = clean_fp = clean_count = 0
    for case in cases:
        predicted = report["cases"][case["case"]]
        expected = set(case["expected"])
        if not expected:
            clean_count += 1
        if predicted is None:
            abstentions += 1
            fn += len(expected)
            continue
        if not isinstance(predicted, list) or any(
                not isinstance(rule, str) or rule not in CHECKS | {"unmatched"} for rule in predicted):
            raise ValueError("each adjudicated finding needs a known rule or 'unmatched'")
        matched = {rule for rule in predicted if rule in CHECKS}
        extras = len(predicted) - len(matched) - predicted.count("unmatched")
        duplicate += extras
        tp += len(matched & expected)
        count_wrong = len(matched - expected) + predicted.count("unmatched") + extras
        fp += count_wrong
        fn += len(expected - matched)
        if not expected:
            clean_fp += count_wrong
    return {"reviewer": report["reviewer"], "cases": len(cases),
            "tp": tp, "fp": fp, "fn": fn, "abstentions": abstentions, "duplicate_findings": duplicate,
            "clean_false_findings_per_case": clean_fp / clean_count if clean_count else None,
            "precision": tp / (tp+fp) if tp+fp else None,
            "recall": tp / (tp+fn) if tp+fn else None,
            "f1": 2*tp / (2*tp+fp+fn) if 2*tp+fp+fn else None}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, help="score manually adjudicated review JSON")
    parser.add_argument("--review-inputs", action="store_true", help="emit candidates without expected labels")
    args = parser.parse_args()
    path = ROOT / "wesfarmers_fy26_public.json"
    reference = read(path)
    trusted = {(r["segment"], r["year"]): r["value"] for r in reference["rows"]}
    cases = suite(reference)
    if args.score:
        output = score(cases, read(args.score))
    elif args.review_inputs:
        output = {"reference": reference, "cases": [
            {"case": c["case"], "candidate": c["candidate"]} for c in cases]}
    else:
        output = score(cases, {"reviewer": "deterministic contract smoke check",
            "cases": {c["case"]: check(c["candidate"], trusted) for c in cases}})
    output["reference_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
