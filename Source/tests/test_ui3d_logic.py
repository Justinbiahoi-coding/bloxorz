"""3D front-end logic that runs without a window: settings, lighting levels, solver hand-off."""
import json
import tempfile
import unittest
from pathlib import Path

from engine import GameSession


class SettingsTests(unittest.TestCase):
    def setUp(self):
        from ui3d import settings
        self.settings = settings
        self.saved = (settings.PATH, dict(settings._values))
        self.tmp = tempfile.TemporaryDirectory()
        settings.PATH = Path(self.tmp.name) / 'settings.json'
        settings._values.clear()
        settings._values.update({k: (list(v) if isinstance(v, list) else v) for k, v in settings.DEFAULTS.items()})

    def tearDown(self):
        self.settings.PATH, values = self.saved
        self.settings._values.clear()
        self.settings._values.update(values)
        self.tmp.cleanup()

    def test_round_trip(self):
        s = self.settings
        s.set('music', 0.7)
        s.mark_completed(12)
        s._values['music'] = 0.1
        s.load()
        self.assertEqual(s.get('music'), 0.7)
        self.assertTrue(s.is_completed(12))

    def test_bad_values_fall_back_to_defaults(self):
        s = self.settings
        s.PATH.write_text(json.dumps({'music': 'loud', 'fullscreen': 1, 'move_speed': 2, 'completed': 'x'}))
        s.load()
        self.assertEqual(s.get('music'), s.DEFAULTS['music'])
        self.assertEqual(s.get('fullscreen'), s.DEFAULTS['fullscreen'])     # 1 is not a bool
        self.assertEqual(s.get('move_speed'), 2)                              # an int speed is fine
        self.assertEqual(s.get('completed'), [])

    def test_unreadable_file_is_ignored(self):
        s = self.settings
        s.PATH.write_text('{not json')
        s.load()
        self.assertEqual(s.get('music'), s.DEFAULTS['music'])

    def test_listeners_can_unsubscribe(self):
        s = self.settings
        seen = []
        fn = lambda key, value: seen.append(key)
        s.on_change(fn)
        s.set('legend', False)
        s.off(fn)
        s.set('legend', True)
        self.assertEqual(seen, ['legend'])


class LightingTests(unittest.TestCase):
    def test_exposure_does_not_compound(self):
        """Building the opening again must not brighten the scene again (getColor is a live view)."""
        from panda3d.core import NodePath
        from ui3d.world import lights, set_exposure
        sun = lights(NodePath('render'))
        base = sun.node().getColor()[0]
        for _ in range(3):
            set_exposure(sun, 2.1, 1.9)
        set_exposure(sun, 1.0, 1.0)
        self.assertAlmostEqual(sun.node().getColor()[0], base, places=5)


class SolveFromTests(unittest.TestCase):
    def test_moves_map_to_keys_and_win(self):
        from ui3d.autoplay import ACTION_KEYS, solve_from
        session = GameSession(1)
        moves, result, error = solve_from(session, 'BFS')
        self.assertIsNone(error)
        keys = {'left arrow': 'LEFT', 'right arrow': 'RIGHT', 'up arrow': 'DOWN', 'down arrow': 'UP',
                'space': 'SWITCH'}
        for action in moves:                       # play them through the same key table the scenes use
            self.assertTrue(session.move(keys[ACTION_KEYS[action]]))
        self.assertTrue(session.won)

    def test_missing_solver_reports_instead_of_raising(self):
        from ui3d.autoplay import solve_from
        moves, _, error = solve_from(GameSession(1), 'Iterative DFS')
        self.assertIsNone(moves)
        self.assertIn('not implemented', error)


if __name__ == '__main__':
    unittest.main()
