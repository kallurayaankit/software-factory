from pathlib import Path
import unittest
from benchmarks.retail_eval import check, read, score, suite

class RetailEvalTests(unittest.TestCase):
    def setUp(self):
        self.reference = read(Path(__file__).parent / "benchmarks" / "wesfarmers_fy26_public.json")
        self.trusted = {(r["segment"], r["year"]): r["value"] for r in self.reference["rows"]}
        self.cases = suite(self.reference)

    def test_public_inputs_keep_original_values(self):
        self.assertEqual(self.trusted[("bunnings_group", 2026)], 20331)
        self.assertEqual(self.trusted[("kmart_group", 2026)], 11655)
        self.assertEqual(self.trusted[("officeworks", 2026)], 3679)

    def test_contract_matches_all_fixed_cases(self):
        for case in self.cases:
            with self.subTest(case=case["case"]):
                self.assertEqual(check(case["candidate"], self.trusted), case["expected"])

    def test_unmatched_duplicate_and_abstention_count(self):
        result = {c["case"]: c["expected"] for c in self.cases}
        result["r01"] = ["unmatched"]
        result["r04"] = None
        result["r05"] *= 2
        s = score(self.cases, {"reviewer": "test", "cases": result})
        self.assertEqual((s["tp"], s["fp"], s["fn"], s["abstentions"]), (7, 2, 1, 1))
        self.assertEqual(s["clean_false_findings_per_case"], 0.5)

    def test_missing_case_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "every benchmark case"):
            score(self.cases, {"reviewer": "test", "cases": {}})
