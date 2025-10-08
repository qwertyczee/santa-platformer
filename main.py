import sys
from typing import Optional

import pygame

from constants import (
    ASSETS_DIR,
    BASE_HEIGHT,
    BASE_WIDTH,
    FPS,
    GRAVITY,
    LEVEL_COMPLETE_DELAY,
    MAX_FALL,
    POWERUP_DURATIONS,
    GameState,
)
from display import DisplayManager
from player import Player
from level import LevelManager, load_campaign_data
from camera import Camera
from collision import clamp_player_to_level, resolve_horizontal, resolve_vertical
from ui import StoryTextbox, draw_hud, draw_message, show_message
from utils import get_texture
from settings import Settings
from menu import LevelSelect, MainMenu, OptionsMenu, PauseMenu


pygame.init()

# ---------------------------------------------------------------------------
# Core systems
# ---------------------------------------------------------------------------
display = DisplayManager()
pygame.display.set_caption("Santa Platformer (Story Edition)")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
big_font = pygame.font.SysFont(None, 48)

story_box = StoryTextbox(font, big_font)

ground_tile = pygame.image.load(str(ASSETS_DIR / "ground.png")).convert_alpha()
ground_tile_width = ground_tile.get_width()

game_surface = display.create_game_surface()
settings = Settings.load()

# Load campaign data once and reuse for every level
campaign_data = load_campaign_data()
level_names = [lvl.get("name", f"Level {idx + 1}") for idx, lvl in enumerate(campaign_data.get("levels", []))]
if not level_names:
    level_names = ["Story Level"]

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
state = GameState.MAIN_MENU
previous_state = GameState.MAIN_MENU

main_menu = MainMenu(big_font, font)
pause_menu = PauseMenu(big_font, font)
level_select = LevelSelect(big_font, font, level_names)
options_menu = OptionsMenu(big_font, font, settings)

level_manager: Optional[LevelManager] = None
player: Optional[Player] = None
camera: Optional[Camera] = None
lives = 0
score = 0
level_complete_time: Optional[int] = None

story_next_state = GameState.PLAYING
story_post_action = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def spawn_player(reset_score: bool = True) -> None:
    global player, camera, score
    player = Player(*level_manager.player_start)
    camera = Camera()
    if reset_score:
        score = 0


def start_new_game(level_index: int = 0) -> None:
    global level_manager, lives, level_complete_time
    level_manager = LevelManager(campaign_data, settings=settings, index=level_index)
    spawn_player(reset_score=True)
    lives = settings.lives
    level_complete_time = None


def begin_story(sequence, story_state, next_state=GameState.PLAYING, post_action=None):
    global state, story_next_state, story_post_action
    if sequence:
        story_box.start(sequence)
        story_next_state = next_state
        story_post_action = post_action
        state = story_state
        pygame.mouse.set_visible(True)
    else:
        if callable(post_action):
            post_action()
        else:
            state = next_state
            if state == GameState.PLAYING:
                pygame.mouse.set_visible(False)


def finish_story():
    global state, story_post_action
    story_box.reset()
    post_action = story_post_action
    story_post_action = None
    if callable(post_action):
        post_action()
    else:
        state = story_next_state
        if state == GameState.PLAYING:
            pygame.mouse.set_visible(False)


