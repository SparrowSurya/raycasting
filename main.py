import math
from enum import IntEnum, auto
import pygame as pg
from functools import cached_property
from typing import Tuple, List, Optional, Sequence


# CONSTANTS
# --------------------------------------------------------------------------------------

WHITE : _Color = (0xFF, 0xFF, 0xFF)
BLACK : _Color = (0x00, 0x00, 0x00)
GREY  : _Color = (0xA0, 0xA0, 0xA0)
RED   : _Color = (0xFF, 0x00, 0x00)
YELLOW: _Color = (0xFF, 0xFF, 0x00)
PINK  : _Color = (0xFF, 0xC0, 0xCB)

MAP = (
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    (1, 0, 1, 0, 0, 0, 0, 0, 0, 1),
    (1, 0, 1, 0, 0, 1, 1, 0, 0, 1),
    (1, 0, 1, 0, 0, 1, 1, 0, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    (0, 0, 0, 0, 0, 0, 0, 1, 0, 1),
    (1, 0, 0, 0, 1, 0, 0, 0, 0, 1),
    (1, 1, 1, 1, 1, 1, 1, 0, 1, 1),
)


MAP_ROWS = len(MAP)
MAP_COLS = len(MAP[0])

SCREEN_HEIGHT = 600
SCREEN_WIDTH = 800

MINIMAP_UNIT_SIZE = 60
MINIMAP_HEIGHT = MAP_ROWS * MINIMAP_UNIT_SIZE
MINIMAP_WIDTH = MAP_COLS * MINIMAP_UNIT_SIZE
MINIMAP_SCALE = 0.3
MINIMAP_ALPHA = 255

TILE_SIZE = SCREEN_WIDTH // len(MAP[0])
MAX_DIST = math.sqrt(MINIMAP_WIDTH**2 + MINIMAP_HEIGHT**2)
FOV = math.radians(60)
RESOLUTION = 64

SCENE_HEIGHT = SCREEN_HEIGHT
SCENE_WIDTH = SCREEN_WIDTH
DIST_SCALE = 0.04
COL_SCALE = 1.2

FPS = 30

# TYPES
# --------------------------------------------------------------------------------------

_Color = Tuple[int, int, int]


# FUNCTIONS
# --------------------------------------------------------------------------------------

def raycast(pos: Vec2, angle: float, tilemap: TileMap) -> Optional[Ray]:
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
            side = Side.LEFT if dx > 0 else Side.RIGHT
        else:
            t = t_h
            t_h += dt_h
            map_y += step_y
            side = Side.UP if dy > 0 else Side.DOWN

        try:
            if tilemap.is_obstacle(map_x, map_y, is_tiled=True):
                hit_x = pos.x + t * dx
                hit_y = pos.y + t * dy
                return Ray(
                    hit=Vec2(hit_x, hit_y),
                    tile_x=map_x,
                    tile_y=map_y,
                    side=side,
                    angle=angle,
                )
        except IndexError:
            return None

    return None


def cast_rays(
    player: Player,
    tilemap: TileMap,
    fov: float,
    res: int,
) -> Sequence[Optional[Ray]]:
    pos = player.pos
    angle = player.angle
    rays: List[Optional[Ray]] = []

    start_angle = angle + fov / 2
    step = fov / (res - 1)

    for i in range(res):
        ray_angle = start_angle - i * step
        ray = raycast(pos, ray_angle, tilemap)
        rays.append(ray)

    rays.reverse()
    return rays


def draw_triangle(
    surface: pg.Surface,
    pos: Vec2,
    angle: float,
    color: _Color,
    scale: float = 1.0,
):
    local_points = ( 9,  0), (-6,  6), (-6, -6)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    points: List[Tuple[float, float]] = []

    for lx, ly in local_points:
        wx = pos.x + (lx * cos_a - ly * sin_a) * scale
        wy = pos.y + (lx * sin_a + ly * cos_a) * scale
        points.append((wx, wy))

    pg.draw.polygon(surface, color, points)


def draw_minimap(surface: pg.Surface, tilemap: TileMap):
    surface.fill(BLACK)
    color = GREY
    for y in range(MAP_ROWS):
        for x in range(MAP_COLS):
            rect = (
                MINIMAP_UNIT_SIZE*x,
                MINIMAP_UNIT_SIZE*y,
                MINIMAP_UNIT_SIZE,
                MINIMAP_UNIT_SIZE,
            )
            if tilemap.is_obstacle(x, y, is_tiled=True):
                pg.draw.rect(surface, color, rect)
            else:
                pg.draw.rect(surface, color, rect, width=2)


def draw_rays(surface: pg.Surface, pos: Vec2, rays: Sequence[Optional[Ray]], color: _Color):
    for ray in rays:
        if ray is None:
            continue
        pg.draw.line(surface, color, pos.as_tuple(), ray.hit.as_tuple())


def draw_3d(
    surface: pg.Surface,
    tilemap: TileMap,
    rays: Sequence[Optional[Ray]],
    pos: Vec2,
    angle: float,
):
    screen_w, screen_h = surface.get_size()
    column_w = screen_w / len(rays)

    for i, ray in enumerate(rays):
        if ray is None:
            continue

        dist = pos.dist(ray.hit) * DIST_SCALE
        if dist <= 0:
            continue

        perp_dist = dist * math.cos(ray.angle - angle)
        if perp_dist <= 0:
            continue

        height = (screen_h * COL_SCALE) / perp_dist
        top = (screen_h - height) / 2
        rect = (i*column_w, top, column_w+1, height)
        pg.draw.rect(surface, PINK , rect)


# CLASSSES
# --------------------------------------------------------------------------------------

class Side(IntEnum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class TileMap:
    def __init__(self, map: Sequence[Sequence[int]], size: float):
        self._map = map
        self.size = size

    @cached_property
    def max_dist(self) -> float:
        return math.sqrt(self.width**2 + self.height**2)

    @cached_property
    def rows(self) -> int:
        return len(self._map)

    @cached_property
    def cols(self) -> int:
        return len(self._map[0])

    @cached_property
    def width(self) -> float:
        return self.cols * self.size

    @cached_property
    def height(self) -> float:
        return self.rows * self.size

    def get_point(self, nx: float, ny: float) -> Vec2:
        return Vec2(self.width*nx, self.height*ny)

    def inside(self, x: float, y: float, is_tiled: bool = False) -> bool:
        tile_x, tile_y = (int(x), int(y)) if is_tiled else self.tile_coord(x, y)
        return 0 <= tile_x < self.cols and 0 <= tile_y < self.rows

    def get(self, x: int, y: int) -> int:
        if self.inside(x, y, is_tiled=True):
            return self._map[y][x]
        return 0

    def is_obstacle(self, x: float, y: float, is_tiled: bool = False) -> bool:
        tile_x, tile_y = (int(x), int(y)) if is_tiled else self.tile_coord(x, y)
        if self.inside(tile_x, tile_y, is_tiled=True):
            return self._map[tile_y][tile_x] != 0
        return False

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

    def dist(self, other: Vec2) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx**2 + dy**2)

    def __str__(self) -> str:
        return f"Vec2({self.x:.2}, {self.y:.2})"

    __repr__ = __str__


class Ray:
    def __init__(self, hit: Vec2, tile_x: int, tile_y: int, angle: float, side: Side):
        self.hit = hit
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.angle = angle
        self.side = side

class Player:
    def __init__(self,
        pos: Vec2,
        angle: float,
        vel: float,
        rvel: float,
        fov: float,
        color: _Color,
    ):
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

    def draw(self, screen: pg.Surface, scale: float = 1.0):
        draw_triangle(screen, self.pos, self.angle, self.color, scale)


# SETTINGS
# --------------------------------------------------------------------------------------

show_minimap = True
show_rays = False

# SETUP
# --------------------------------------------------------------------------------------

pg.init()
screen_surface = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
minimap_surface = pg.surface.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT), pg.SRCALPHA)
scene_surface = pg.surface.Surface((SCENE_WIDTH, SCENE_HEIGHT), pg.SRCALPHA)
clock = pg.time.Clock()
running = True

