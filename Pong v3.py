import pygame
import sys
import random
import asyncio
import math
import os
import json

WIDTH, HEIGHT = 1000, 600
FPS = 60
CONFIG_FILE = "pong_settings.json"

def get_modern_font(size):
    try:
        return pygame.font.SysFont("SF Pro Display,Arial,sans-serif", size, bold=True)
    except Exception:
        return pygame.font.Font(None, size)

THEMES = {
    "Dark": {
        "bg": (15, 15, 35),
        "accent": (100, 200, 255),
        "text": (240, 240, 240),
        "menu_bg": (25, 25, 50),
        "button": (40, 40, 80),
        "button_hover": (80, 80, 160),
        "paddle": (100, 200, 255),
        "ball": (255, 150, 100),
        "particle": (255, 200, 150),
        "paused": (200, 50, 50)
    },
    "Light": {
        "bg": (240, 240, 255),
        "accent": (0, 120, 255),
        "text": (30, 30, 50),
        "menu_bg": (210, 220, 255),
        "button": (200, 210, 230),
        "button_hover": (160, 180, 230),
        "paddle": (0, 120, 255),
        "ball": (255, 150, 100),
        "particle": (255, 200, 150),
        "paused": (200, 50, 50)
    },
    "Colorblind": {
        "bg": (20, 20, 20),
        "accent": (255, 255, 0),
        "text": (255, 255, 255),
        "menu_bg": (40, 40, 40),
        "button": (90, 90, 90),
        "button_hover": (160, 160, 60),
        "paddle": (255, 255, 0),
        "ball": (255, 90, 90),
        "particle": (255, 220, 0),
        "paused": (255, 150, 0)
    }
}

WIN_SCORE = 10
DIFFICULTY_SETTINGS = {
    "Easy": {"ai_speed": 4, "ball_speed": 5, "ai_miss_chance": 0.18},
    "Medium": {"ai_speed": 7, "ball_speed": 8, "ai_miss_chance": 0.04},
    "Hard": {"ai_speed": 12, "ball_speed": 11, "ai_miss_chance": 0.0, "predict": True}
}
POWERUP_TYPES = ["Speed", "Size", "MultiBall"]

def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f)
    except Exception:
        pass

def load_settings():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

class Particle:
    def __init__(self, pos, color):
        self.pos = list(pos)
        self.velocity = [random.uniform(-3, 3), random.uniform(-3, 3)]
        self.lifetime = random.randint(15, 30)
        self.color = color
        self.alpha = 255
    
    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.lifetime -= 1
        self.alpha = max(0, int(255 * self.lifetime / 30))
        return self.lifetime > 0

class ConfettiParticle:
    def __init__(self, pos):
        self.pos = list(pos)
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(2, 6)
        self.velocity = [speed * math.cos(angle), speed * math.sin(angle) - 2]
        self.lifetime = random.randint(40, 60)
        self.color = (
            random.randint(100,255),
            random.randint(100,255),
            random.randint(100,255)
        )
        self.alpha = 255
    
    def update(self):
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.velocity[1] += 0.15  # gravity
        self.lifetime -= 1
        self.alpha = max(0, int(255 * self.lifetime / 60))
        return self.lifetime > 0

class PowerUp:
    def __init__(self, rect, kind):
        self.rect = rect
        self.kind = kind
        self.color = (random.randint(150,255), random.randint(150,255), random.randint(150,255))

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=10)
        font = pygame.font.Font(None, 28)
        txt = font.render(self.kind[0], True, (0,0,0))
        surface.blit(txt, (self.rect.x+7, self.rect.y+7))

