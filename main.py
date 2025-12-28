import math
import pygame as pg
from functools import cached_property
from typing import Tuple, List, Optional, Sequence


# CONSTANTS
# --------------------------------------------------------------------------------------
FPS = 30
HEIGHT = 540
WIDTH = HEIGHT

WHITE  = (0xFF, 0xFF, 0xFF)
BLACK  = (0x00, 0x00, 0x00)
GREY   = (0xA0, 0xA0, 0xA0)
RED    = (0xFF, 0x00, 0x00)
YELLOW = (0xFF, 0xFF, 0x00)

MAP = (
    (1, 1, 1, 1, 1, 1, 1, 1),
    (1, 0, 1, 0, 0, 0, 0, 1),
    (1, 0, 1, 0, 0, 1, 0, 1),
    (1, 0, 1, 0, 0, 1, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 1),
    (1, 0, 0, 0, 1, 0, 0, 1),
    (1, 1, 1, 1, 1, 1, 1, 1),
)

TILE_SIZE = WIDTH // len(MAP[0])
MAX_DIST = math.sqrt(WIDTH**2 + HEIGHT**2)
HFOV = 30
FOV = HFOV*2
RAY_RES = 36

# TYPES
# --------------------------------------------------------------------------------------

_Color = Tuple[int, int, int]


# FUNCTIONS
# --------------------------------------------------------------------------------------

def raycast(pos: Vec2, angle: float, tilemap: TileMap) -> Optional[Vec2]:
    dx = math.cos(angle)
    dy = math.sin(angle)

    map_x, map_y = tilemap.tile_coord(pos.x, pos.y)

    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    if dx != 0:
        next_vx = (map_x + (dx > 0)) * tilemap.size
        t_v = (next_vx - pos.x) / dx
        dt_v = tilemap.size / abs(dx)
    else:
        t_v = float("inf")
        dt_v = float("inf")

    if dy != 0:
        next_hy = (map_y + (dy > 0)) * tilemap.size
        t_h = (next_hy - pos.y) / dy
        dt_h = tilemap.size / abs(dy)
    else:
        t_h = float("inf")
        dt_h = float("inf")

    t = 0.0
    while t < tilemap.max_dist:
        if t_v < t_h:
            t = t_v
            t_v += dt_v
            map_x += step_x
        else:
            t = t_h
            t_h += dt_h
            map_y += step_y

        try:
            if tilemap.is_obstacle(map_x, map_y, is_tiled=True):
                hit_x = pos.x + t * dx
                hit_y = pos.y + t * dy
                return Vec2(hit_x, hit_y)
        except IndexError:
            return None

    return None


def draw_triangle(surface: pg.Surface, pos: Vec2, angle: float, color: _Color):
    local_points = ( 9,  0), (-4,  4), (-4, -4)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    points: List[Tuple[float, float]] = []

    for lx, ly in local_points:
        wx = pos.x + (lx * cos_a - ly * sin_a)
        wy = pos.y + (lx * sin_a + ly * cos_a)
        points.append((wx, wy))

    pg.draw.polygon(surface, color, points)


# CLASSSES
# --------------------------------------------------------------------------------------

