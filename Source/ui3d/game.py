"""Tower mode in 3D: the climb starts in the lobby and ends on the roof. Win a floor by standing in its
elevator: the doors close, the car rides up with the camera, and the next floor opens around its arrival
elevator. Arrows roll, Space swaps split cubes, R restarts the floor,
Esc quits."""
import math

from ursina import Entity, Text, Vec3, application, camera, color, destroy, held_keys, time, window

from engine import Tower
from engine.problem import DIRS

from .block import Block
from .cat import Cat, available as cat_available
from .floor import Floor
from .liftscene import LiftScene
from .prowl import Prowlers
from .intro import Intro
from .world import FLOOR_H, aim_sun, move_lantern, point_camera

KEYS = {'left arrow': 'LEFT', 'right arrow': 'RIGHT', 'up arrow': 'DOWN', 'down arrow': 'UP'}
ROLL_S, DOORS_S, RIDE_S = 0.17, 0.6, 7.5
SKY = [(14, 17, 34), (16, 20, 40), (18, 22, 46), (20, 25, 52), (22, 28, 58)]   # night, lobby .. roof


def floor_name(index, count):
    """Bottom-up: LOBBY, FLOOR 1 .. FLOOR n, ROOFTOP."""
    if index == 0:
        return 'LOBBY'
    if index == count - 1:
        return 'ROOFTOP'
    return 'FLOOR {}'.format(index)


def _ease(t):
    return t * t * (3 - 2 * t)


def _mix(a, b, k):
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


