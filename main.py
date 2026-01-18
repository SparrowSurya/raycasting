import math
import pathlib
from enum import IntEnum, StrEnum, auto
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
GREEN : _Color = (0x00, 0xFF, 0x00)

MAP = (
    (1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    (1, 0, 1, 0, 0, 0, 0, 0, 0, 1),
    (1, 0, 1, 0, 0, 1, 1, 0, 0, 1),
    (1, 0, 1, 0, 0, 1, 1, 0, 0, 1),
    (1, 0, 0, 0, 0, 0, 0, 0, 0, 1),
    (0, 0, 0, 0, 0, 0, 0, 1, 0, 1),
    (1, 0, 0, 0, 1, 0, 0, 0, 0, 1),
    (1, 1, 1, 1, 1, 1, 0, 1, 1, 1),
)


MAP_ROWS = len(MAP)
MAP_COLS = len(MAP[0])

SCREEN_HEIGHT = int(480 * 1.25)
SCREEN_WIDTH = int(640 * 1.25)

TILE_SIZE = 32
VIEW_DISTANCE = 256
FOV = math.radians(60)
RESOLUTION = 4
COLLISSION_RADIUS = 4
PLAYER_VEL = 2
PLAYER_RVEL = math.radians(5)

SCENE_HEIGHT = MAP_ROWS * TILE_SIZE
SCENE_WIDTH = MAP_COLS * TILE_SIZE
MINIMAP_HEIGHT = MAP_ROWS * TILE_SIZE
MINIMAP_WIDTH = MAP_COLS * TILE_SIZE
RAYS_COUNT = int(SCENE_WIDTH // RESOLUTION)
MINIMAP_ALPHA = 255
MINIMAP_SCALE = 0.5

FPS = 30

ASSET_PATH = "assets"

# TYPES
# --------------------------------------------------------------------------------------

_Color = Tuple[int, int, int]


# FUNCTIONS
# --------------------------------------------------------------------------------------


def load_asset(kind: AssetType, name: str, asset_path: str = ASSET_PATH) -> pg.Surface:
    file_path = pathlib.Path(asset_path, kind, name)
    return pg.image.load(file_path)


def normalize_angle(angle: float) -> float:
    angle = angle % math.tau
    if angle <= 0:
        angle = math.tau + angle
    return angle


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
    while t < tilemap.max_distance:
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
                hit = Vec2(x = pos.x+ t * dx, y = pos.y + t * dy)
                return Ray(
                    hit=hit,
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
    rays_count: int,
) -> Sequence[Optional[Ray]]:
    pos = player.pos
    angle = player.angle
    rays: List[Optional[Ray]] = []

    ray_angle = angle - fov / 2
    for _ in range(rays_count):
        ray = raycast(pos, ray_angle, tilemap)
        rays.append(ray)
        ray_angle += fov / rays_count

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
                TILE_SIZE*x,
                TILE_SIZE*y,
                TILE_SIZE,
                TILE_SIZE,
            )
            if tilemap.is_obstacle(x, y, is_tiled=True):
                pg.draw.rect(surface, color, rect)
            pg.draw.rect(surface, BLACK, rect, width=2)


def draw_rays(surface: pg.Surface, pos: Vec2, rays: Sequence[Optional[Ray]], color: _Color):
    for ray in rays:
        if ray is None:
            continue
        pg.draw.line(surface, color, pos.as_tuple(), ray.hit.as_tuple())


def draw_max_distance(surface: pg.Surface, pos: Vec2, angle: float, distance: float):
    x1 = pos.x + distance * math.cos(angle)
    y1 = pos.y + distance * math.sin(angle)
    pg.draw.line(surface, GREEN, pos.as_tuple(), (x1, y1))


def draw_walls(
    surface: pg.Surface,
    tilemap: TileMap,
    rays,
    pos: Vec2,
    angle: float,
    fov: float,
    wall_tex: pg.Surface,
):
    surface_w, surface_h = surface.get_size()
    col_w = surface_w / len(rays)
    proj_dist = (surface_w / 2) / math.tan(fov / 2)

    tex_w, tex_h = wall_tex.get_size()

    for i, ray in enumerate(rays):
        if ray is None:
            continue

        dist = pos.dist(ray.hit) * math.cos(ray.angle - angle)
        if dist <= 0:
            continue

        height = (tilemap.size / dist) * proj_dist
        height = min(height, 1000)
        y = (surface_h - height) / 2

        if ray.side.is_vertical():
            offset = ray.hit.x % tilemap.size
        else:
            offset = ray.hit.y % tilemap.size

        tex_x = int(offset / tilemap.size * tex_w)
        tex_x = max(0, min(tex_w - 1, tex_x))

        column = wall_tex.subsurface(tex_x, 0, 1, tex_h)
        column = pg.transform.scale(column, (int(col_w) + 1, int(height)))

        t = min(dist / tilemap.max_distance, 1.0)
        shade = int(255 * (1 - t))
        column.fill((shade, shade, shade), special_flags=pg.BLEND_MULT)

        surface.blit(column, (i * col_w, y))


# CLASSSES
# --------------------------------------------------------------------------------------


class AssetType(StrEnum):
    TEXTURE = "textures"

class Side(IntEnum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    def is_vertical(self) -> bool:
        return self in (Side.UP, Side.DOWN)

    def is_horizontal(self) -> bool:
        return self in (Side.LEFT, Side.RIGHT)


class TileMap:
    def __init__(self, map: Sequence[Sequence[int]], size: float, max_distance: float):
        self._map = map
        self.size = size
        self.max_distance = max_distance

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

    def collides(self, pos: Vec2, radius: float) -> bool:
        points = [
            Vec2(pos.x - radius, pos.y),
            Vec2(pos.x + radius, pos.y),
            Vec2(pos.x, pos.y - radius),
            Vec2(pos.x, pos.y + radius),
        ]
        return any(self.is_obstacle(p.x, p.y, is_tiled=False) for p in points)



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
    def __init__(self,
        hit: Vec2,
        tile_x: int,
        tile_y: int,
        angle: float,
        side: Side,
    ):
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
        radius: float,
        color: _Color,
    ):
        self.pos = pos
        self.angle = angle
        self.vel = vel
        self.rvel = rvel
        self.fov = fov
        self.radius = radius
        self.color = color

    def move_ahead(self) -> Player:
        self.pos = Vec2(
            self.pos.x + self.vel * math.cos(self.angle),
            self.pos.y + self.vel * math.sin(self.angle),
        )
        return self

    def move_back(self) -> Player:
        self.pos = Vec2(
            self.pos.x - self.vel * math.cos(self.angle),
            self.pos.y - self.vel * math.sin(self.angle),
        )
        return self

    def rotate_right(self) -> Player:
        self.angle = normalize_angle(self.angle - self.rvel)
        return self

    def rotate_left(self) -> Player:
        self.angle = normalize_angle(self.angle + self.rvel)
        return self

    def draw(self, screen: pg.Surface, scale: float = 1.0):
        draw_triangle(screen, self.pos, self.angle, self.color, scale)


class SpriteSheet:
    def __init__(self, sprite: pg.Surface, rows: int, cols: int):
        self._sprite = sprite
        self.rows = rows
        self.cols = cols
        self.size = Vec2(sprite.get_width() / cols, sprite.get_height() / rows)

    def sprite(self, row: int, col: int) -> pg.Surface:
        x = col * self.size.x
        y = row * self.size.y
        return self._sprite.subsurface((x, y, self.size.x, self.size.y))


# SETTINGS
# --------------------------------------------------------------------------------------

show_minimap = True
show_rays = False
show_max_distance = True

# SETUP
# --------------------------------------------------------------------------------------

pg.init()
pg.font.init()


screen_surface = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags=pg.RESIZABLE)
minimap_surface = pg.surface.Surface((MINIMAP_WIDTH, MINIMAP_HEIGHT), pg.SRCALPHA)
scene_surface = pg.surface.Surface((SCENE_WIDTH, SCENE_HEIGHT), pg.SRCALPHA)

