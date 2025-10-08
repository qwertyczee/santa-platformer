import pygame
import sys
from pathlib import Path

# Import our modules
from constants import BASE_WIDTH, BASE_HEIGHT, FPS, STARTING_LIVES, GRAVITY, MAX_FALL, LEVEL_COMPLETE_DELAY, ASSETS_DIR, POWERUP_DURATIONS
from display import DisplayManager
from player import Player
from level import LevelManager, LEVELS
from camera import Camera
from collision import resolve_horizontal, resolve_vertical, clamp_player_to_level
from ui import draw_hud, draw_message, show_message
from utils import get_texture

pygame.init()

# --- Game Initialization ---
display = DisplayManager()
pygame.display.set_caption("Santa Platformer (Pygame)")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)
big_font = pygame.font.SysFont(None, 48)

# Create game surface for rendering at base resolution
game_surface = display.create_game_surface()

# --- Game Objects ---
level_manager = LevelManager(LEVELS)
player = Player(*level_manager.player_start)
camera = Camera()
lives = STARTING_LIVES
score = 0
level_complete_time = None

# --- Main Game Loop ---
running = True
while running:
    dt_ms = clock.tick(FPS)
    now = pygame.time.get_ticks()

    # --- Events ---
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.VIDEORESIZE:
            # Handle window resize
            display.resize_window(ev.w, ev.h)
            game_surface = display.create_game_surface()
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.key in (pygame.K_UP, pygame.K_SPACE, pygame.K_w):
                # jump press
                if player.jumps_remaining > 0:
                    player.vy = player.jump_strength
                    player.jumps_remaining -= 1
        elif ev.type == pygame.KEYUP:
            pass

    # --- Input Handling ---
    keys = pygame.key.get_pressed()
    player.vx = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player.vx = -player.speed
        player.facing_right = False
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player.vx = player.speed
        player.facing_right = True

    # update powerup effects
    player.update_powerups(now)

    # --- Physics ---
    # apply gravity
    player.vy += GRAVITY
    if player.vy > MAX_FALL:
        player.vy = MAX_FALL

    # update position floats
    player.x += player.vx
    # resolve horizontal collisions
    resolve_horizontal(player, [level_manager.ground] + level_manager.platforms)

    player.y += player.vy
    on_ground = resolve_vertical(player, [level_manager.ground] + level_manager.platforms)

    # clamp player to level bounds
    clamp_player_to_level(player, level_manager.width, level_manager.height)

    # --- Camera Update ---
    camera.update(player.rect, level_manager.width, level_manager.height)

    # --- Enemies Update ---
    for e in level_manager.enemies:
        e.update()

    # --- Collisions: presents ---
    for p in level_manager.presents[:]:
        if player.rect.colliderect(p["rect"]):
            level_manager.presents.remove(p)
            score += 1
            show_message("Present collected!", 900)

    # --- Collisions: powerups ---
    for pu in level_manager.powerups[:]:
        if player.rect.colliderect(pu['rect']):
            ptype = pu['type']
            player.apply_powerup(ptype, POWERUP_DURATIONS[ptype], now)
            level_manager.powerups.remove(pu)
            show_message(f"Powerup: {ptype}", 1100)

    # --- Collisions: enemies ---
    collided_enemy = None
    for e in level_manager.enemies:
        if player.rect.colliderect(e.rect):
            collided_enemy = e
            break

    if collided_enemy:
        if not player.is_invincible(now):
            lives -= 1
            if lives <= 0:
                # Game Over -> restart everything
                show_message("Game Over! Restarting...", 2000)
                pygame.time.delay(1200)
                # Restart full game
                level_manager = LevelManager(LEVELS)
                player = Player(*level_manager.player_start)
                lives = STARTING_LIVES
                score = 0
                continue
            else:
                # respawn player at start of current level
                player.respawn(*level_manager.player_start)
                show_message("You lost a life!", 900)

    # --- Goal Check ---
    if player.rect.colliderect(level_manager.goal):
        if score >= level_manager.total_presents:
            if not level_manager.completed:
                # Mark level completed and start timer (don't switch levels yet)
                level_manager.completed = True
                level_complete_time = pygame.time.get_ticks()
                show_message("Level Complete!", 1500)
        else:
            show_message("Collect all presents before the tree!", 1300)

    # --- Drawing ---
    if level_manager.background:
        game_surface.blit(level_manager.background, (-camera.x, -camera.y))
    else:
        game_surface.fill((24, 36, 60))  # fallback
    
    game_surface.blit(level_manager.overlay, (-camera.x, -camera.y))

    # draw ground (tiled horizontally)
    tile = pygame.image.load("assets/ground.png").convert_alpha()
    tile_width = tile.get_width()
    tile_height = tile.get_height()

    for x in range(0, level_manager.ground.width, tile_width):
        game_surface.blit(tile, (level_manager.ground.x + x - camera.x,
                        level_manager.ground.y - camera.y))
        
    # draw floating platforms
    for plat in level_manager.platforms:
        surf = get_texture('platform', (plat.width, plat.height))
        game_surface.blit(surf, (plat.x - camera.x, plat.y - camera.y))

    # draw presents
    for p in level_manager.presents:
        surf = get_texture(p["texture"], (p["rect"].width, p["rect"].height))
        game_surface.blit(surf, (p["rect"].x - camera.x, p["rect"].y - camera.y))

    # draw powerups
    for pu in level_manager.powerups:
        surf = get_texture(pu['type'], (pu['rect'].width, pu['rect'].height))
        game_surface.blit(surf, (pu['rect'].x - camera.x, pu['rect'].y - camera.y))

    # draw enemies
    for e in level_manager.enemies:
        surf = get_texture('enemy', (e.rect.width, e.rect.height))
        game_surface.blit(surf, (e.rect.x - camera.x, e.rect.y - camera.y))

    # draw goal (tree)
    tree_texture_name = 'tree1' if level_manager.completed else 'tree'
    surf_tree = get_texture(tree_texture_name, (level_manager.goal.width, level_manager.goal.height))
    game_surface.blit(surf_tree, (level_manager.goal.x - camera.x, level_manager.goal.y - camera.y))
    
    player.update_animation(dt_ms)  # dt_ms from clock.tick()
    surf_player = player.get_current_frame()

    # invincibility flicker
    if not (player.is_invincible(now) and (now // 150) % 2 == 0):
        game_surface.blit(surf_player, (player.rect.x - camera.x, player.rect.y - camera.y))

    # HUD
    draw_hud(game_surface, font, lives, score, level_manager, player)
    
    # message text
    draw_message(game_surface, font)

    # --- Handle delayed level switch ---
    if level_manager.completed and level_complete_time is not None:
        if pygame.time.get_ticks() - level_complete_time > LEVEL_COMPLETE_DELAY:
            advanced = level_manager.next_level()
            if advanced:
                player = Player(*level_manager.player_start)
                score = 0
                level_manager.completed = False
                level_complete_time = None
            else:
                # final victory
                game_surface.fill((10,10,40))
                text = big_font.render("You saved Christmas! 🎅🎉", True, (255,255,200))
                game_surface.blit(text, (BASE_WIDTH//2 - text.get_width()//2, BASE_HEIGHT//2 - text.get_height()//2))
                display.render_game_surface(game_surface)
                pygame.display.flip()
                pygame.time.delay(3000)
                # restart game
                level_manager = LevelManager(LEVELS)
                player = Player(*level_manager.player_start)
                lives = STARTING_LIVES
                score = 0
                level_complete_time = None
    
    # Render game surface to screen with scaling
    display.render_game_surface(game_surface)
    pygame.display.flip()

pygame.quit()
sys.exit()