class TowerGame(Entity):
    def __init__(self, sun):
        super().__init__()
        self.sun = sun
        self.tower = Tower()
        self.floor = Floor(self.tower.session, 0, self.tower.count)
        self.next_floor = None
        self.block = Block()
        self.phase, self.t = 'play', 0.0
        self.queued = None
        self.prowl, self.cut, self.cut_cat = None, None, None
        camera.fov = 42
        self._place_block()
        self._aim(self.floor)
        self.hud_name = Text('', position=window.top_left + Vec3(0.06, -0.05, 0), scale=2.2, color=color.white)
        self.hud_info = Text('', position=window.top_left + Vec3(0.065, -0.12, 0), scale=1.2,
                             color=color.rgb(255, 200, 87))
        self.banner = Text('', origin=(0, 0), scale=2.4, color=color.white, y=0.05)
        self.panel = Entity(parent=camera.ui, model='quad', color=color.rgba(20, 26, 44, 190), z=1,
                            scale=(0.5, 0.17), position=window.top_left + Vec3(0.27, -0.095, 0))
        self._hud()
        self.flash = Entity(parent=camera.ui, model='quad', scale=(4, 2), z=2, color=color.rgba(0, 0, 0, 0), enabled=False)
        self.over_text = Text('GAME OVER', origin=(0, 0), scale=4.4, y=0.08, z=-3, color=color.rgba(255, 240, 230, 0), enabled=False)
        self.over_sub = Text('press R to try again', origin=(0, 0), scale=1.6, y=-0.32, z=-3, color=color.rgba(235, 230, 220, 0), enabled=False)
        self.elev = LiftScene(self.sun)                      # the lift cutscene, shown while the car climbs
        self.intro = Intro(self.floor, self.tower.count, *self._camera_for(self.floor))
        self.intro.light(self.sun)
        self.phase = 'intro'
        self._show_hud(False)
        self._show_floor(False)                              # the lobby sits inside the intro's tower

    def _show_floor(self, on):
        self.floor.root.enabled = on
        for e in self.block.pieces:
            e.enabled = on
        for c in getattr(self.block, 'chars', []):
            c['shadow'].enabled = on

    # ---- helpers ----
    def _place_block(self):
        self.block.place(self.tower.session, self.tower.session.state, self.floor.base)

    def _player_pos(self, floor):
        pieces = self.block.pieces if floor is self.floor else []
        if not pieces:
            return floor.centre
        p = sum((e.position for e in pieces), Vec3(0)) / len(pieces)
        return Vec3(p.x, floor.base, p.z)

    def _camera_for(self, floor, focus=None):
        """A far, steep camera (about 60 degrees, like Rolling Cat) that keeps the whole floor in view and
        only leans a little towards the player."""
        focus = focus if focus is not None else self._player_pos(floor)
        c = floor.centre
        target = Vec3(c.x * 0.8 + focus.x * 0.2, floor.base + 0.4, c.z * 0.8 + focus.z * 0.2)
        dist = max(20.0, min(40.0, floor.span * 1.35 + 12.0))
        return target + Vec3(0, dist * 0.87, -dist * 0.5), target

    def _aim(self, floor):
        pos, target = self._camera_for(floor)
        camera.position = pos
        point_camera(camera, target)
        aim_sun(self.sun, target)
        k = floor.index / max(1, floor.count - 1)
        i = min(len(SKY) - 2, int(k * (len(SKY) - 1)))
        window.color = color.rgb(*_mix(SKY[i], SKY[i + 1], k * (len(SKY) - 1) - i))

    def _show_hud(self, on):
        for e in (self.hud_name, self.hud_info, self.panel):
            e.enabled = on

    def _hud(self):
        s = self.tower.session
        self.hud_name.text = floor_name(self.tower.index, self.tower.count)
        self.hud_info.text = 'LEVEL {} / {}     MOVES {}'.format(self.tower.index + 1, self.tower.count, s.moves)

    # ---- input ----
    def input(self, key):
        if key == 'escape':
            application.quit()
        if key == 'f':
            window.fullscreen = not window.fullscreen
        if self.phase == 'intro':
            if not key.endswith(' up'):
                self.intro.skip_or_enter()
            return
        if self.phase == 'roll' and (key in KEYS or key == 'space'):
            self.queued = key                                    # buffer one move so play feels responsive
            return
        if self.phase == 'over':
            if key in ('r', 'enter', 'space'):
                self._retry()
            return
        if self.phase != 'play':
            return
        s = self.tower.session
        before = s.state
        if key in KEYS or key == 'space':
            action = KEYS.get(key, 'SWITCH')
            if not s.move(action):
                if key in KEYS and self.prowl is not None:
                    self._fall(action)                       # off the path: onto the bare floor, where they are
                return
            if before.bridges != s.state.bridges:
                self.floor.refresh()
            if action != 'SWITCH' and self.block.start_roll(s, before, s.state, action, DIRS[action], self.floor.base):
                self.phase, self.t = 'roll', 0.0
            else:
                self._place_block()
                self._after_move()
        elif key == 'r':
            s.reset()
            self.floor.refresh()
            self._place_block()
            if self.prowl:
                self.prowl.reset()
        self._hud()

    # ---- falling off the path: the dead come for the bin ----
    def _spawn_prowlers(self):
        self.prowl = Prowlers(self.floor, count=4 + (1 if self.floor.index > 4 else 0), seed=self.floor.index)

    def _fall(self, action):
        s = self.tower.session
        if self.block.start_fall(s, s.state, action, DIRS[action], self.floor.base):
            self.phase, self.t = 'fall', 0.0

    def _bin_spot(self):
        pc = self.block.pieces[0].position
        return Vec3(pc.x, self.floor.base, pc.z)

    def _begin_swarm(self):
        self.swarm_centre = self._bin_spot()
        self.prowl.converge(self.swarm_centre)
        self.phase, self.t = 'swarm', 0.0

    VOID = Vec3(0, -800, 0)                                  # a black room far away for the game-over picture

    def _begin_bite(self):
        """The bin is surrounded. Swap the player piece for a bin with a loose lid; the cat stays hidden inside."""
        import builtins
        piece = self.block.pieces[0]
        self.cut = Entity(position=piece.position)
        self.cut.setQuat(builtins.render, piece.spinner.getQuat(builtins.render))
        self.cut_body = Entity(parent=self.cut, model='models/bin/bin_block_body')
        self.cut_lid = Entity(parent=self.cut, model='models/bin/bin_block_lid')
        for e in (self.cut_body, self.cut_lid):
            for m in e.findAllMaterials():
                m.setMetallic(0)
        piece.enabled = False
        self.cut_cat = Cat(parent=None, scale=2.8) if cat_available() else None
        if self.cut_cat:
            self.cut_cat.root.enabled = False
        self.cut_pos = Vec3(self.cut.position)
        self.void_on = False
        self.phase, self.t = 'bite', 0.0

    def _bite(self, dt):
        """0-0.5 they close in and the bin shakes; 0.5-1.3 the lid bursts off; 1.6-2.2 the picture goes black;
        then the cat lies still in the dark (see _over)."""
        t = self.t
        self.prowl.face(self.swarm_centre)
        self.prowl.lunge(min(1.0, t / 0.5))
        shake = math.sin(t * 60) * 0.05 * (1.0 if t < 1.4 else 0.0)
        self.cut.position = self.cut_pos + Vec3(shake, 0, -shake * 0.6)
        if t > 0.5:
            u = min(1.0, (t - 0.5) / 0.8)
            self.cut_lid.world_position = self.cut_pos + Vec3(1.8 * u, 3.4 * math.sin(math.pi * u) + 0.6 * u, -1.2 * u)
            self.cut_lid.rotation = (0, 0, 540 * u)
        cam_target = self.cut_pos + Vec3(0, 0.9, 0)
        cam_pos = self.cut_pos + Vec3(1.2, 4.2 - 0.6 * min(1.0, t / 1.5), -6.2 + 1.0 * min(1.0, t / 1.5))
        camera.position = camera.position + (cam_pos - camera.position) * min(1.0, dt * 3)
        point_camera(camera, cam_target)
        if t > 1.6:
            self.flash.enabled = True
            self.flash.color = color.rgba(0, 0, 0, int(255 * min(1.0, (t - 1.6) / 0.5)))
        if t > 2.2:                                          # black: move to the dark room, cat lying still in the middle
            self.void_on = True
            self._show_hud(False)
            window.color = color.black
            if self.cut_cat:
                c = self.cut_cat.root
                c.enabled = True
                c.position = self.VOID + Vec3(0.3, 0.1, 0)
                c.rotation = (0, 90, 0)                     # lying on its side, seen in profile
                self.cut_cat.show('Lie_idle', 0)
            camera.position = self.VOID + Vec3(0, 3.2, -7.0)
            point_camera(camera, self.VOID + Vec3(0, 0.3, 0))
            camera.fov = 32
            aim_sun(self.sun, self.VOID + Vec3(0, 0.4, 0))
            move_lantern(self.sun, self.VOID + Vec3(0, 0.2, 0.4))
            self.phase, self.t = 'over', 0.0

    @staticmethod
    def _bounce(k):
        """Ease-out bounce: drops, hits the ground, bounces twice."""
        k = max(0.0, min(1.0, k))
        if k < 1 / 2.75:
            return 7.5625 * k * k
        if k < 2 / 2.75:
            k -= 1.5 / 2.75
            return 7.5625 * k * k + 0.75
        if k < 2.5 / 2.75:
            k -= 2.25 / 2.75
            return 7.5625 * k * k + 0.9375
        k -= 2.625 / 2.75
        return 7.5625 * k * k + 0.984375

    def _over(self):
        """Out of the black, the cat lies there; GAME OVER drops in from the top of the screen."""
        t = self.t
        self.flash.color = color.rgba(0, 0, 0, int(255 * max(0.0, 1 - t / 0.5)))
        self.over_text.enabled = self.over_sub.enabled = True
        k = self._bounce((t - 0.5) / 1.0)
        self.over_text.y = 0.62 + (0.2 - 0.62) * k
        self.over_text.color = color.rgba(255, 240, 230, 255 if t > 0.5 else 0)
        self.over_sub.color = color.rgba(235, 230, 220, int(230 * max(0.0, min(1.0, (t - 1.8) / 0.5))))

    def _retry(self):
        s = self.tower.session
        if self.cut:
            destroy(self.cut)
        if self.cut_cat:
            self.cut_cat.destroy()
        self.cut = self.cut_cat = None
        self.flash.enabled = self.over_text.enabled = self.over_sub.enabled = False
        camera.fov = 42
        self._show_hud(True)
        s.reset()
        self.floor.refresh()
        self._place_block()
        self.prowl.reset()
        self._aim(self.floor)
        self.phase, self.t = 'play', 0.0
        self._hud()

    def _after_move(self):
        if self.tower.session.won:
            self.phase, self.t = 'close', 0.0

    # ---- per frame ----
    def update(self):
        dt = time.dt
        self.block.tick(dt, self.phase == 'play')
        self.floor.animate(time.time())
        if self.prowl and self.phase in ('play', 'roll', 'fall', 'swarm', 'bite', 'over'):
            self.prowl.update(dt)
        if self.phase in ('play', 'roll'):                    # camera and lantern follow the player smoothly
            pos, target = self._camera_for(self.floor)
            k = min(1.0, dt * 3.0)
            camera.position = camera.position + (pos - camera.position) * k
            prev = getattr(self, 'cam_target', target)
            self.cam_target = prev + (target - prev) * k
            point_camera(camera, self.cam_target)
            move_lantern(self.sun, self._player_pos(self.floor))
            aim_sun(self.sun, self.cam_target)
        if self.floor.beacon:
            self.floor.beacon.color = color.rgb(255, 60, 50) if int(time.time() * 1.6) % 2 else color.rgb(90, 30, 30)
        if self.phase == 'intro':
            self.intro.step(dt)
            if self.intro.done:
                self.intro.destroy()
                self._show_floor(True)
                self._aim(self.floor)
                self._show_hud(True)
                self._spawn_prowlers()
                self.phase = 'play'
        elif self.phase == 'fall':
            self.t += dt / self.block.duration
            self.block.set_progress(min(1.0, self.t))
            if self.t >= 1:
                self.block.finish()
                self._begin_swarm()
        elif self.phase == 'swarm':
            self.t += dt
            self.prowl.face(self.swarm_centre)
            cam_pos = self.swarm_centre + Vec3(0, 9.0, -10.5)
            k = min(1.0, dt * 2.5)
            camera.position = camera.position + (cam_pos - camera.position) * k
            point_camera(camera, self.swarm_centre + Vec3(0, 0.6, 0))
            if self.prowl.arrived or self.t > 6.0:
                self._begin_bite()
        elif self.phase == 'bite':
            self.t += dt
            self._bite(dt)
        elif self.phase == 'over':
            self.t += dt
            self._over()
        elif self.phase == 'roll':
            self.t += dt / self.block.duration
            self.block.set_progress(min(1.0, self.t))
            if self.t >= 1:
                self.block.finish()
                self.phase = 'play'
                self._after_move()
                self._hud()
                if self.queued and self.phase == 'play':     # a key pressed mid-move plays right after
                    key, self.queued = self.queued, None
                    self.input(key)
        elif self.phase == 'close':                                 # standing in the elevator: doors close
            self.t += dt / DOORS_S
            if self.floor.lift:
                self.floor.lift.set_open(1 - _ease(min(1.0, self.t)))
            if self.t >= 1:
                if self.tower.is_last:
                    self.phase = 'done'
                    self.banner.text = 'You made it to the roof!\n{} floors, {} moves'.format(
                        self.tower.count, self.tower.total_moves + self.tower.session.moves)
                    return
                for c in getattr(self.block, 'chars', []):
                    c['shadow'].enabled = False
                self.ride = [(e, Vec3(e.position)) for e in self.block.pieces] + [(self.floor.lift.root, Vec3(self.floor.lift.root.position))]
                self.tower.descend()                                # (Tower.descend = next level)
                self.next_floor = Floor(self.tower.session, self.tower.index, self.tower.count)
                # the new floor's arrival car stands on a different cell: the old car slides over to it while it rises
                car, new = self.floor.lift.root, self.next_floor.arrival.root
                self.ride_shift = (new.x - car.x, new.z - car.z)
                self.ride_yaw = ((new.rotation_y - car.rotation_y + 180) % 360 - 180, car.rotation_y)
                self.cam_from = (camera.position, self._camera_for(self.floor)[1])
                self.phase, self.t = 'ride', 0.0
                self._show_hud(False)
                self.elev.start(self.floor.index, self.next_floor.index, self.next_floor.roof)
        elif self.phase == 'ride':                                  # the car and the camera go up a storey
            self.t += dt / RIDE_S
            k = _ease(min(1.0, self.t))
            rise = (self.next_floor.base - self.floor.base) * k
            dx, dz = self.ride_shift
            for e, p0 in self.ride:
                e.position = Vec3(p0.x + dx * k, p0.y + rise, p0.z + dz * k)
            self.floor.lift.root.rotation_y = self.ride_yaw[1] + self.ride_yaw[0] * k
            pos, target = self._camera_for(self.next_floor)
            start_pos, start_target = self.cam_from
            camera.position = start_pos + (pos - start_pos) * k
            point_camera(camera, start_target + (target - start_target) * k)
            self.elev.update(min(1.0, self.t))                      # the cutscene takes the camera over
            if self.t >= 1:
                self.elev.hide()
                self._show_hud(True)
                self.prowl = None                               # they die with their floor
                self.floor.destroy()
                self.floor, self.next_floor = self.next_floor, None
                self._spawn_prowlers()
                self._aim(self.floor)
                self._place_block()
                self.phase, self.t = 'open', 0.0
                self._hud()
        elif self.phase == 'open':                                  # arrival doors slide open
            self.t += dt / DOORS_S
            if self.floor.arrival:
                self.floor.arrival.set_open(_ease(min(1.0, self.t)))
            if self.t >= 1:
                self.phase = 'play'