font = pg.font.SysFont(None, 24)

clock = pg.time.Clock()
running = True

tilemap = TileMap(MAP, TILE_SIZE, VIEW_DISTANCE)
player = Player(
    pos=tilemap.get_point(0.6,0.6),
    angle=0,
    vel=PLAYER_VEL,
    rvel=PLAYER_RVEL,
    fov=FOV,
    radius=COLLISSION_RADIUS,
    color=YELLOW,
)
walls = SpriteSheet(
    sprite=load_asset(AssetType.TEXTURE, "wolftextures.png"),
    rows=1,
    cols=8,
)
wall_texture = walls.sprite(0, 1)


# MAINLOOP
# --------------------------------------------------------------------------------------

while running:

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        if event.type == pg.VIDEORESIZE:
            SCREEN_HEIGHT = event.h
            SCREEN_WIDTH = event.w

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_q:
                running = False
            if event.key == pg.K_x:
                show_minimap = not show_minimap
            if event.key == pg.K_r:
                show_rays = not show_rays
            if event.key == pg.K_d:
                show_max_distance = not show_max_distance

    keys = pg.key.get_pressed()
    if keys[pg.K_LEFT]:
        player.rotate_right()
    if keys[pg.K_RIGHT]:
        player.rotate_left()
    if keys[pg.K_UP]:
        if tilemap.collides(player.move_ahead().pos, player.radius):
            player.move_back()
    if keys[pg.K_DOWN]:
        if tilemap.collides(player.move_back().pos, player.radius):
            player.move_ahead()

    screen_surface.fill(BLACK)
    rays = cast_rays(player, tilemap, FOV, RAYS_COUNT)
    scene_surface.fill(BLACK)
    draw_walls(scene_surface, tilemap, rays, player.pos, player.angle, player.fov, wall_texture)
    scene_pos = (SCREEN_WIDTH-SCENE_WIDTH)/2, (SCREEN_HEIGHT-SCENE_HEIGHT)/2
    screen_surface.blit(scene_surface, scene_pos)
    if show_minimap:
        draw_minimap(minimap_surface, tilemap)
        if show_rays:
            draw_rays(minimap_surface, player.pos, rays, YELLOW)
        if show_max_distance:
            draw_max_distance(minimap_surface, player.pos, player.angle, tilemap.max_distance)
        player.draw(minimap_surface, 1.5)
        minimap_surface.set_alpha(MINIMAP_ALPHA)
        screen_surface.blit(pg.transform.scale_by(minimap_surface, MINIMAP_SCALE), (0, 0))
    pg.display.flip()
    clock.tick(FPS)


# EXIT
# --------------------------------------------------------------------------------------
pg.quit()
