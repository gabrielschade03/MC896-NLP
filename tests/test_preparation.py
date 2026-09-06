"""Testes de integridade, separação e preservação dos dados (sem dependências)."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.data_io import DataError, read_csv
from src.prepare_data import prepare
from src.splitting import split_by_article
from src.validation import validate


def case(identifier, article, **changes):
    return {"case_id": identifier, "article_id": article, "case_text": 'Fever, "cough".\nSecond line.',
            "age": "", "gender": "Unknown", **changes}


def article(identifier):
    return {"article_id": identifier, "title": "A title", "keywords": "[fever]",
            "mesh_terms": "['Diagnosis, Differential', Fever]", "major_mesh_terms": "", "case_amount": ""}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.cases = [case("a1", "a"), case("a2", "a"), case("b1", "b"), case("c1", "c")]
        self.articles = [article(value) for value in "abc"]

    def write_csv(self, path, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_group_split_is_complete_disjoint_and_order_independent(self):
        groups = split_by_article(self.cases, 0.2, 42)
        self.assertEqual(groups, split_by_article(list(reversed(self.cases)), 0.2, 42))
        dev = {row["article_id"] for row in groups["development"]}
        evaluation = {row["article_id"] for row in groups["evaluation"]}
        self.assertFalse(dev & evaluation)
        self.assertEqual(len(evaluation), 1)
        self.assertCountEqual([row["case_id"] for rows in groups.values() for row in rows],
                              [row["case_id"] for row in self.cases])

    def test_invalid_split_parameters(self):
        for value in (0, 1, -0.1, float("nan")):
            with self.subTest(value=value), self.assertRaises(DataError):
                split_by_article(self.cases, value, 42)
        with self.assertRaises(DataError):
            split_by_article(self.cases[:2], 0.2, 42)

    def test_duplicate_and_orphan_ids_block_validation(self):
        report = validate(self.cases + [case("a1", "missing")], self.articles + [article("a")])
        self.assertEqual(report["duplicate_ids"]["case_id"], ["a1"])
        self.assertEqual(report["duplicate_ids"]["metadata_article_id"], ["a"])
        self.assertEqual(report["orphan_article_ids"], ["missing"])
        self.assertEqual(len(report["errors"]), 3)

    def test_blank_required_fields_and_whitespace_ids(self):
        rows = [case(" a ", "a", case_text="  ")]
        self.assertEqual(len(validate(rows, self.articles)["errors"]), 2)

    def test_missing_age_is_not_zero_and_invalid_age_is_reported(self):
        rows = [case("a1", "a"), case("a2", "a", age="0"), case("b1", "b", age="NaN")]
        report = validate(rows, self.articles)
        self.assertEqual(report["missing_fields"]["cases"]["age"], 1)
        self.assertEqual(report["invalid_age_case_ids"], ["b1"])
        self.assertFalse(report["errors"])
        self.assertEqual(rows[0]["age"], "")

    def test_declared_counts_are_checked(self):
        self.articles[0]["case_amount"] = "9"
        report = validate(self.cases, self.articles)
        self.assertEqual(report["case_amount_mismatches"],
                         [{"article_id": "a", "declared": 9, "observed": 2}])

    def test_csv_multiline_and_join_roundtrip_and_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_csv(root / "cases.csv", self.cases)
            self.write_csv(root / "metadata.csv", self.articles)
            original = (root / "cases.csv").read_bytes()
            output = root / "output"
            report = prepare(root, output)
            self.assertEqual(report["counts"]["cases"], 4)
            records = [json.loads(line) for path in (output / "records").glob("*.jsonl")
                       for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 4)
            for record in records:
                self.assertEqual(record["case"]["case_text"], self.cases[0]["case_text"])
                self.assertEqual(record["case"]["article_id"], record["article"]["article_id"])
                self.assertEqual(record["article"]["mesh_terms"], self.articles[0]["mesh_terms"])
            before = {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            prepare(root, output)
            self.assertEqual(before, {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()})
            self.assertEqual(original, (root / "cases.csv").read_bytes())
            with self.assertRaises(DataError):
                prepare(root, output, seed=99)
            self.assertEqual(before, {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()})

    def test_invalid_data_writes_no_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.write_csv(root / "cases.csv", self.cases + [self.cases[0]])
            self.write_csv(root / "metadata.csv", self.articles)
            with self.assertRaises(DataError):
                prepare(root, root / "output")
            self.assertFalse((root / "output").exists())

    def test_malformed_csv_and_headers(self):
        examples = ("a,b\n1,2,3\n", "a,b\n1\n", "a,a\n1,2\n", "other\n1\n", "a,b\n")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.csv"
            for content in examples:
                with self.subTest(content=content):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(DataError):
                        read_csv(path, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
