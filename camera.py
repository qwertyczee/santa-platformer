import pygame
from constants import BASE_WIDTH, BASE_HEIGHT

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0
    
    def update(self, player_rect, level_width, level_height):
        # Simple follow camera, clamped to level bounds
        self.x = int(player_rect.centerx - BASE_WIDTH // 2)
        self.y = int(player_rect.centery - BASE_HEIGHT // 2)
        
        # Clamp to level bounds
        self.x = max(0, min(level_width - BASE_WIDTH, self.x))
        self.y = max(0, min(level_height - BASE_HEIGHT, self.y))
    
    def apply(self, rect):
        """Convert world coordinates to screen coordinates"""
        return pygame.Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)
    
    def apply_pos(self, x, y):
        """Convert world position to screen position"""
        return (x - self.x, y - self.y)