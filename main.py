# main.py (FULL)
import pygame
import sys
from pathlib import Path

from constants import BASE_WIDTH, BASE_HEIGHT, FPS, STARTING_LIVES, GRAVITY, MAX_FALL, LEVEL_COMPLETE_DELAY, ASSETS_DIR, POWERUP_DURATIONS, GameState
from display import DisplayManager
from player import Player
from level import LevelManager, LEVELS
from camera import Camera
from collision import resolve_horizontal, resolve_vertical, clamp_player_to_level
from ui import draw_hud, draw_message, show_message
from utils import get_texture
from settings import Settings
from menu import MainMenu, PauseMenu, LevelSelect, OptionsMenu

pygame.init()

# --- Game Initialization ---
display = DisplayManager()
pygame.display.set_caption("Santa Platformer (Pygame)")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
big_font = pygame.font.SysFont(None, 48)

game_surface = display.create_game_surface()

# Settings
settings = Settings.load()

# --- Game State & Screens ---
state = GameState.MAIN_MENU
previous_state = GameState.MAIN_MENU  # Track where we came from for Options back button
main_menu = MainMenu(big_font, font)
pause_menu = PauseMenu(big_font, font)
level_select = LevelSelect(big_font, font, [lvl["name"] for lvl in LEVELS])
options_menu = OptionsMenu(big_font, font, settings)

# --- Game Objects (lazy init for levels) ---
def start_new_game(level_index=0):
    global level_manager, player, camera, lives, score, level_complete_time
    level_manager = LevelManager(LEVELS, settings)
    level_manager.index = level_index
    level_manager.load_level(level_index)

    player = Player(*level_manager.player_start)
    camera = Camera()
    # apply difficulty lives
    global STARTING_LIVES  # we keep original constant but use settings.lives
    lives = settings.lives
    score = 0
    level_complete_time = None

level_manager = None
player = None
camera = None
lives = 0
score = 0
level_complete_time = None

# mouse visible in menus
pygame.mouse.set_visible(True)