class TileMap:
    def __init__(self, map: Sequence[Sequence[int]], size: float):
        self._map = map
        self.size = size

    @cached_property
    def max_dist(self) -> float:
        width = self.cols * self.size
        height = self.rows * self.size
        return math.sqrt(width**2 + height**2)

    @cached_property
    def rows(self) -> int:
        return len(self._map)

    @cached_property
    def cols(self) -> int:
        return len(self._map[0])

    def is_obstacle(self, x: float, y: float, is_tiled: bool = False) -> bool:
        tile_x, tile_y = (int(x), int(y)) if is_tiled else self.tile_coord(x, y)
        return self._map[tile_y][tile_x] == 1

    def tile_coord(self, x: float, y: float) -> Tuple[int, int]:
        return int(x // self.size), int(y // self.size)


class Vec2:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    @classmethod
    def uniform(cls, v: float = 0.0):
        return cls(v, v)

    def move_by(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    def as_tuple(self):
        return self.x, self.y


class Player:
    def __init__(self, pos: Vec2, angle: float, vel: float, rvel: float, fov: float, color: _Color):
        self.pos = pos
        self.angle = angle
        self.vel = vel
        self.rvel = rvel
        self.fov = fov
        self.color = color

    def move_ahead(self):
        self.pos = Vec2(
            self.pos.x + self.vel * math.cos(self.angle),
            self.pos.y + self.vel * math.sin(self.angle),
        )

    def move_back(self):
        self.pos = Vec2(
            self.pos.x - self.vel * math.cos(self.angle),
            self.pos.y - self.vel * math.sin(self.angle),
        )

    def rotate_right(self):
        self.angle -= self.rvel
        if self.angle < 0:
            self.angle += math.tau

    def rotate_left(self):
        self.angle += self.rvel
        if self.angle >= math.tau:
            self.angle -= math.tau

    def draw(self, screen: pg.Surface):
        draw_triangle(screen, self.pos, self.angle, self.color)


class RayCaster:
    def __init__(self, player: Player, fov: float, color: Optional[_Color] = None):
        self.player = player
        self.fov = fov
        self.color = color

    def render(self, surface: pg.Surface, tilemap: TileMap, res: int):
        color = self.color or self.player.color
        rays = self.cast_rays(tilemap, res)
        for ray in rays:
            pg.draw.line(surface, color, player.pos.as_tuple(), ray.as_tuple())

    def cast_rays(self, tilemap: TileMap, res: int) -> Sequence[Vec2]:
        pos = self.player.pos
        angle = self.player.angle
        rays: List[Vec2] = []

        center_hit = raycast(pos, angle, tilemap)
        if center_hit is not None:
            rays.append(center_hit)

        if res > 1:
            fov = math.radians(self.fov)
            half = res // 2
            step = fov / (res - 1)

            for i in range(1, half + 1):
                a = angle + i * step
                hit = raycast(pos, a, tilemap)
                if hit is not None:
                    rays.append(hit)

            for i in range(1, half + 1):
                a = angle - i * step
                hit = raycast(pos, a, tilemap)
                if hit is not None:
                    rays.append(hit)

        return rays


# SETUP
# --------------------------------------------------------------------------------------

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
mini_map = pg.surface.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
clock = pg.time.Clock()
running = True

tilemap = TileMap(MAP, TILE_SIZE)
player = Player(
    pos=Vec2(400, 360),
    angle=math.pi*1.5,
    vel=4,
    rvel=math.radians(5),
    fov=FOV,
    color=RED,
)
raycaster = RayCaster(player, FOV, YELLOW)



# MAINLOOP
# --------------------------------------------------------------------------------------

while running:

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False

    keys = pg.key.get_pressed()

    if keys[pg.K_LEFT]:
        player.rotate_right()
    if keys[pg.K_RIGHT]:
        player.rotate_left()
    if keys[pg.K_UP]:
        pos = player.pos
        player.move_ahead()
        if tilemap.is_obstacle(*player.pos.as_tuple()):
            player.pos = pos
    if keys[pg.K_DOWN]:
        pos = player.pos
        player.move_back()
        if tilemap.is_obstacle(*player.pos.as_tuple()):
            player.pos = pos

    screen.fill(GREY)
    mini_map.fill(GREY)
    for i in range(len(MAP)):
        for j in range(len(MAP[i])):
            color = WHITE if MAP[i][j] == 1 else BLACK
            pg.draw.rect(mini_map, color, (TILE_SIZE*j+1, TILE_SIZE*i+1, TILE_SIZE-1, TILE_SIZE-1))
    raycaster.render(mini_map, tilemap, RAY_RES)
    player.draw(mini_map)
    screen.blit(mini_map)
    pg.display.flip()
    clock.tick(FPS)


# EXIT
# --------------------------------------------------------------------------------------

pg.quit()
