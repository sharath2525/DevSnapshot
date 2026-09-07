from __future__ import annotations

import unittest
from pathlib import PurePath

from app.core.exclusions import ExclusionMatcher, normalize_exclusion


class ExclusionMatcherTests(unittest.TestCase):
    def test_folder_name_matches_at_any_depth(self) -> None:
        matcher = ExclusionMatcher(["node_modules"])
        self.assertTrue(matcher.should_exclude_directory(PurePath("node_modules")))
        self.assertTrue(
            matcher.should_exclude_directory(PurePath("packages", "web", "node_modules"))
        )
        self.assertFalse(matcher.should_exclude_directory(PurePath("node_modules_notes")))

    def test_relative_path_matches_only_that_tree(self) -> None:
        matcher = ExclusionMatcher(["dataset/raw"])
        self.assertTrue(matcher.should_exclude_directory(PurePath("dataset", "raw")))
        self.assertTrue(
            matcher.should_exclude_directory(PurePath("dataset", "raw", "images"))
        )
        self.assertFalse(matcher.should_exclude_directory(PurePath("other", "raw")))

    def test_rules_are_normalized_and_case_insensitive(self) -> None:
        matcher = ExclusionMatcher([r" Cache\\Raw "])
        self.assertTrue(matcher.should_exclude_directory(PurePath("cache", "raw")))
        self.assertEqual(normalize_exclusion(r"/dataset\\raw/"), "dataset/raw")
        self.assertEqual(normalize_exclusion("../outside"), "")


if __name__ == "__main__":
    unittest.main()
