import unittest

from engine.catalog import (ADVANCED_LEVELS, LEVEL_NUMBERS, NORMAL_LEVELS,
                            TUTORIAL_LEVELS, TUTORIAL_TIPS, level_label,
                            levels_for_mode, next_level)


class CatalogTests(unittest.TestCase):
    def test_tutorials_are_in_normal_mode_first(self):
        for number in TUTORIAL_LEVELS:
            self.assertIn(number, LEVEL_NUMBERS)
            self.assertIn(number, NORMAL_LEVELS)
            self.assertNotIn(number, ADVANCED_LEVELS)
            self.assertIn(number, TUTORIAL_TIPS)
        self.assertEqual(NORMAL_LEVELS[:len(TUTORIAL_LEVELS)], list(TUTORIAL_LEVELS))

    def test_split_is_by_level_number(self):
        self.assertEqual(NORMAL_LEVELS[len(TUTORIAL_LEVELS):], list(range(1, 24)))
        self.assertEqual(ADVANCED_LEVELS, list(range(24, 54)))
        self.assertIn(22, NORMAL_LEVELS)
        self.assertIn(26, ADVANCED_LEVELS)
        self.assertEqual(sorted(NORMAL_LEVELS + ADVANCED_LEVELS), LEVEL_NUMBERS)

    def test_modes_have_separate_level_lists(self):
        self.assertEqual(levels_for_mode('normal'), NORMAL_LEVELS)
        self.assertEqual(levels_for_mode('advanced'), ADVANCED_LEVELS)
        self.assertFalse(set(NORMAL_LEVELS) & set(ADVANCED_LEVELS))

    def test_next_level_stays_inside_mode(self):
        self.assertEqual(next_level('normal', 54), 55)
        self.assertEqual(next_level('normal', 57), 1)
        self.assertEqual(next_level('normal', 23), None)
        self.assertEqual(next_level('advanced', 24), 25)
        self.assertIsNone(next_level('advanced', ADVANCED_LEVELS[-1]))

    def test_tutorial_labels(self):
        self.assertEqual(level_label(54), 'Tutorial 1 - Fragile')
        self.assertEqual(level_label(57), 'Tutorial 4 - Split')
        self.assertEqual(level_label(1), 'Level 1')


if __name__ == '__main__':
    unittest.main()
