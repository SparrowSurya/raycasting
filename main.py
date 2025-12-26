import math
import pygame as pg
from typing import Tuple, List


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
    (1, 0, 1, 0, 0, 0, 0, 1),
    (1, 0, 1, 0, 0, 0, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 1),
    (1, 1, 1, 1, 1, 1, 1, 1),
)

SIZE = WIDTH // len(MAP[0])

# TYPES
# --------------------------------------------------------------------------------------

_Color = Tuple[int, int, int]


# CLASSSES
# --------------------------------------------------------------------------------------

class PgUtil:

    @staticmethod
    def to_pg_coord(x: float, y: float):
        return x, HEIGHT-y

class Vec2:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    @classmethod
    def uniform(cls, v: float):
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
            self.angle += 2 * math.pi

    def rotate_left(self):
        self.angle += self.rvel
        if self.angle >= 2 * math.pi:
            self.angle -= 2 * math.pi

    def draw(self, screen: pg.Surface):
        local_points = ( 9,  0), (-4,  4), (-4, -4)
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        height = screen.get_height()
        points: List[Tuple[float, float]] = []

        for lx, ly in local_points:
            wx = self.pos.x + (lx * cos_a - ly * sin_a)
            wy = self.pos.y + (lx * sin_a + ly * cos_a)
            points.append((wx, height - wy))

        pg.draw.polygon(screen, self.color, points)


# SETUP
# --------------------------------------------------------------------------------------

pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
clock = pg.time.Clock()
running = True

player = Player(
    pos=Vec2(200, 300),
    angle=math.pi/2,
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
        player.rotate_left()
    if keys[pg.K_RIGHT]:
        player.rotate_right()
    if keys[pg.K_UP]:
        player.move_ahead()
    if keys[pg.K_DOWN]:
        player.move_back()


    screen.fill(GREY)
    for i in range(len(MAP)):
        for j in range(len(MAP[i])):
            color = WHITE if MAP[i][j] == 1 else BLACK
            pg.draw.rect(screen, color, (SIZE*j+1, SIZE*i+1, SIZE-1, SIZE-1))
    player.draw(screen)
    pg.display.flip()
    clock.tick(FPS)


# EXIT
# --------------------------------------------------------------------------------------

pg.quit()
