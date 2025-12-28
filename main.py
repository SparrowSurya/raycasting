import math
import pygame as pg
from functools import cached_property
from typing import Tuple, List, Optional, Sequence


# CONSTANTS
# --------------------------------------------------------------------------------------
FPS = 30
SCREEN_HEIGHT = 640
SCREEN_WIDTH = SCREEN_HEIGHT

WHITE : _Color = (0xFF, 0xFF, 0xFF)
BLACK : _Color = (0x00, 0x00, 0x00)
GREY  : _Color = (0xA0, 0xA0, 0xA0)
RED   : _Color = (0xFF, 0x00, 0x00)
YELLOW: _Color = (0xFF, 0xFF, 0x00)
PINK  : _Color = (0xFF, 0xC0, 0xCB)

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

MAP_ROWS = len(MAP)
MAP_COLS = len(MAP[0])
MINIMAP_HEIGHT = 540
MINIMAP_WIDTH = MINIMAP_HEIGHT
MINIMAP_TILE_SIZE = min(MINIMAP_HEIGHT//MAP_ROWS, MINIMAP_WIDTH//MAP_COLS)
MINIMAP_SCALE = 0.5

TILE_SIZE = SCREEN_WIDTH // len(MAP[0])
MAX_DIST = math.sqrt(MINIMAP_WIDTH**2 + MINIMAP_HEIGHT**2)
FOV = math.radians(60)
RESOLUTION = 64

SCENE_HEIGHT = 360
SCENE_WIDTH = SCENE_HEIGHT+200
DIST_SCALE = 0.02
COL_SCALE = 1.25

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


def cast_rays(
    player: Player,
    tilemap: TileMap,
    fov: float,
    res: int,
) -> Sequence[Tuple[Vec2, float]]:
    pos = player.pos
    angle = player.angle
    rays: List[Tuple[Vec2, float]] = []

    start_angle = angle + fov / 2
    step = fov / (res - 1)

    for i in range(res):
        ray_angle = start_angle - i * step
        hit = raycast(pos, ray_angle, tilemap)
        if hit is not None:
            rays.append((hit, ray_angle))

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
    surface.fill(GREY)
    for y in range(MAP_ROWS):
        for x in range(MAP_COLS):
            color = WHITE if tilemap.at(x, y) else BLACK
            rect = (
                MINIMAP_TILE_SIZE*x,
                MINIMAP_TILE_SIZE*y,
                MINIMAP_TILE_SIZE,
                MINIMAP_TILE_SIZE,
            )
            pg.draw.rect(surface, color, rect)


def draw_rays(surface: pg.Surface, pos: Vec2, rays: Sequence[Vec2], color: _Color):
    for ray in rays:
        pg.draw.line(surface, color, pos.as_tuple(), ray.as_tuple())


def draw_3d(
    surface: pg.Surface,
    rays: Sequence[Tuple[Vec2, float]],
    pos: Vec2,
    angle: float,
):
    screen_w, screen_h = surface.get_size()
    column_w = screen_w / len(rays)

    for i, (hit, ray_angle) in enumerate(rays):
        dist = pos.dist(hit) * DIST_SCALE
        if dist <= 0:
            continue

        perp_dist = dist * math.cos(ray_angle - angle)
        if perp_dist <= 0:
            continue

        height = (screen_h * COL_SCALE) / perp_dist
        top = (screen_h - height) / 2
        rect = (i*column_w, top, column_w+1, height)
        pg.draw.rect(surface, PINK, rect)


# CLASSSES
# --------------------------------------------------------------------------------------

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

    def at(self, x: int, y: int) -> int:
        return self._map[y][x]

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

    def dist(self, other: Vec2) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx**2 + dy**2)

    def __str__(self) -> str:
        return f"Vec2({self.x:.2}, {self.y:.2})"

    __repr__ = __str__


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

minimap = TileMap(MAP, MINIMAP_TILE_SIZE)
player = Player(
    pos=minimap.get_point(0.6, 0.6),
    angle=math.pi*1.5,
    vel=3,
    rvel=math.radians(5),
    fov=FOV,
    color=RED,
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

    keys = pg.key.get_pressed()

    if keys[pg.K_LEFT]:
        player.rotate_right()
    if keys[pg.K_RIGHT]:
        player.rotate_left()
    if keys[pg.K_UP]:
        pos = player.pos
        player.move_ahead()
        if minimap.is_obstacle(*player.pos.as_tuple()):
            player.pos = pos
    if keys[pg.K_DOWN]:
        pos = player.pos
        player.move_back()
        if minimap.is_obstacle(*player.pos.as_tuple()):
            player.pos = pos


    screen_surface.fill(GREY)
    rays = cast_rays(player, minimap, FOV, RESOLUTION)
    scene_surface.fill(BLACK)
    draw_3d(scene_surface, rays, player.pos, player.angle)
    scene_pos = (SCREEN_WIDTH-SCENE_WIDTH)/2, (SCREEN_HEIGHT-SCENE_HEIGHT)/2
    screen_surface.blit(scene_surface, scene_pos)
    if show_minimap:
        draw_minimap(minimap_surface, minimap)
        if show_rays:
            draw_rays(minimap_surface, player.pos, [ray[0] for ray in rays], YELLOW)
        player.draw(minimap_surface, 2.0)
        sized_minimap = pg.transform.scale_by(minimap_surface, MINIMAP_SCALE)
        minimap_pos = (SCREEN_WIDTH-MINIMAP_WIDTH*MINIMAP_SCALE, 0)
        sized_minimap.set_alpha(100)
        screen_surface.blit(sized_minimap, minimap_pos)
    pg.display.flip()
    clock.tick(FPS)


# EXIT
# --------------------------------------------------------------------------------------

pg.quit()
