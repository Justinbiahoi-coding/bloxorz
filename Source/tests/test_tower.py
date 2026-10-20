import unittest
from collections import deque

from engine import FLOORS, Tower


def winning_moves(session):
    p = session.problem
    seen, queue = {p.initial}, deque([(p.initial, [])])
    while queue:
        state, path = queue.popleft()
        if p.goal_test(state):
            return path
        for a in p.actions(state):
            nxt = p.result(state, a)
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [a]))


class TowerTests(unittest.TestCase):
    def test_cannot_descend_before_winning(self):
        self.assertFalse(Tower((2, 3)).descend())

    def test_winning_a_floor_drops_to_the_next_until_the_last(self):
        tower = Tower((2, 3))
        for expected_index in (1, None):
            for move in winning_moves(tower.session):
                tower.session.move(move)
            if expected_index is None:
                self.assertTrue(tower.is_last)
                self.assertFalse(tower.descend())
            else:
                self.assertTrue(tower.descend())
                self.assertEqual(tower.index, expected_index)
                self.assertEqual(tower.total_moves, 4)

    def test_default_tower_is_fully_solvable(self):
        tower = Tower()
        for _ in FLOORS:
            for move in winning_moves(tower.session):
                tower.session.move(move)
            tower.descend()
        self.assertTrue(tower.session.won)


if __name__ == '__main__':
    unittest.main()