running = True
while running:
    dt_ms = clock.tick(FPS)
    now = pygame.time.get_ticks()
    events = list(pygame.event.get())

    # Global window/system events
    for ev in events:
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.VIDEORESIZE:
            display.resize_window(ev.w, ev.h)
            game_surface = display.create_game_surface()

    # --- STATE MACHINE ---
    if state == GameState.MAIN_MENU:
        pygame.mouse.set_visible(True)
        action = main_menu.render(game_surface, events, display.to_base_pos)
        # clear & draw
        display.render_game_surface(game_surface)
        pygame.display.flip()

        if action == "Start":
            start_new_game(0)
            state = GameState.PLAYING
            pygame.mouse.set_visible(False)
        elif action == "Level Selector":
            state = GameState.LEVEL_SELECT
        elif action == "Options":
            previous_state = GameState.MAIN_MENU
            state = GameState.OPTIONS
        elif action == "Quit":
            running = False
        continue

    if state == GameState.LEVEL_SELECT:
        pygame.mouse.set_visible(True)
        act = level_select.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()
        if act == "Back":
            state = GameState.MAIN_MENU
        elif isinstance(act, str) and act.startswith("START_LEVEL_"):
            idx = int(act.split("_")[-1])
            start_new_game(idx)
            state = GameState.PLAYING
            pygame.mouse.set_visible(False)
        continue

    if state == GameState.OPTIONS:
        pygame.mouse.set_visible(True)
        act = options_menu.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()
        if act == "Back":
            # Return to the previous menu
            state = previous_state
            # Rebuild LevelSelect if coming from there (names unchanged; but keep separation)
            if previous_state == GameState.LEVEL_SELECT:
                level_select = LevelSelect(big_font, font, [lvl["name"] for lvl in LEVELS])
            # If we change difficulty, re-apply powerup multipliers at runtime
            continue
        continue

    if state == GameState.PAUSED:
        pygame.mouse.set_visible(True)
        act = pause_menu.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()
        # pause controls
        for ev in events:
            if ev.type == pygame.KEYDOWN and ev.key == settings.get_key("pause"):
                state = GameState.PLAYING
                pygame.mouse.set_visible(False)
        if act == "Resume":
            state = GameState.PLAYING
            pygame.mouse.set_visible(False)
        elif act == "Options":
            previous_state = GameState.PAUSED
            state = GameState.OPTIONS
        elif act == "Quit to Menu":
            state = GameState.MAIN_MENU
        continue

    # --- PLAYING ---
    pygame.mouse.set_visible(False)

    # Input mapping
    keys = pygame.key.get_pressed()

    # Handle pause
    for ev in events:
        if ev.type == pygame.KEYDOWN and ev.key == settings.get_key("pause"):
            state = GameState.PAUSED

        elif ev.type == pygame.KEYDOWN and ev.key == settings.get_key("jump"):
            if player and player.can_jump(now):
                player.vy = player.jump_strength
                player.jumps_remaining -= 1

    # Movement
    player.vx = 0
    if keys[settings.get_key("left")]:
        player.vx = -player.speed
        player.facing_right = False
    if keys[settings.get_key("right")]:
        player.vx = player.speed
        player.facing_right = True

    # Powerups durations apply multiplier by difficulty
    def scaled_duration(ptype: str) -> int:
        base = POWERUP_DURATIONS[ptype]
        return int(base * settings.powerup_mult)
    
    # Update powerup states
    player.update_powerups(now)

    # Physics
    player.vy += GRAVITY
    if player.vy > MAX_FALL:
        player.vy = MAX_FALL

    player.x += player.vx
    resolve_horizontal(player, [level_manager.ground] + level_manager.platforms)
    player.y += player.vy
    on_ground = resolve_vertical(player, [level_manager.ground] + level_manager.platforms)
    clamp_player_to_level(player, level_manager.width, level_manager.height)

    # Camera & enemies
    camera.update(player.rect, level_manager.width, level_manager.height)
    for e in level_manager.enemies:
        e.update()

    # Presents
    for p in level_manager.presents[:]:
        if player.rect.colliderect(p["rect"]):
            level_manager.presents.remove(p)
            score += 1
            show_message("Present collected!", 900)

    # Powerups
    for pu in level_manager.powerups[:]:
        if player.rect.colliderect(pu['rect']):
            ptype = pu['type']
            player.apply_powerup(ptype, scaled_duration(ptype), now)
            level_manager.powerups.remove(pu)
            show_message(f"Powerup: {ptype}", 1100)

    # Enemies collide
    collided_enemy = None
    for e in level_manager.enemies:
        if player.rect.colliderect(e.rect):
            collided_enemy = e
            break

    if collided_enemy:
        if not player.is_invincible(now):
            lives -= 1
            if lives <= 0:
                show_message("Game Over! Returning to Menu...", 1800)
                pygame.time.delay(1200)
                state = GameState.MAIN_MENU
                continue
            else:
                player.respawn(*level_manager.player_start)
                show_message("You lost a life!", 900)

    # Goal
    if player.rect.colliderect(level_manager.goal):
        if score >= level_manager.total_presents:
            if not level_manager.completed:
                level_manager.completed = True
                level_complete_time = pygame.time.get_ticks()
                show_message("Level Complete!", 1500)
        else:
            show_message("Collect all presents before the tree!", 1300)

    # Drawing
    if level_manager.background:
        game_surface.blit(level_manager.background, (-camera.x, -camera.y))
    else:
        game_surface.fill((24, 36, 60))

    game_surface.blit(level_manager.overlay, (-camera.x, -camera.y))

    tile = pygame.image.load("assets/ground.png").convert_alpha()
    tile_width = tile.get_width()

    for x in range(0, level_manager.ground.width, tile_width):
        game_surface.blit(tile, (level_manager.ground.x + x - camera.x,
                        level_manager.ground.y - camera.y))

    for plat in level_manager.platforms:
        surf = get_texture('platform', (plat.width, plat.height))
        game_surface.blit(surf, (plat.x - camera.x, plat.y - camera.y))

    for p in level_manager.presents:
        surf = get_texture(p["texture"], (p["rect"].width, p["rect"].height))
        game_surface.blit(surf, (p["rect"].x - camera.x, p["rect"].y - camera.y))

    for pu in level_manager.powerups:
        surf = get_texture(pu['type'], (pu['rect'].width, pu['rect'].height))
        game_surface.blit(surf, (pu['rect'].x - camera.x, pu['rect'].y - camera.y))

    for e in level_manager.enemies:
        surf = get_texture('enemy', (e.rect.width, e.rect.height))
        game_surface.blit(surf, (e.rect.x - camera.x, e.rect.y - camera.y))

    tree_texture_name = 'tree1' if level_manager.completed else 'tree'
    surf_tree = get_texture(tree_texture_name, (level_manager.goal.width, level_manager.goal.height))
    game_surface.blit(surf_tree, (level_manager.goal.x - camera.x, level_manager.goal.y - camera.y))

    player.update_animation(dt_ms)
    surf_player = player.get_current_frame()
    if not (player.is_invincible(now) and (now // 150) % 2 == 0):
        game_surface.blit(surf_player, (player.rect.x - camera.x, player.rect.y - camera.y))

    draw_hud(game_surface, font, lives, score, level_manager, player)
    draw_message(game_surface, font)

    # Delayed level switch
    if level_manager.completed and level_complete_time is not None:
        if pygame.time.get_ticks() - level_complete_time > LEVEL_COMPLETE_DELAY:
            advanced = level_manager.next_level()
            if advanced:
                # re-apply difficulty enemy scaling on new level already handled in load_level
                player = Player(*level_manager.player_start)
                score = 0
                level_manager.completed = False
                level_complete_time = None
            else:
                game_surface.fill((10,10,40))
                text = big_font.render("You saved Christmas! 🎅🎉", True, (255,255,200))
                game_surface.blit(text, (BASE_WIDTH//2 - text.get_width()//2, BASE_HEIGHT//2 - text.get_height()//2))
                display.render_game_surface(game_surface)
                pygame.display.flip()
                pygame.time.delay(2000)
                state = GameState.MAIN_MENU

    display.render_game_surface(game_surface)
    pygame.display.flip()

pygame.quit()
sys.exit()
