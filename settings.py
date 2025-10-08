# settings.py
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent / "settings.json"

DIFFICULTY_PRESETS = {
    "Easy":   {"lives": 5, "enemy_speed_mult": 0.85, "powerup_mult": 1.25},
    "Normal": {"lives": 3, "enemy_speed_mult": 1.00, "powerup_mult": 1.00},
    "Hard":   {"lives": 2, "enemy_speed_mult": 1.25, "powerup_mult": 0.85},
}

DEFAULT_CONTROLS = {
    "left": "LEFT",
    "right": "RIGHT",
    "jump": "SPACE",
    "pause": "ESCAPE",
}

def key_name_to_const(name: str) -> int:
    import pygame
    name = name.upper()
    # Allow both pygame names and symbols
    if hasattr(pygame, f"K_{name.lower()}"):
        return getattr(pygame, f"K_{name.lower()}")
    try:
        return pygame.key.key_code(name.lower())
    except Exception:
        return pygame.K_UNKNOWN

def key_const_to_name(code: int) -> str:
    import pygame
    n = pygame.key.name(code)
    return n.upper()

@dataclass
class Settings:
    difficulty: str = "Normal"
    controls: dict = None

    # derived (computed) runtime values
    lives: int = 3
    enemy_speed_mult: float = 1.0
    powerup_mult: float = 1.0

    def __post_init__(self):
        if self.controls is None:
            self.controls = DEFAULT_CONTROLS.copy()
        self.apply_difficulty()

    @classmethod
    def load(cls) -> "Settings":
        if SETTINGS_PATH.exists():
            try:
                data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
                s = cls(**data)
                s.apply_difficulty()
                return s
            except Exception:
                pass
        s = cls()
        s.save()
        return s

    def save(self):
        SETTINGS_PATH.write_text(json.dumps({
            "difficulty": self.difficulty,
            "controls": self.controls
        }, indent=2), encoding="utf-8")

    def apply_difficulty(self):
        p = DIFFICULTY_PRESETS.get(self.difficulty, DIFFICULTY_PRESETS["Normal"])
        self.lives = p["lives"]
        self.enemy_speed_mult = p["enemy_speed_mult"]
        self.powerup_mult = p["powerup_mult"]

    # helpers
    def get_key(self, action: str) -> int:
        return key_name_to_const(self.controls.get(action, DEFAULT_CONTROLS[action]))

    def set_key(self, action: str, key_code: int):
        self.controls[action] = key_const_to_name(key_code)
        self.save()
