import math
import pygame as pg
from typing import Tuple, List, Optional


# CONSTANTS
# --------------------------------------------------------------------------------------
FPS = 30
HEIGHT = 540
WIDTH = HEIGHT

WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0x00, 0x00, 0x00)
GREY  = (0xA0, 0xA0, 0xA0)
RED   = (0xFF, 0x00, 0x00)

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

# TYPES
# --------------------------------------------------------------------------------------

_Color = Tuple[int, int, int]


# FUNCTIONS
# --------------------------------------------------------------------------------------

def raycast(pos: Vec2, angle: float) -> Optional[Vec2]:
    dx = math.cos(angle)
    dy = math.sin(angle)

    map_x = int(pos.x // TILE_SIZE)
    map_y = int(pos.y // TILE_SIZE)

    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1

    if dx != 0:
        next_vx = (map_x + (dx > 0)) * TILE_SIZE
        t_v = (next_vx - pos.x) / dx
        dt_v = TILE_SIZE / abs(dx)
    else:
        t_v = float("inf")
        dt_v = float("inf")

    if dy != 0:
        next_hy = (map_y + (dy > 0)) * TILE_SIZE
        t_h = (next_hy - pos.y) / dy
        dt_h = TILE_SIZE / abs(dy)
    else:
        t_h = float("inf")
        dt_h = float("inf")

    t = 0.0
    while t < MAX_DIST:
        if t_v < t_h:
            t = t_v
            t_v += dt_v
            map_x += step_x
        else:
            t = t_h
            t_h += dt_h
            map_y += step_y

        try:
            if MAP[map_y][map_x] == 1:
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

class PgUtil:

    @staticmethod
    def to_pg_coord(x: float, y: float):
        return x, HEIGHT-y


class Vec2:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    @classmethod
    def uniform(cls, v: float = 0.0):
        return cls(v, v)

    def set(self, x: float, y: float):
        self.x = x
        self.y = y

    def move_by(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    def as_tuple(self):
        return self.x, self.y


class Player:
    def __init__(self, pos: Vec2, angle: float, vel: float, rvel: float, color: _Color):
        self.pos = pos
        self.angle = angle
        self.vel = vel
        self.rvel = rvel
        self.color = color

    def move_ahead(self):
        self.pos.set(
            self.pos.x + self.vel * math.cos(self.angle),
            self.pos.y + self.vel * math.sin(self.angle),
        )

    def move_back(self):
        self.pos.set(
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


# SETUP
# --------------------------------------------------------------------------------------

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
mini_map = pg.surface.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
clock = pg.time.Clock()
running = True

player = Player(
    pos=Vec2(400, 360),
    angle=math.pi*1.5,
    vel=4,
    rvel=math.radians(5),
    color=RED,
)


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
        player.move_ahead()
    if keys[pg.K_DOWN]:
        player.move_back()

    screen.fill(GREY)
    mini_map.fill(GREY)

    for i in range(len(MAP)):
        for j in range(len(MAP[i])):
            color = WHITE if MAP[i][j] == 1 else BLACK
            pg.draw.rect(mini_map, color, (TILE_SIZE*j+1, TILE_SIZE*i+1, TILE_SIZE-1, TILE_SIZE-1))
    player.draw(mini_map)

    for da in range(-HFOV, HFOV):
        ray = raycast(player.pos, player.angle + math.radians(da))
        if ray is not None:
            pg.draw.line(mini_map, RED, player.pos.as_tuple(), ray.as_tuple())

    screen.blit(mini_map)
    pg.display.flip()
    clock.tick(FPS)


# EXIT
# --------------------------------------------------------------------------------------

pg.quit()
