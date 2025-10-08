import pygame
from constants import BASE_WIDTH, MESSAGE_DURATION

# Message display variables
message = ""
message_until = 0

def show_message(text, ms=MESSAGE_DURATION):
    """Display a message for a specified duration."""
    global message, message_until
    message = text
    message_until = pygame.time.get_ticks() + ms

def draw_hud(screen, font, lives, score, level_manager, player):
    """Draw the heads-up display with game information."""
    # Lives, Level, Score
    lives_surf = font.render(f"Lives: {lives}", True, (255,255,255))
    level_surf = font.render(f"Level: {level_manager.index+1} - {level_manager.name}", True, (255,255,255))
    score_surf = font.render(f"Presents: {score}/{level_manager.total_presents}", True, (255,255,255))
    screen.blit(lives_surf, (10, 8))
    screen.blit(level_surf, (10, 32))
    screen.blit(score_surf, (10, 56))

    # active powerups + timers
    now = pygame.time.get_ticks()
    x = BASE_WIDTH - 10
    y = 8
    for ptype in ['double_jump','speed_boost','invincibility']:
        end = player.power_until[ptype]
        if end > now:
            remain_s = (end - now) // 1000 + 1
            text = f"{ptype} {remain_s}s"
            surf = font.render(text, True, (255,255,255))
            rect = surf.get_rect(topright=(x,y))
            screen.blit(surf, rect)
            y += 22

def draw_message(screen, font):
    """Draw the current message if active."""
    global message, message_until
    now = pygame.time.get_ticks()
    if message and now < message_until:
        m_surf = font.render(message, True, (255, 255, 255))
        screen.blit(m_surf, (BASE_WIDTH//2 - m_surf.get_width()//2, 8))