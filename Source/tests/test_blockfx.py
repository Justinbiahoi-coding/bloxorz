import unittest

from ui.blockfx import make_box, rolls_to


class BlockGeometryTests(unittest.TestCase):
    def test_box_sizes_follow_the_block_pose(self):
        self.assertEqual(make_box([(3, 4)], False), (3, 4, 1, 1, 2))            # standing
        self.assertEqual(make_box([(3, 4), (4, 4)], False), (3, 4, 2, 1, 1))    # lying along x
        self.assertEqual(make_box([(3, 4), (3, 5)], False), (3, 4, 1, 2, 1))    # lying along y
        self.assertEqual(make_box([(3, 4)], True), (3, 4, 1, 1, 1))             # split cube

    def test_roll_matches_the_engine_rules(self):
        standing = (3, 4, 1, 1, 2)
        self.assertTrue(rolls_to(standing, (1, 0), (4, 4, 2, 1, 1)))      # tips over eastwards
        self.assertTrue(rolls_to((4, 4, 2, 1, 1), (1, 0), (6, 4, 1, 1, 2)))   # lying along the move: stands up
        self.assertTrue(rolls_to((4, 4, 1, 2, 1), (1, 0), (5, 4, 1, 2, 1)))   # lying across: rolls sideways
        self.assertFalse(rolls_to(standing, (1, 0), (5, 4, 2, 1, 1)))


if __name__ == '__main__':
    unittest.main()
