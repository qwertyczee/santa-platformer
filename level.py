import pygame
import random
from constants import ASSETS_DIR, WIDTH, HEIGHT
from enemy import Enemy

# --- Level definitions ---
LEVELS = [
    {
        "name": "Snowy Village",
        "width": 1600,
        "height": 600,
        "player_start": (80, 480),
        "goal": (1500, 480, 60, 80),  # tree
        "ground": (0, 560, 1600, 40),
        "platforms": [
            (200, 430, 160, 20),
            (420, 330, 160, 20),
            (700, 460, 200, 20),
            (1100, 380, 200, 20),
            (1350, 300, 180, 20),
        ],
        "presents": [
            (220, 400, 30, 30),
            (460, 300, 30, 30),
            (760, 430, 30, 30),
            (1120, 350, 30, 30),
            (1370, 270, 30, 30),
        ],
        "enemies": [
            # x,y,w,h, patrol_min_x, patrol_max_x, speed
            (600, 520, 40, 40, 500, 740, 2),
            (1300, 340, 40, 40, 1250, 1450, 1.5),
        ],
        "powerups": [
            {"rect": (520, 480, 24, 24), "type": "double_jump"},
            {"rect": (900, 420, 24, 24), "type": "speed_boost"},
        ]
    },

    {
        "name": "Icicle Climb",
        "width": 1200,
        "height": 800,
        "player_start": (60, 700),
        "goal": (1100, 700, 60, 80),
        "ground": (0, 760, 1200, 40),
        "platforms": [
            (150, 640, 130, 20),
            (320, 520, 130, 20),
            (510, 400, 130, 20),
            (720, 280, 130, 20),
            (920, 160, 130, 20),
        ],
        "presents": [
            (170, 510, 30, 30),
            (340, 490, 30, 30),
            (530, 370, 30, 30),
            (740, 250, 30, 30),
            (940, 130, 30, 30),
        ],
        "enemies": [
            (400, 720, 40, 40, 300, 520, 2.2),
            (800, 720, 40, 40, 760, 980, 1.7),
        ],
        "powerups": [
            {"rect": (600, 360, 24, 24), "type": "invincibility"},
        ]
    }
]

class LevelManager:
    def __init__(self, levels_data):
        self.completed = False
        self.levels = levels_data
        self.index = 0
        self.load_level(self.index)

    def load_level(self, index):
        data = self.levels[index]
        self.width = data.get('width', WIDTH)
        self.height = data.get('height', HEIGHT)

        # --- auto-generate ground at the bottom ---
        ground_height = 40
        self.ground = pygame.Rect(0, self.height - ground_height, self.width, ground_height)

        # --- floating platforms ---
        self.platforms = [pygame.Rect(*p) for p in data['platforms']]

        self.presents = []
        for p in data['presents']:
            rect = pygame.Rect(*p)
            texture = random.choice(["present", "present1", "present2", "present3"])
            self.presents.append({"rect": rect, "texture": texture})
        self.powerups = [{'rect': pygame.Rect(*p['rect']), 'type': p['type']} for p in data.get('powerups', [])]
        self.enemies = [Enemy(*e) for e in data.get('enemies', [])]
        sx, sy = data['player_start']
        gx, gy, gw, gh = data['goal']
        self.goal = pygame.Rect(gx, gy, gw, gh)
        self.player_start = (sx, sy)
        self.total_presents = len(self.presents)
        self.name = data.get('name', f"Level {index+1}")

        # --- Load background ---
        bg_path = ASSETS_DIR / f"bckg{index+1}.png"
        if bg_path.exists():
            bg_img = pygame.image.load(str(bg_path)).convert()
            self.background = pygame.transform.scale(bg_img, (self.width, self.height))
        else:
            self.background = pygame.Surface((self.width, self.height))
            self.background.fill((50, 50, 100))  # fallback color
        
        self.overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 120))

    def next_level(self):
        if self.index + 1 < len(self.levels):
            self.index += 1
            self.load_level(self.index)
            return True
        else:
            return False  # no more levels