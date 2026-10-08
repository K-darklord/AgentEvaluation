"""Regression tests for the T1 'commit, don't scan' extractor contract.

Freezes the false-positive / false-negative cases found on 2026-10-08 when the new
benchmarks (AIME / GPQA-Diamond / BBH) were added, so a future refactor cannot silently
re-open them. Run from the repo root:

    python -m unittest tests.test_evaluator_commit -v

No third-party test dependency: stdlib unittest only (repo has no test framework).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import evaluator as ev  # noqa: E402


def bbh(gold, pred):
    return ev._score_bbh({"gold_answer": gold, "final_answer": pred})


def aime(gold, pred):
    return ev._score_aime({"gold_answer": gold, "final_answer": pred})


def gpqa(gold, pred):
    return ev._score_gpqa({"gold_answer": gold, "final_answer": pred})


class TestCommittedText(unittest.TestCase):
    """Closed-set word targets: no prose substring matching."""

    def test_false_positives_now_zero(self):
        # gold='No' must not match "I don't know" (contains 'no' inside 'know').
        self.assertEqual(bbh("No", "I don't know."), 0.0)
        self.assertEqual(bbh("No", "This is not correct."), 0.0)
        # gold='Yes' must not match "Yesterday" (starts with 'yes').
        self.assertEqual(bbh("Yes", "Yesterday I went to the store."), 0.0)
        # gold='True' must not match prose that merely mentions the word.
        self.assertEqual(bbh("True", "It is not true that it's false."), 0.0)

    def test_true_positives_still_one(self):
        self.assertEqual(bbh("Yes", "Yes"), 1.0)
        self.assertEqual(bbh("No", "No."), 1.0)
        self.assertEqual(bbh("True", "True"), 1.0)
        self.assertEqual(bbh("False", "False"), 1.0)
        self.assertEqual(bbh("No", "The answer is No."), 1.0)
        self.assertEqual(bbh("Yes", "Final answer: yes"), 1.0)
        self.assertEqual(bbh("No", "reasoning...\nNo"), 1.0)

    def test_extract_committed_text_direct(self):
        s = {"yes", "no", "true", "false"}
        self.assertEqual(ev._extract_committed_text("No", s), "no")
        self.assertEqual(ev._extract_committed_text("(Yes)", s), "yes")
        self.assertEqual(ev._extract_committed_text("answer: FALSE", s), "false")
        self.assertIsNone(ev._extract_committed_text("I don't know", s))
        self.assertIsNone(ev._extract_committed_text("Yesterday", s))


class TestCommittedLetter(unittest.TestCase):
    def test_letter_targets(self):
        self.assertEqual(bbh("(B)", "B"), 1.0)
        self.assertEqual(bbh("(B)", "Answer: (B)"), 1.0)
        self.assertEqual(bbh("(K)", "K"), 1.0)   # geometric_shapes goes up to (K)
        self.assertEqual(bbh("(A)", "B"), 0.0)

    def test_gpqa_prose_no_longer_scores_by_luck(self):
        # gpqa_009/gpqa_016 class: prose answer with no committed option letter.
        self.assertEqual(gpqa("A", "The answer involves quantum tunnelling."), 0.0)
        self.assertEqual(gpqa("C", "C"), 1.0)

    def test_letter_with_label_is_a_commit(self):
        # BBH models echo '(X) label' -- this is a real commit to option X (bbh_0001/0002/0009).
        self.assertEqual(bbh("(B)", "(B) heptagon"), 1.0)
        self.assertEqual(bbh("(J)", "(J) triangle"), 1.0)
        self.assertEqual(bbh("(A)", "(A) Modifiers or Adjectives"), 1.0)
        self.assertEqual(bbh("(B)", "B. heptagon"), 1.0)
        self.assertEqual(bbh("(A)", "(B) heptagon"), 0.0)

    def test_bare_article_is_not_a_commit(self):
        # a line beginning with the English article 'A' (or 'i.e.') must not read as option A.
        self.assertEqual(gpqa("A", "A triangle has three sides."), 0.0)
        self.assertEqual(gpqa("A", "i.e. something else entirely"), 0.0)


class TestGpqaEmphasisRegression(unittest.TestCase):
    """gpqa_001 class (2026-10-08): a markdown-emphasised committed letter used to be
    labelled complete_failure, silently under-counting GPQA accuracy."""

    def test_bold_and_emphasis_letters_are_a_commit(self):
        self.assertEqual(gpqa("B", "**B**"), 1.0)
        self.assertEqual(gpqa("A", "**A**"), 1.0)
        self.assertEqual(gpqa("C", "*C*"), 1.0)
        self.assertEqual(gpqa("D", "`D`"), 1.0)
        self.assertEqual(gpqa("B", "Answer: **B**"), 1.0)

    def test_emphasis_still_no_prose_false_positive(self):
        self.assertEqual(gpqa("A", "A triangle has three sides."), 0.0)
        self.assertEqual(gpqa("A", "i.e. something else entirely"), 0.0)

    def test_committed_wrong_letter_is_wrong_option_not_failure(self):
        out = ev._label_row_tiered(
            {"gold_answer": "B", "final_answer": "**C**", "metadata": {"benchmark": "gpqa"}}
        )
        self.assertEqual(out["error_type"], "wrong_option")
        out2 = ev._label_row_tiered(
            {"gold_answer": "B", "final_answer": "no option picked here",
             "metadata": {"benchmark": "gpqa"}}
        )
        self.assertEqual(out2["error_type"], "complete_failure")


class TestCommittedNumber(unittest.TestCase):
    def test_numeric_committed_not_first(self):
        # committed number is 24 though 3/5/15 appear earlier.
        self.assertEqual(bbh("24", "First 3 times 5 is 15, then the answer is 24."), 1.0)
        self.assertEqual(bbh("-50", "-50"), 1.0)
        self.assertEqual(bbh("8", "8"), 1.0)

    def test_numeric_false_positives_now_zero(self):
        self.assertEqual(bbh("24", "First 3 times 5 is 15, then I am not sure."), 0.0)
        self.assertEqual(bbh("8", "There are 8 items in total."), 0.0)

    def test_extract_committed_number_direct(self):
        self.assertEqual(ev._extract_committed_number("the answer is 24."), 24.0)
        self.assertEqual(ev._extract_committed_number("\\boxed{42}"), 42.0)
        self.assertEqual(ev._extract_committed_number("3.14"), 3.14)
        self.assertIsNone(ev._extract_committed_number("no number here"))


class TestAimeRegression(unittest.TestCase):
    """AIME path (already on the contract) must not regress."""

    def test_committed_integer(self):
        self.assertEqual(aime("42", "42"), 1.0)
        self.assertEqual(aime("42", "\\boxed{42}"), 1.0)
        self.assertEqual(aime("42", "The answer is 42."), 1.0)

    def test_blob_passing_through_gold_scores_wrong(self):
        self.assertEqual(aime("42", "We compute 42 mid-way but the boxed answer is 7."), 0.0)
        self.assertEqual(aime("42", "I am not sure."), 0.0)


if __name__ == "__main__":
    unittest.main()