class Button:
    def __init__(self, text, x, y, width=220, height=50):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.hovered = False
        self.selected = False

    def draw(self, surface, font, theme, alpha=255):
        color = theme["button_hover"] if self.hovered or self.selected else theme["button"]
        surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        fill = color + (alpha,)
        border = theme["accent"] + (alpha,) if self.hovered or self.selected else theme["menu_bg"] + (alpha,)
        pygame.draw.rect(surf, fill, (0,0,self.rect.width,self.rect.height), border_radius=10)
        pygame.draw.rect(surf, border, (0,0,self.rect.width,self.rect.height), 2, border_radius=10)
        text_surf = font.render(self.text, True, theme["text"])
        text_rect = text_surf.get_rect(center=(self.rect.width//2, self.rect.height//2))
        surf.blit(text_surf, text_rect)
        surface.blit(surf, self.rect.topleft)

class PongGame:
    def __init__(self):
        pygame.display.set_caption("Ultimate Pong Deluxe")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.font = get_modern_font(40)
        self.big_font = get_modern_font(72)
        self.title_font = get_modern_font(54)
        self.theme = "Dark"
        self.theme_colors = THEMES[self.theme]
        self.state = "menu"
        self.difficulty = "Medium"
        self.left_score = 0
        self.right_score = 0
        self.particles = []
        self.confetti = []
        self.winner = None
        self.paused = False
        self.trail = []
        self.mode = "PvAI"
        self.achievements = set()
        self.streak = 0
        self.max_streak = 0
        self.powerups = []
        self.active_powerups = {"left": [], "right": []}
        self.stats = {"games": 0, "wins": 0, "losses": 0}
        self.show_help = False
        self.menu_alpha = 0
        self.menu_fade_in = True
        self.menu_selected = 0
        self.sound_on = True

        self.menu_buttons = [
            Button("Player vs AI", 0, 0),
            Button("Player vs Player", 0, 0),
            Button("Easy", 0, 0),
            Button("Medium", 0, 0),
            Button("Hard", 0, 0),
            Button("Switch Theme", 0, 0),
            Button("Colorblind Mode", 0, 0),
            Button("Toggle Sound", 0, 0),
            Button("Show Help", 0, 0)
        ]
        self.reset_game()
        self.load_config()

        try:
            pygame.mixer.init()
            self.sound_enabled = True
            self.snd_hit = pygame.mixer.Sound(pygame.mixer.Sound.buffer(b'\x00'*1000))
        except Exception:
            self.sound_enabled = False

        self.controls = {
            "left_up": pygame.K_w,
            "left_down": pygame.K_s,
            "right_up": pygame.K_UP,
            "right_down": pygame.K_DOWN
        }

    def save_config(self):
        settings = {
            "theme": self.theme,
            "difficulty": self.difficulty,
            "mode": self.mode,
            "sound_on": self.sound_on
        }
        save_settings(settings)

    def load_config(self):
        settings = load_settings()
        self.theme = settings.get("theme", self.theme)
        self.theme_colors = THEMES[self.theme]
        self.difficulty = settings.get("difficulty", self.difficulty)
        self.mode = settings.get("mode", self.mode)
        self.sound_on = settings.get("sound_on", self.sound_on)

    def reset_game(self):
        self.left_paddle = pygame.Rect(30, HEIGHT//2-45, 15, 90)
        self.right_paddle = pygame.Rect(WIDTH-45, HEIGHT//2-45, 15, 90)
        ball_speed = DIFFICULTY_SETTINGS[self.difficulty]["ball_speed"]
        self.balls = [self._random_ball(ball_speed)]
        self.trail = []
        self.ai_speed = DIFFICULTY_SETTINGS[self.difficulty]["ai_speed"]
        self.ai_miss_chance = DIFFICULTY_SETTINGS[self.difficulty].get("ai_miss_chance", 0.0)
        self.ai_predict = DIFFICULTY_SETTINGS[self.difficulty].get("predict", False)
        self.powerups = []
        self.active_powerups = {"left": [], "right": []}

    def _random_ball(self, speed):
        angle = random.uniform(-0.5, 0.5)
        direction = random.choice([-1, 1])
        return {
            "rect": pygame.Rect(WIDTH//2-10, HEIGHT//2-10, 20, 20),
            "vel": [
                direction * speed * math.cos(angle),
                speed * math.sin(angle)
            ]
        }

    def create_particles(self, pos, color=None):
        c = color if color else self.theme_colors["particle"]
        for _ in range(15):
            self.particles.append(Particle(pos, c))

    def create_confetti(self, pos):
        for _ in range(35):
            self.confetti.append(ConfettiParticle(pos))

    def handle_collisions(self):
        for ball in self.balls:
            if ball["rect"].colliderect(self.left_paddle):
                ball["vel"][0] = abs(ball["vel"][0]) * 1.07
                ball["vel"][1] += random.uniform(-1, 1)
                self.create_particles(ball["rect"].center)
                if self.sound_on and self.sound_enabled: self.snd_hit.play()
            if ball["rect"].colliderect(self.right_paddle):
                ball["vel"][0] = -abs(ball["vel"][0]) * 1.07
                ball["vel"][1] += random.uniform(-1, 1)
                self.create_particles(ball["rect"].center)
                if self.sound_on and self.sound_enabled: self.snd_hit.play()
            if ball["rect"].top <= 0 or ball["rect"].bottom >= HEIGHT:
                ball["vel"][1] *= -1
                self.create_particles(ball["rect"].center)
            for p in self.powerups[:]:
                if ball["rect"].colliderect(p.rect):
                    self.apply_powerup(p, ball)
                    self.powerups.remove(p)

    def apply_powerup(self, p, ball):
        if p.kind == "Speed":
            ball["vel"][0] *= 1.5
            ball["vel"][1] *= 1.5
        elif p.kind == "Size":
            ball["rect"].inflate_ip(10, 10)
        elif p.kind == "MultiBall":
            if len(self.balls) < 3:
                for _ in range(2):
                    new_ball = self._random_ball(DIFFICULTY_SETTINGS[self.difficulty]["ball_speed"])
                    new_ball["rect"].center = ball["rect"].center
                    self.balls.append(new_ball)
        self.create_particles(p.rect.center, p.color)

    def maybe_spawn_powerup(self):
        if random.random() < 0.005 and len(self.powerups) < 2:
            kind = random.choice(POWERUP_TYPES)
            x = random.randint(WIDTH//4, WIDTH*3//4)
            y = random.randint(100, HEIGHT-100)
            self.powerups.append(PowerUp(pygame.Rect(x, y, 34, 34), kind))

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[self.controls["left_up"]] and self.left_paddle.top > 0:
            self.left_paddle.y -= 7
        if keys[self.controls["left_down"]] and self.left_paddle.bottom < HEIGHT:
            self.left_paddle.y += 7
        if self.mode == "PvP":
            if keys[self.controls["right_up"]] and self.right_paddle.top > 0:
                self.right_paddle.y -= 7
            if keys[self.controls["right_down"]] and self.right_paddle.bottom < HEIGHT:
                self.right_paddle.y += 7
        else:
            target = self._ai_predict_ball_y() if self.ai_predict else self.balls[0]["rect"].centery
            dead_zone = 10
            if abs(self.right_paddle.centery - target) > dead_zone:
                if random.random() > self.ai_miss_chance:
                    if self.right_paddle.centery < target and self.right_paddle.bottom < HEIGHT:
                        move = min(self.ai_speed, target - self.right_paddle.centery)
                        self.right_paddle.y += move
                    elif self.right_paddle.centery > target and self.right_paddle.top > 0:
                        move = min(self.ai_speed, self.right_paddle.centery - target)
                        self.right_paddle.y -= move
            self.right_paddle.top = max(self.right_paddle.top, 0)
            self.right_paddle.bottom = min(self.right_paddle.bottom, HEIGHT)

    def _ai_predict_ball_y(self):
        ball = self.balls[0]
        bx, by = ball["rect"].center
        vx, vy = ball["vel"]
        if vx <= 0:
            return by
        t = (self.right_paddle.left - bx) / vx
        predicted_y = by + vy * t
        while predicted_y < 0 or predicted_y > HEIGHT:
            if predicted_y < 0:
                predicted_y = -predicted_y
            elif predicted_y > HEIGHT:
                predicted_y = 2*HEIGHT - predicted_y
        return predicted_y

    def update_game(self):
        for ball in self.balls:
            ball["rect"].x += int(ball["vel"][0])
            ball["rect"].y += int(ball["vel"][1])
        self.trail.append(self.balls[0]["rect"].center)
        if len(self.trail) > 20:
            self.trail.pop(0)
        self.maybe_spawn_powerup()
        scored = False
        for ball in self.balls[:]:
            if ball["rect"].left <= 0:
                self.right_score += 1
                self.achievements.add("Lose a point")
                scored = True
                self.balls.remove(ball)
            elif ball["rect"].right >= WIDTH:
                self.left_score += 1
                self.streak += 1
                self.max_streak = max(self.max_streak, self.streak)
                if self.streak >= 5:
                    self.achievements.add("5 streak!")
                scored = True
                self.balls.remove(ball)
        if scored:
            if not self.balls:
                self.balls = [self._random_ball(DIFFICULTY_SETTINGS[self.difficulty]["ball_speed"])]
            self.left_paddle.centery = HEIGHT//2
            self.right_paddle.centery = HEIGHT//2
        self.particles = [p for p in self.particles if p.update()]
        self.confetti = [c for c in self.confetti if c.update()]

    def draw_main_menu(self, t):
        c = self.theme_colors
        self.screen.fill(c["menu_bg"])
        # Spacious title at top-left
        title_text = self.title_font.render("Ultimate Pong Deluxe", True, c["accent"])
        title_y = 60
        self.screen.blit(title_text, (60, title_y))
        # Divider, spaced below title
        divider_y = title_y + title_text.get_height() + 18
        pygame.draw.line(self.screen, c["accent"], (60, divider_y), (WIDTH-60, divider_y), 2)
        # Spacious button layout
        button_width, button_height = 300, 58
        button_gap = 38
        total_height = len(self.menu_buttons) * button_height + (len(self.menu_buttons)-1) * button_gap
        button_y_start = divider_y + 60
        available_height = HEIGHT - button_y_start - 140
        if total_height > available_height:
            scale = available_height / total_height
            button_height = int(button_height * scale)
            button_gap = int(button_gap * scale)
            total_height = len(self.menu_buttons) * button_height + (len(self.menu_buttons)-1) * button_gap
        button_x = WIDTH//2 - button_width//2
        mouse_pos = pygame.mouse.get_pos()
        for i, button in enumerate(self.menu_buttons):
            button.rect.x = button_x
            button.rect.y = button_y_start + i * (button_height + button_gap)
            button.rect.width = button_width
            button.rect.height = button_height
            button.hovered = button.rect.collidepoint(mouse_pos)
            button.selected = (i == self.menu_selected)
            alpha = min(255, int(self.menu_alpha))
            button.draw(self.screen, self.font, c, alpha=alpha)
        # Info and stats with extra bottom margin
        info_text = self.font.render("First to 10 wins. W/S and ↑/↓ to move.", True, c["text"])
        self.screen.blit(info_text, (WIDTH//2 - info_text.get_width()//2, HEIGHT - 90))
        stats_font = pygame.font.Font(None, 28)
        stats = stats_font.render(
            f"Games: {self.stats['games']}  Wins: {self.stats['wins']}  Losses: {self.stats['losses']}  Max Streak: {self.max_streak}",
            True, c["button_hover"])
        self.screen.blit(stats, (WIDTH//2 - stats.get_width()//2, HEIGHT - 52))
        if self.menu_fade_in and self.menu_alpha < 255:
            self.menu_alpha += 8
        else:
            self.menu_alpha = 255

    def draw_help(self):
        c = self.theme_colors
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        self.screen.blit(overlay, (0,0))
        lines = [
            "Controls:",
            "W/S: Move left paddle",
            "Up/Down: Move right paddle (PvP)",
            "P: Pause",
            "SPACE: Return to menu after a game",
            "Click 'Switch Theme' for Light/Dark mode",
            "Power-ups: S=Speed, Z=Size, M=MultiBall",
            "First to 10 points wins.",
            "Achievements unlock for streaks and more!",
            "Navigate menu: ↑/↓ or W/S, Enter to select"
        ]
        for i, line in enumerate(lines):
            txt = self.font.render(line, True, c["text"])
            self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 120 + i*40))

    def draw_game(self):
        c = self.theme_colors
        self.screen.fill(c["bg"])
        for i, pos in enumerate(self.trail):
            alpha = int(255 * (i+1) / len(self.trail))
            trail_color = (c["ball"][0], c["ball"][1], c["ball"][2], alpha)
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(s, trail_color, (0,0,20,20))
            self.screen.blit(s, (pos[0]-10, pos[1]-10))
        pygame.draw.rect(self.screen, c["paddle"], self.left_paddle, border_radius=8)
        pygame.draw.rect(self.screen, c["paddle"], self.right_paddle, border_radius=8)
        for ball in self.balls:
            pygame.draw.ellipse(self.screen, c["ball"], ball["rect"])
        for p in self.particles:
            surf = pygame.Surface((6,6), pygame.SRCALPHA)
            color = p.color + (p.alpha,)
            pygame.draw.circle(surf, color, (3,3), 3)
            self.screen.blit(surf, (int(p.pos[0]), int(p.pos[1])))
        for p in self.powerups:
            p.draw(self.screen)
        score_text = self.big_font.render(f"{self.left_score} - {self.right_score}", True, c["text"])
        score_rect = score_text.get_rect(center=(WIDTH//2, 50))
        self.screen.blit(score_text, score_rect)
        if self.paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((c["paused"][0], c["paused"][1], c["paused"][2], 120))
            self.screen.blit(overlay, (0,0))
            pause_text = self.big_font.render("PAUSED", True, c["text"])
            pause_rect = pause_text.get_rect(center=(WIDTH//2, HEIGHT//2))
            self.screen.blit(pause_text, pause_rect)
        if self.achievements:
            ach = self.font.render("Achievements: " + ", ".join(self.achievements), True, c["accent"])
            self.screen.blit(ach, (20, HEIGHT-40))

    def draw_winner(self):
        c = self.theme_colors
        self.screen.fill(c["bg"])
        win_text = self.big_font.render(f"{self.winner} Wins!", True, c["accent"])
        win_rect = win_text.get_rect(center=(WIDTH//2, HEIGHT//2-40))
        self.screen.blit(win_text, win_rect)
        info_text = self.font.render("Press SPACE to return to menu.", True, c["text"])
        info_rect = info_text.get_rect(center=(WIDTH//2, HEIGHT//2+40))
        self.screen.blit(info_text, info_rect)
        if self.achievements:
            ach = self.font.render("Achievements: " + ", ".join(self.achievements), True, c["accent"])
            self.screen.blit(ach, (20, HEIGHT-40))
        for conf in self.confetti:
            surf = pygame.Surface((8,8), pygame.SRCALPHA)
            color = conf.color + (conf.alpha,)
            pygame.draw.circle(surf, color, (4,4), 4)
            self.screen.blit(surf, (int(conf.pos[0]), int(conf.pos[1])))

    async def run(self):
        t = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_config()
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    global WIDTH, HEIGHT
                    WIDTH, HEIGHT = event.w, event.h
                    self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                if self.state == "menu":
                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_DOWN, pygame.K_s):
                            self.menu_selected = (self.menu_selected + 1) % len(self.menu_buttons)
                        if event.key in (pygame.K_UP, pygame.K_w):
                            self.menu_selected = (self.menu_selected - 1) % len(self.menu_buttons)
                        if event.key == pygame.K_RETURN:
                            self.menu_fade_in = True
                            self.menu_alpha = 0
                            self.menu_buttons[self.menu_selected].hovered = True
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': self.menu_buttons[self.menu_selected].rect.center}))
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        for idx, button in enumerate(self.menu_buttons):
                            if button.rect.collidepoint(event.pos):
                                self.menu_selected = idx
                                if button.text == "Player vs AI":
                                    self.mode = "PvAI"
                                    self.state = "game"
                                    self.left_score = self.right_score = 0
                                    self.reset_game()
                                elif button.text == "Player vs Player":
                                    self.mode = "PvP"
                                    self.state = "game"
                                    self.left_score = self.right_score = 0
                                    self.reset_game()
                                elif button.text in DIFFICULTY_SETTINGS:
                                    self.difficulty = button.text
                                    self.reset_game()
                                elif button.text == "Switch Theme":
                                    self.theme = "Light" if self.theme == "Dark" else "Dark"
                                    self.theme_colors = THEMES[self.theme]
                                elif button.text == "Colorblind Mode":
                                    self.theme = "Colorblind"
                                    self.theme_colors = THEMES[self.theme]
                                elif button.text == "Toggle Sound":
                                    self.sound_on = not self.sound_on
                                elif button.text == "Show Help":
                                    self.show_help = not self.show_help
                                self.save_config()
                    if self.menu_fade_in:
                        self.menu_alpha = min(255, self.menu_alpha + 8)
                        if self.menu_alpha >= 255:
                            self.menu_fade_in = False
                elif self.state == "winner":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        self.state = "menu"
                        self.menu_fade_in = True
                        self.menu_alpha = 0
                elif self.state == "game":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                        self.paused = not self.paused
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
                        self.show_help = not self.show_help

            if self.state == "menu":
                self.draw_main_menu(t)
                if self.show_help:
                    self.draw_help()
            elif self.state == "game":
                if not self.paused:
                    self.handle_input()
                    self.handle_collisions()
                    self.update_game()
                self.draw_game()
                if self.show_help:
                    self.draw_help()
                if self.left_score >= WIN_SCORE:
                    self.winner = "Left"
                    self.stats["games"] += 1
                    self.stats["wins"] += 1
                    self.state = "winner"
                    self.streak = 0
                    self.create_confetti((WIDTH//2, HEIGHT//2-40))
                elif self.right_score >= WIN_SCORE:
                    self.winner = "Right"
                    self.stats["games"] += 1
                    self.stats["losses"] += 1
                    self.state = "winner"
                    self.streak = 0
                    self.create_confetti((WIDTH//2, HEIGHT//2-40))
            elif self.state == "winner":
                self.draw_winner()

            pygame.display.flip()
            self.clock.tick(FPS)
            t += 0.05
            await asyncio.sleep(0)

if __name__ == "__main__":
    pygame.init()
    game = PongGame()
    asyncio.run(game.run())