def advance_to_next_level():
    global level_complete_time, state
    if level_manager and level_manager.next_level():
        spawn_player(reset_score=True)
        level_manager.completed = False
        level_complete_time = None
        intro = level_manager.story_intro
        if intro:
            begin_story(intro, GameState.STORY_INTRO, GameState.PLAYING)
        else:
            state = GameState.PLAYING
            pygame.mouse.set_visible(False)
    else:
        game_surface.fill((10, 10, 40))
        text = big_font.render("You saved Christmas! 🎅🎉", True, (255, 255, 200))
        game_surface.blit(text, (BASE_WIDTH // 2 - text.get_width() // 2, BASE_HEIGHT // 2 - text.get_height() // 2))
        display.render_game_surface(game_surface)
        pygame.display.flip()
        pygame.time.delay(2200)
        pygame.mouse.set_visible(True)
        state = GameState.MAIN_MENU


def handle_checkpoint(checkpoint: dict) -> bool:
    sequence = level_manager.activate_checkpoint(checkpoint["id"])
    show_message("Checkpoint reached!", 1000)
    story_started = False
    if sequence:
        begin_story(sequence, GameState.STORY_INTERLUDE, GameState.PLAYING)
        story_started = True
    if dispatch_events("checkpoint_reached", checkpoint["id"]):
        story_started = True
    return story_started


def dispatch_events(trigger_type: str, value) -> bool:
    triggered_story = False
    triggered = level_manager.handle_progress_event(trigger_type, value)
    for event in triggered:
        level_manager.apply_event_effect(event)
        sequence_id = event.get("story")
        if sequence_id and not triggered_story:
            begin_story(level_manager.get_story_sequence(sequence_id), GameState.STORY_INTERLUDE, GameState.PLAYING)
            triggered_story = True
    return triggered_story


def draw_world(include_hud: bool = True) -> None:
    if not level_manager or not player:
        game_surface.fill((24, 36, 60))
        return

    if level_manager.background:
        game_surface.blit(level_manager.background, (-camera.x, -camera.y))
    else:
        game_surface.fill((24, 36, 60))

    if level_manager.overlay:
        game_surface.blit(level_manager.overlay, (-camera.x, -camera.y))

    ground = level_manager.ground
    for x in range(0, max(ground.width, BASE_WIDTH), ground_tile_width):
        game_surface.blit(
            ground_tile,
            (ground.x + x - camera.x, ground.y - camera.y),
        )

    for plat in level_manager.platforms:
        surf = get_texture("platform", (plat.width, plat.height))
        game_surface.blit(surf, (plat.x - camera.x, plat.y - camera.y))

    for present in level_manager.presents:
        rect = present["rect"]
        surf = get_texture(present["texture"], (rect.width, rect.height))
        game_surface.blit(surf, (rect.x - camera.x, rect.y - camera.y))

    for power in level_manager.powerups:
        rect = power["rect"]
        surf = get_texture(power["type"], (rect.width, rect.height))
        game_surface.blit(surf, (rect.x - camera.x, rect.y - camera.y))

    for enemy in level_manager.enemies:
        surf = get_texture("enemy", (enemy.rect.width, enemy.rect.height))
        game_surface.blit(surf, (enemy.rect.x - camera.x, enemy.rect.y - camera.y))

    tree_texture = "tree1" if level_manager.completed else "tree"
    tree_surf = get_texture(tree_texture, (level_manager.goal.width, level_manager.goal.height))
    game_surface.blit(tree_surf, (level_manager.goal.x - camera.x, level_manager.goal.y - camera.y))

    player.update_animation(clock.get_time())
    if not (player.is_invincible(pygame.time.get_ticks()) and (pygame.time.get_ticks() // 150) % 2 == 0):
        frame = player.get_current_frame()
        game_surface.blit(frame, (player.rect.x - camera.x, player.rect.y - camera.y))

    if include_hud:
        draw_hud(game_surface, font, lives, score, level_manager, player)
        draw_message(game_surface, font)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
pygame.mouse.set_visible(True)
running = True
while running:
    dt_ms = clock.tick(FPS)
    now = pygame.time.get_ticks()
    events = list(pygame.event.get())

    for event in events:
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            display.resize_window(event.w, event.h)
            game_surface = display.create_game_surface()

    if state == GameState.MAIN_MENU:
        pygame.mouse.set_visible(True)
        action = main_menu.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()

        if action == "Start":
            start_new_game(0)
            if level_manager.story_intro:
                begin_story(level_manager.story_intro, GameState.STORY_INTRO, GameState.PLAYING)
            else:
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
        selection = level_select.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()

        if selection == "Back":
            state = GameState.MAIN_MENU
        elif isinstance(selection, str) and selection.startswith("START_LEVEL_"):
            idx = int(selection.split("_")[-1])
            start_new_game(idx)
            if level_manager.story_intro:
                begin_story(level_manager.story_intro, GameState.STORY_INTRO, GameState.PLAYING)
            else:
                state = GameState.PLAYING
                pygame.mouse.set_visible(False)
        continue

    if state == GameState.OPTIONS:
        pygame.mouse.set_visible(True)
        action = options_menu.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()
        if action == "Back":
            state = previous_state
            if previous_state == GameState.LEVEL_SELECT:
                level_select = LevelSelect(big_font, font, level_names)
        continue

    if state == GameState.PAUSED:
        pygame.mouse.set_visible(True)
        action = pause_menu.render(game_surface, events, display.to_base_pos)
        display.render_game_surface(game_surface)
        pygame.display.flip()

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == settings.get_key("pause"):
                state = GameState.PLAYING
                pygame.mouse.set_visible(False)

        if action == "Resume":
            state = GameState.PLAYING
            pygame.mouse.set_visible(False)
        elif action == "Options":
            previous_state = GameState.PAUSED
            state = GameState.OPTIONS
        elif action == "Quit to Menu":
            state = GameState.MAIN_MENU
        continue

    if state in (GameState.STORY_INTRO, GameState.STORY_INTERLUDE, GameState.STORY_OUTRO):
        pygame.mouse.set_visible(True)
        story_box.update(dt_ms)
        for event in events:
            story_box.handle_event(event)
        draw_world(include_hud=False)
        story_box.draw(game_surface)
        display.render_game_surface(game_surface)
        pygame.display.flip()
        if story_box.finished:
            finish_story()
        continue

    # ------------------------------------------------------------------
    # PLAYING
    # ------------------------------------------------------------------
    pygame.mouse.set_visible(False)
    keys = pygame.key.get_pressed()

    for event in events:
        if event.type == pygame.KEYDOWN:
            if event.key == settings.get_key("pause"):
                state = GameState.PAUSED
            elif event.key == settings.get_key("jump") and player and player.can_jump(now):
                player.vy = player.jump_strength
                player.jumps_remaining -= 1

    player.vx = 0
    if keys[settings.get_key("left")]:
        player.vx = -player.speed
        player.facing_right = False
    if keys[settings.get_key("right")]:
        player.vx = player.speed
        player.facing_right = True

    def scaled_duration(ptype: str) -> int:
        base = POWERUP_DURATIONS[ptype]
        return int(base * settings.powerup_mult)

    player.update_powerups(now)

    player.vy += GRAVITY
    if player.vy > MAX_FALL:
        player.vy = MAX_FALL

    player.x += player.vx
    resolve_horizontal(player, [level_manager.ground] + level_manager.platforms)
    player.y += player.vy
    resolve_vertical(player, [level_manager.ground] + level_manager.platforms)
    clamp_player_to_level(player, level_manager.width, level_manager.height)

    checkpoint = level_manager.checkpoint_collisions(player.rect)
    if checkpoint and handle_checkpoint(checkpoint):
        continue

    camera.update(player.rect, level_manager.width, level_manager.height)
    for enemy in level_manager.enemies:
        enemy.update()

    story_triggered = False
    for present in level_manager.presents[:]:
        if player.rect.colliderect(present["rect"]):
            level_manager.presents.remove(present)
            score += 1
            show_message("Present collected!", 900)
            if dispatch_events("presents_collected", score):
                story_triggered = True
                break

    if story_triggered or state != GameState.PLAYING:
        continue

    for power in level_manager.powerups[:]:
        if player.rect.colliderect(power["rect"]):
            ptype = power["type"]
            player.apply_powerup(ptype, scaled_duration(ptype), now)
            level_manager.powerups.remove(power)
            show_message(f"Powerup: {ptype}", 1100)

    collided_enemy = None
    for enemy in level_manager.enemies:
        if player.rect.colliderect(enemy.rect):
            collided_enemy = enemy
            break

    if collided_enemy and not player.is_invincible(now):
        lives -= 1
        if lives <= 0:
            show_message("Game Over! Returning to Menu...", 1800)
            pygame.time.delay(1200)
            state = GameState.MAIN_MENU
            pygame.mouse.set_visible(True)
            continue
        player.respawn(*level_manager.player_start)
        show_message("You lost a life!", 900)

    if player.rect.colliderect(level_manager.goal):
        if score >= level_manager.total_presents:
            if not level_manager.completed:
                level_manager.completed = True
                level_complete_time = now
                show_message("Level Complete!", 1500)
        else:
            show_message("Collect all presents before the tree!", 1300)

    draw_world(include_hud=True)
    display.render_game_surface(game_surface)
    pygame.display.flip()

    if level_manager.completed and level_complete_time is not None:
        if now - level_complete_time > LEVEL_COMPLETE_DELAY:
            if level_manager.story_outro and not level_manager.outro_played:
                level_manager.outro_played = True
                begin_story(level_manager.story_outro, GameState.STORY_OUTRO, GameState.MAIN_MENU, post_action=advance_to_next_level)
            else:
                advance_to_next_level()

pygame.quit()
sys.exit()
