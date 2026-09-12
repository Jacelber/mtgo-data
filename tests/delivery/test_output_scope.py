"""Selected product validation accepts real growth and rejects incorrect totals."""
import json
from pathlib import Path
import tempfile
import unittest
import shutil

from validate_output_invariants import validate_repository_output
from tools.check_outputs import check


class OutputScopeTests(unittest.TestCase):
    def test_workflow_entry_connects_selected_schema_and_actual_arithmetic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "configs").mkdir()
            shutil.copyfile(Path(__file__).parents[2] / "configs/formats.yaml", root / "configs/formats.yaml")
            schemas = root / "schemas"
            schemas.mkdir()
            def write(path, content):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(content), encoding="utf-8")
            write("schemas/result.schema.json", {"$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "https://example.test/result.schema.json", "type": "object",
                "required": ["total_decks"], "properties": {"total_decks": {"type": "integer", "minimum": 0}}})
            for name, pattern in (("manifest", "stats/*/mtgo/range_4w.json"),
                                  ("melee-data-manifest", "data/*/melee/*.json")):
                write(f"schemas/{name}.json", {"schema_version": "1.0.0", "output_schema_version_embedded": True,
                      "mappings": [{"pattern": pattern, "schema": "result.schema.json"}]})
            selected = "stats/standard/mtgo/range_4w.json"
            unrelated = root / "stats/modern/mtgo/range_4w.json"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("malformed unrelated output")
            output = {"format": "standard", "total_decks": 5, "total_high_score": 0, "total_top8": 0,
                      "archetypes": [{"id": "a", "count": 5, "high_score_count": 0, "top8_count": 0,
                                      "high_score_share": 0, "top8_share": 0}]}
            write(selected, output)
            good = check(root, [selected, "README.md"])
            self.assertEqual((good["state"], good["schema_outputs"], good["mtgo_formats"]), ("passed", 1, ["standard"]))
            output["total_decks"] = 4
            write(selected, output)
            bad = check(root, [selected])
            self.assertEqual(bad["state"], "failed")
            self.assertTrue(any("sum(count)=5" in error for error in bad["failures"]))
            self.assertEqual(check(root, ["README.md"])["state"], "not_required")

    def test_unrelated_malformed_format_does_not_block_valid_selected_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "stats/standard/mtgo/range_4w.json"
            unrelated = root / "stats/modern/mtgo/range_4w.json"
            selected.parent.mkdir(parents=True)
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("not JSON")
            for count in (3, 5):  # Legitimate new population, no frozen count.
                selected.write_text(json.dumps({"total_decks": count, "total_high_score": 0, "total_top8": 0,
                    "archetypes": [{"id": "a", "count": count, "high_score_count": 0, "top8_count": 0,
                                    "high_score_share": 0, "top8_share": 0}]}))
                self.assertEqual(validate_repository_output(root, ["standard"]), [])
            content = json.loads(selected.read_text())
            content["total_decks"] = 4
            selected.write_text(json.dumps(content))
            self.assertTrue(any("sum(count)=5" in error for error in validate_repository_output(root, ["standard"])))

    def test_missing_selected_product_cannot_pass_as_zero_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(validate_repository_output(root, ["standard"]))
            (root / "stats/standard/mtgo").mkdir(parents=True)
            self.assertTrue(validate_repository_output(root, ["standard"]))
            with self.assertRaises(ValueError):
                validate_repository_output(root, ["../escape"])
