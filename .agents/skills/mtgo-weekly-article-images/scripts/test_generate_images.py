"""Small hand-calculable cases for article selection and event headers."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'src'))
from generate_images import event_suffix, share, summarize


def record(parent, child=None, high=True, top=False):
    return dict(archetype_id=parent, subtype_id=child, is_high_score=high, is_top8=top)


class ArticleTablesTest(unittest.TestCase):
    def test_exact_two_percent_and_four_week_only_selection(self):
        now = [record('family', 'a')]*4 + [record('family', 'b')]*3 + [record('bulk')]*193
        prior = [record('old')]*4 + [record('bulk')]*196
        rows, totals = summarize([now, [], prior])
        self.assertEqual([k for k, _ in rows], [('bulk', None), ('family', 'a'), ('old', None), None])
        self.assertEqual(totals, [(200, 0), (0, 0), (200, 0)])
        self.assertEqual(rows[-1][1], [[3, 0], [0, 0], [0, 0]])

    def test_threshold_precedes_display_rounding(self):
        values = [record('border')]*39 + [record('bulk')]*1961
        self.assertNotIn(('border', None), [k for k, _ in summarize([values]*3)[0]])

    def test_high_and_top8_use_separate_counts_including_unknown(self):
        values = [record('a', high=True, top=False), record('a', high=False, top=True),
                  record('unknown', high=True, top=True)]
        rows, totals = summarize([values]*3)
        self.assertEqual(totals, [(2, 2)]*3)
        self.assertEqual(rows[0][1], [[1, 1]]*3)
        self.assertIsNone(share(0, 0))

    def test_pooled_reference_changes_eligibility(self):
        # One small week at 50%, three large weeks at 0%: pooled 5/310 < 2%.
        prior = [record('small')]*5 + [record('bulk')]*305
        now = [record('bulk')]*100
        self.assertNotIn(('small', None), [k for k, _ in summarize([now, now, prior])[0]])

    def test_event_abbreviations(self):
        for description, expected in [('Modern Showcase Challenge', 'SC'),
                                      ('Modern RC Super Qualifier', 'SQ'),
                                      ('Modern RC Qualifier', 'RCQ'),
                                      ('Modern Showcase Qualifier', 'SCQ'),
                                      ('Modern Challenge 16', ''), ('Modern Challenge 64', '')]:
            with self.subTest(description=description):
                self.assertEqual(event_suffix(description, 'modern'), expected)


if __name__ == '__main__':
    unittest.main()