tilemap = TileMap(MAP, MINIMAP_UNIT_SIZE)
player = Player(
    pos=tilemap.get_point(0.6, 0.6),
    angle=math.pi*1.5,
    vel=2,
    rvel=math.radians(5),
    fov=FOV,
    color=YELLOW,
)


# MAINLOOP
# --------------------------------------------------------------------------------------

while running:

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_x:
                show_minimap = not show_minimap
            if event.key == pg.K_r:
                show_rays = not show_rays
            if event.key == pg.K_q:
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

    screen_surface.fill(GREY)
    rays = cast_rays(player, tilemap, FOV, RESOLUTION)
    scene_surface.fill(BLACK)
    draw_3d(scene_surface, tilemap, rays, player.pos, player.angle)
    scene_pos = (SCREEN_WIDTH-SCENE_WIDTH)/2, (SCREEN_HEIGHT-SCENE_HEIGHT)/2
    screen_surface.blit(scene_surface, scene_pos)
    if show_minimap:
        draw_minimap(minimap_surface, tilemap)
        if show_rays:
            draw_rays(minimap_surface, player.pos, rays, YELLOW)
        player.draw(minimap_surface, 2.0)
        sized_minimap = pg.transform.scale_by(minimap_surface, MINIMAP_SCALE)
        minimap_pos = (SCREEN_WIDTH-MINIMAP_WIDTH*MINIMAP_SCALE, 0)
        sized_minimap.set_alpha(MINIMAP_ALPHA)
        screen_surface.blit(sized_minimap, minimap_pos)
    pg.display.flip()
    clock.tick(FPS)


# EXIT
# --------------------------------------------------------------------------------------

pg.quit()
