import asyncio
import math
import random
import sys
import pygame

WIDTH, HEIGHT = 1100, 650
FPS = 60

PADDLE_W, PADDLE_H = 18, 200
PADDLE_SPEED = 520.0
PADDLE_SEGMENTS = 14

BALL_R = 10
BALL_BASE_SPEED = 420.0
BALL_MAX_SPEED = 980.0
HIT_SPEEDUP = 1.04
SPIN_MAX = 420.0

SCORE_TO_WIN = 11
MARGIN = 32

BG = (10, 17, 33)
FG = (230, 238, 252)
ACCENT = (115, 175, 255)
DIM = (70, 85, 120)

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v
class Paddle:
    def __init__(self, x, y, w, h, segments):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.segments = segments
        self.segment_present = [True] * segments

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    @property
    def cx(self):
        return self.x + self.w * 0.5

    @property
    def cy(self):
        return self.y + self.h * 0.5

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.w

    def reset_segments(self):
        for i in range(self.segments):
            self.segment_present[i] = True

    def segment_index_at_y(self, y):
        rel = y - self.y
        if rel < 0 or rel >= self.h:
            return None
        seg_h = self.h / self.segments
        idx = int(rel // seg_h)
        return max(0, min(self.segments - 1, idx))

    def has_segment(self, idx):
        if idx is None:
            return False
        return self.segment_present[idx]

    def remove_segment(self, idx):
        if idx is None:
            return
        self.segment_present[idx] = False

    def draw(self, surf):
        seg_h = self.h / self.segments
        for i, present in enumerate(self.segment_present):
            if present:
                seg_rect = pygame.Rect(int(self.x), int(self.y + i * seg_h), int(self.w), int(seg_h) - 1)
                pygame.draw.rect(surf, FG, seg_rect, border_radius=3)
        outline = self.rect.copy()
        pygame.draw.rect(surf, DIM, outline, width=1, border_radius=4)

class Ball:
    def __init__(self, x, y, r):
        self.x = x
        self.y = y
        self.r = r
        self.vx = 0.0
        self.vy = 0.0

    def serve(self, direction=None):
        self.x = WIDTH * 0.5
        self.y = HEIGHT * 0.5
        angle = random.uniform(-0.35, 0.35)
        speed = BALL_BASE_SPEED
        if direction is None:
            direction = random.choice([-1, 1])
        self.vx = direction * speed * math.cos(angle)
        self.vy = speed * math.sin(angle)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def left(self): return self.x - self.r
    @property
    def right(self): return self.x + self.r
    @property
    def top(self): return self.y - self.r
    @property
    def bottom(self): return self.y + self.r

    def draw(self, surf):
        pygame.draw.circle(surf, ACCENT, (int(self.x), int(self.y)), self.r)

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Sacrifices Must Be Made")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.huge = pygame.font.SysFont(None, 72)
        self.reset(full=True)

    def reset(self, full=False, serve_dir=None):
        self.left = Paddle(MARGIN, HEIGHT/2 - PADDLE_H/2, PADDLE_W, PADDLE_H, PADDLE_SEGMENTS)
        self.right = Paddle(WIDTH - MARGIN - PADDLE_W, HEIGHT/2 - PADDLE_H/2, PADDLE_W, PADDLE_H, PADDLE_SEGMENTS)
        if full:
            self.score_l = 0
            self.score_r = 0
        self.left.reset_segments()
        self.right.reset_segments()
        self.ball = Ball(WIDTH*0.5, HEIGHT*0.5, BALL_R)
        self.ball.serve(direction=serve_dir)
        self.paused = False
        self.winner = None
        self.hold = {"w": False, "s": False, "up": False, "down": False}

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: pygame.quit(); sys.exit(0)
                if event.key == pygame.K_SPACE: self.paused = not self.paused
                if event.key == pygame.K_r: self.reset(full=True, serve_dir=random.choice([-1, 1]))
                if event.key == pygame.K_RETURN and self.winner is not None:
                    self.reset(full=True, serve_dir=random.choice([-1, 1]))
                if event.key == pygame.K_w: self.hold["w"] = True
                if event.key == pygame.K_s: self.hold["s"] = True
                if event.key == pygame.K_UP: self.hold["up"] = True
                if event.key == pygame.K_DOWN: self.hold["down"] = True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_w: self.hold["w"] = False
                if event.key == pygame.K_s: self.hold["s"] = False
                if event.key == pygame.K_UP: self.hold["up"] = False
                if event.key == pygame.K_DOWN: self.hold["down"] = False

    def move_paddles(self, dt):
        dy = 0.0
        if self.hold["w"]: dy -= PADDLE_SPEED * dt
        if self.hold["s"]: dy += PADDLE_SPEED * dt
        self.left.y = clamp(self.left.y + dy, 0, HEIGHT - self.left.h)
        dy = 0.0
        if self.hold["up"]: dy -= PADDLE_SPEED * dt
        if self.hold["down"]: dy += PADDLE_SPEED * dt
        self.right.y = clamp(self.right.y + dy, 0, HEIGHT - self.right.h)

    def ball_wall_collisions(self):
        if self.ball.top <= 0.0 and self.ball.vy < 0:
            self.ball.y = self.ball.r
            self.ball.vy *= -1
        elif self.ball.bottom >= HEIGHT and self.ball.vy > 0:
            self.ball.y = HEIGHT - self.ball.r
            self.ball.vy *= -1

    def _bounce_from_paddle(self, paddle, is_left_side):
        hit_idx = paddle.segment_index_at_y(self.ball.y)
        if hit_idx is None or not paddle.has_segment(hit_idx):
            return False
        paddle.remove_segment(hit_idx)
        self.ball.vx *= -1
        offset_norm = (self.ball.y - paddle.cy) / (paddle.h * 0.5)
        offset_norm = max(-1.0, min(1.0, offset_norm))
        spin = offset_norm * SPIN_MAX
        self.ball.vy = self.ball.vy * 0.15 + spin * 0.85
        speed = min(math.hypot(self.ball.vx, self.ball.vy) * HIT_SPEEDUP, BALL_MAX_SPEED)
        ang = math.atan2(self.ball.vy, self.ball.vx)
        self.ball.vx = speed * math.cos(ang)
        self.ball.vy = speed * math.sin(ang)
        if is_left_side:
            self.ball.x = paddle.right + self.ball.r + 0.1
        else:
            self.ball.x = paddle.left - self.ball.r - 0.1
        return True

    def ball_paddle_collisions(self, dt):
        prev_x = self.ball.x - self.ball.vx * dt
        if self.ball.vx < 0:
            plane = self.left.right + self.ball.r
            if prev_x > plane and self.ball.x <= plane:
                if self._bounce_from_paddle(self.left, is_left_side=True):
                    return
        if self.ball.vx > 0:
            plane = self.right.left - self.ball.r
            if prev_x < plane and self.ball.x >= plane:
                if self._bounce_from_paddle(self.right, is_left_side=False):
                    return

    def check_score(self):
        if self.ball.right < 0:
            self.score_r += 1
            if self.score_r >= SCORE_TO_WIN and self.score_r - self.score_l >= 2:
                self.winner = "Right"
            self.left.reset_segments(); self.right.reset_segments()
            self.ball.serve(direction=1)
        elif self.ball.left > WIDTH:
            self.score_l += 1
            if self.score_l >= SCORE_TO_WIN and self.score_l - self.score_r >= 2:
                self.winner = "Left "
            self.left.reset_segments(); self.right.reset_segments()
            self.ball.serve(direction=-1)

    def draw_center_line(self):
        dash_h, gap = 14, 12
        x, y = WIDTH // 2, 0
        while y < HEIGHT:
            pygame.draw.rect(self.screen, DIM, (x - 2, y, 4, dash_h))
            y += dash_h + gap

    def draw_ui(self):
        score_l_surf = self.huge.render(f"{self.score_l}", True, FG)
        score_r_surf = self.huge.render(f"{self.score_r}", True, FG)
        self.screen.blit(score_l_surf, (WIDTH*0.25 - score_l_surf.get_width()/2, 24))
        self.screen.blit(score_r_surf, (WIDTH*0.75 - score_r_surf.get_width()/2, 24))

    def run(self):
        self.ball.serve()
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_input()
            if not self.paused and self.winner is None:
                self.move_paddles(dt)
                self.ball.update(dt)
                self.ball_wall_collisions()
                self.ball_paddle_collisions(dt)
                self.check_score()
            self.screen.fill(BG)
            self.draw_center_line()
            self.left.draw(self.screen)
            self.right.draw(self.screen)
            self.ball.draw(self.screen)
            self.draw_ui()
            pygame.display.flip()

if __name__ == "__main__":
    Game().run()
