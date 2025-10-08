import pygame
from constants import BASE_WIDTH, BASE_HEIGHT

class DisplayManager:
    def __init__(self):
        self.base_width = BASE_WIDTH
        self.base_height = BASE_HEIGHT
        self.screen = None
        self.width = 0
        self.height = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self.init_display()
    
    def init_display(self):
        """Initialize the display with a simple resizable window."""
        # Start with a reasonable window size
        info = pygame.display.Info()
        self.width = min(1200, info.current_w - 100)
        self.height = min(900, info.current_h - 100)
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        
        self.calculate_scaling()

    def to_base_pos(self, sx, sy):
        """Convert screen coords to base (800x600) coords for UI hit-testing."""
        # ochrana proti dělení nulou (nemělo by nastat)
        scale_x = self.scale_x if self.scale_x != 0 else 1.0
        scale_y = self.scale_y if self.scale_y != 0 else 1.0
        bx = (sx - self.offset_x) / scale_x
        by = (sy - self.offset_y) / scale_y
        return int(bx), int(by)
    
    def calculate_scaling(self):
        """Calculate scaling factors to maintain aspect ratio."""
        # Calculate scaling to fit the screen while maintaining aspect ratio
        scale_x = self.width / self.base_width
        scale_y = self.height / self.base_height
        
        # Use the smaller scale to ensure everything fits
        self.scale = min(scale_x, scale_y)
        self.scale_x = self.scale
        self.scale_y = self.scale
        
        # Calculate the actual game area size
        self.game_width = int(self.base_width * self.scale)
        self.game_height = int(self.base_height * self.scale)
        
        # Calculate offset to center the game area
        self.offset_x = (self.width - self.game_width) // 2
        self.offset_y = (self.height - self.game_height) // 2
    
    def scale_pos(self, x, y):
        """Scale position from base resolution to actual screen resolution."""
        scaled_x = int(x * self.scale_x) + self.offset_x
        scaled_y = int(y * self.scale_y) + self.offset_y
        return scaled_x, scaled_y
    
    def scale_rect(self, rect):
        """Scale a rectangle from base resolution to actual screen resolution."""
        x = int(rect.x * self.scale_x) + self.offset_x
        y = int(rect.y * self.scale_y) + self.offset_y
        w = int(rect.width * self.scale_x)
        h = int(rect.height * self.scale_y)
        return pygame.Rect(x, y, w, h)
    
    def scale_surface(self, surface):
        """Scale a surface to match the display scale."""
        if self.scale != 1.0:
            new_width = int(surface.get_width() * self.scale)
            new_height = int(surface.get_height() * self.scale)
            return pygame.transform.scale(surface, (new_width, new_height))
        return surface
    
    def create_game_surface(self):
        """Create a surface for rendering the game at base resolution."""
        return pygame.Surface((self.base_width, self.base_height))
    
    def render_game_surface(self, game_surface):
        """Render the game surface to the screen with proper scaling."""
        if self.scale != 1.0:
            scaled_surface = pygame.transform.scale(game_surface, (self.game_width, self.game_height))
            self.screen.blit(scaled_surface, (self.offset_x, self.offset_y))
        else:
            self.screen.blit(game_surface, (0, 0))
    
    def resize_window(self, new_width, new_height):
        """Handle window resize event."""
        self.width = new_width
        self.height = new_height
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.calculate_scaling()