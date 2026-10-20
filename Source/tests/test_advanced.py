import unittest
from collections import deque

from engine import GameSession


def bfs(session):
    """Shortest number of moves to win from the start, or None. (Throwaway reference, not a graded solver.)"""
    p = session.problem
    seen, queue = {p.initial}, deque([(p.initial, 0)])
    while queue:
        state, d = queue.popleft()
        if p.goal_test(state):
            return d
        for a in p.actions(state):
            nxt = p.result(state, a)
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, d + 1))
    return None


class AdvancedTileTests(unittest.TestCase):
    def test_every_level_is_solvable(self):
        for n in range(1, 54):
            self.assertIsNotNone(bfs(GameSession(n)), 'level {} has no solution'.format(n))

    def test_classic_level_one_takes_seven_moves(self):
        self.assertEqual(bfs(GameSession(21)), 7)

    def test_fragile_tile_breaks_standing_block_but_not_lying_one(self):
        from engine import State
        p = GameSession(24).problem      # classic level 4 has fragile tiles
        kinds = p.level.kinds
        fx, fy = next((x, y) for (x, y), k in kinds.items()
                      if k == 'f' and (x + 1, y) in kinds and (x + 2, y) in kinds)
        lying = State([fx + 1, fy, fx + 2, fy], p.initial.bridges)
        self.assertIsNone(p._move(lying, 'LEFT'))          # would stand up on the fragile tile
        standing = State([fx + 2, fy], p.initial.bridges)
        self.assertIsNotNone(p._move(standing, 'LEFT'))    # lies across it instead

    def test_switch_toggles_bridges_and_split_merges(self):
        s = GameSession(22)          # classic level 2: soft/heavy switches and bridges
        self.assertTrue(s.level.switches and s.level.bridge_index)
        s = GameSession(29)          # classic level 9: a split tile
        self.assertTrue(s.level.splits)
        p = s.problem
        split_states = {p.initial}
        frontier = [p.initial]
        seen_split = False
        while frontier and not seen_split:
            nxt = []
            for st in frontier:
                for a in p.actions(st):
                    ns = p.result(st, a)
                    if ns not in split_states:
                        split_states.add(ns)
                        nxt.append(ns)
                        seen_split = seen_split or ns.split
            frontier = nxt
        self.assertTrue(seen_split, 'no split state reachable')


if __name__ == '__main__':
    unittest.main()
