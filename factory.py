"""Offline release-readiness workflow. No generated code is executed."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

RECIPE = "release-readiness-v1"
FILES = ("brief.json", "report.md", "evidence.json")


def dump(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def string(value, label):
    if not isinstance(value, str) or not value.strip() or not value.isprintable() or len(value) > 160:
        raise ValueError(f"{label} must be 1–160 printable characters on one line")
    return value.strip()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate field: {key}")
        result[key] = value
    return result


def parse(data):
    brief = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object)
    if not isinstance(brief, dict) or set(brief) != {"release", "goal", "checks"}:
        raise ValueError("Brief must contain release, goal and checks only")
    release = string(brief["release"], "release")
    goal = string(brief["goal"], "goal")
    raw = brief["checks"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 25:
        raise ValueError("checks must contain 1–25 items")
    checks = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict) or set(item) != {"name", "status", "required"}:
            raise ValueError("Each check must contain name, status and required only")
        name = string(item["name"], "check name")
        if name.casefold() in seen:
            raise ValueError(f"Duplicate check name: {name}")
        seen.add(name.casefold())
        if item["status"] not in ("pass", "fail", "pending") or type(item["required"]) is not bool:
            raise ValueError("status must be pass, fail or pending; required must be a boolean")
        checks.append({"name": name, "status": item["status"], "required": item["required"]})
    if not any(check["required"] for check in checks):
        raise ValueError("At least one check must be required")
    return {"release": release, "goal": goal, "checks": checks}


def markdown(value):
    return "".join("\\" + c if c in "\\`*_{}[]()#+-.!|<>&" else c for c in value)


def package(data):
    brief = parse(data)
    blockers = [row["name"] for row in brief["checks"] if row["required"] and row["status"] != "pass"]
    decision = "BLOCKED" if blockers else "READY FOR HUMAN REVIEW"
    lines = [
        "# Release readiness",
        "",
        f"**Release:** {markdown(brief['release'])}",
        f"**Goal:** {markdown(brief['goal'])}",
        f"**Decision:** {decision}",
        "",
        "| Check | Required | Reported status |",
        "| --- | --- | --- |",
    ]
    for check in brief["checks"]:
        required = "yes" if check["required"] else "no"
        lines.append(f"| {markdown(check['name'])} | {required} | {check['status']} |")
    lines.extend(["", "Blocking checks: " + (", ".join(map(markdown, blockers)) if blockers else "none"), "",
                  "Check statuses are supplied by the brief. This tool does not run or verify those project checks.", ""])
    report = "\n".join(lines).encode("utf-8")
    evidence = {
        "recipe": RECIPE,
        "decision": decision,
        "blocking_checks": blockers,
        "verification": [
            {"check": "brief schema and values", "result": "pass"},
            {"check": "every required check is reported as passed", "result": "fail" if blockers else "pass"},
        ],
        "brief_sha256": digest(data),
        "report_sha256": digest(report),
    }
    return {"brief.json": data, "report.md": report, "evidence.json": dump(evidence)}, evidence


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(files):
    return digest(dump({name: digest(files[name]) for name in FILES}))


def build(source, output):
    files, evidence = package(source.read_bytes())
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        with (output / name).open("xb") as handle:
            handle.write(data)
    print(f"{evidence['decision']}: {output / 'report.md'}")
    print(f"Review fingerprint: {fingerprint(files)}")


def verified(output):
    actual = {}
    for name in FILES:
        path = output / name
        if path.is_symlink():
            raise ValueError(f"Unexpected symbolic link: {name}")
        actual[name] = path.read_bytes()
    expected, evidence = package(actual["brief.json"])
    if actual != expected:
        raise ValueError("Review bundle changed; rebuild to a new directory")
    return evidence, fingerprint(actual)


def approve(output, reviewer, reviewed):
    reviewer = string(reviewer, "reviewer")
    evidence, current = verified(output)
    if evidence["blocking_checks"]:
        raise ValueError("Required checks are not all reported as passed; approval denied")
    if reviewed != current:
        raise ValueError("Reviewed fingerprint does not match this bundle; approval denied")
    approval = {
        "recipe": RECIPE,
        "scope": "local review bundle only; no release or deployment",
        "reviewer": reviewer,
        "fingerprint": current,
        "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    with (output / "approval.json").open("xb") as handle:
        handle.write(dump(approval))
    print(f"Local approval recorded: {output / 'approval.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choices = parser.add_subparsers(dest="command", required=True)
    create = choices.add_parser("build", help="Generate a local review bundle")
    create.add_argument("brief", type=Path)
    create.add_argument("output", type=Path)
    check = choices.add_parser("verify", help="Recompute and verify the review bundle")
    check.add_argument("output", type=Path)
    accept = choices.add_parser("approve", help="Record a manual approval after reviewing")
    accept.add_argument("output", type=Path)
    accept.add_argument("--reviewer", required=True)
    accept.add_argument("--fingerprint", required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args.brief, args.output)
        elif args.command == "verify":
            evidence, current = verified(args.output)
            print(f"Bundle verified: {evidence['decision']}")
            print(f"Review fingerprint: {current}")
        else:
            approve(args.output, args.reviewer, args.fingerprint)
    except FileExistsError:
        parser.exit(2, "error: output or approval already exists; nothing was overwritten\n")
    except (ValueError, OSError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
