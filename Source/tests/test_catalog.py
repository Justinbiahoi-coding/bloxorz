import unittest

from engine.catalog import (ADVANCED_LEVELS, LEVEL_NUMBERS, NORMAL_LEVELS,
                            TUTORIAL_LEVELS, TUTORIAL_TIPS, level_label,
                            levels_for_mode, next_level)


class CatalogTests(unittest.TestCase):
    def test_tutorials_are_in_advanced_mode_first(self):
        for number in TUTORIAL_LEVELS:
            self.assertIn(number, LEVEL_NUMBERS)
            self.assertIn(number, ADVANCED_LEVELS)
            self.assertNotIn(number, NORMAL_LEVELS)
            self.assertIn(number, TUTORIAL_TIPS)
        self.assertEqual(ADVANCED_LEVELS[:len(TUTORIAL_LEVELS)], list(TUTORIAL_LEVELS))

    def test_modes_have_separate_level_lists(self):
        self.assertEqual(levels_for_mode('normal'), NORMAL_LEVELS)
        self.assertEqual(levels_for_mode('advanced'), ADVANCED_LEVELS)
        self.assertFalse(set(NORMAL_LEVELS) & set(ADVANCED_LEVELS))

    def test_next_level_stays_inside_mode(self):
        self.assertEqual(next_level('advanced', 54), 55)
        self.assertEqual(next_level('advanced', 55), 56)
        self.assertEqual(next_level('advanced', 56), 57)
        self.assertIsNone(next_level('normal', NORMAL_LEVELS[-1]))

    def test_tutorial_labels(self):
        self.assertEqual(level_label(54), 'Tutorial 1 - Fragile')
        self.assertEqual(level_label(57), 'Tutorial 4 - Split')
        self.assertEqual(level_label(1), 'Level 1')


if __name__ == '__main__':
    unittest.main()
