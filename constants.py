import pygame
from pathlib import Path

# --- Screen and Game Settings ---
BASE_WIDTH, BASE_HEIGHT = 800, 600  # Base resolution for scaling
FPS = 60
FULLSCREEN = True  # Start in fullscreen mode (borderless windowed fullscreen)
RESIZABLE = True  # Allow window resizing

# --- Physics Constants ---
GRAVITY = 0.6          # px/frame^2
MAX_FALL = 15          # terminal velocity
BASE_SPEED = 5         # px/frame
BASE_JUMP = -13        # px/frame

# --- Game Settings ---
STARTING_LIVES = 3

# --- Asset Paths ---
ASSETS_DIR = Path(__file__).parent / "assets"

# --- Game States ---
class GameState:
    MAIN_MENU   = "MAIN_MENU"
    LEVEL_SELECT= "LEVEL_SELECT"
    OPTIONS     = "OPTIONS"
    PLAYING     = "PLAYING"
    PAUSED      = "PAUSED"

# --- Power-up Durations (in milliseconds) ---
POWERUP_DURATIONS = {
    'double_jump': 15000,
    'speed_boost': 8000,
    'invincibility': 6000
}

# --- Animation Settings ---
ANIMATION_SPEED = 200  # ms per frame

# --- Message Display ---
MESSAGE_DURATION = 1500  # default message duration in ms
LEVEL_COMPLETE_DELAY = 3000  # delay before switching levels after completion
RESPAWN_INVINCIBLE_TIME = 1200  # ms of invincibility after respawn