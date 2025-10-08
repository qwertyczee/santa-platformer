import pygame
from constants import ASSETS_DIR

# --- Texture Cache ---
_texture_cache = {}

def get_texture(name, size):
    """
    Load and cache a texture with fallback to colored rectangles.
    
    Args:
        name (str): Name of the texture file (without .png extension)
        size (tuple): (width, height) of the texture
        
    Returns:
        pygame.Surface: The loaded or generated texture
    """
    key = (name, size)
    if key in _texture_cache:
        return _texture_cache[key]

    path = ASSETS_DIR / f"{name}.png"
    w, h = size
    surf = None
    if path.exists():
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            surf = pygame.transform.smoothscale(img, (w, h))
        except Exception as e:
            print("Failed to load", path, e)

    if surf is None:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        colors = {
            'player': (200, 40, 40),
            'platform': (139, 69, 19),
            'present': (255, 215, 0),
            'enemy': (245, 245, 245),
            'tree': (20, 120, 20),
            'double_jump': (150, 50, 200),
            'speed_boost': (50, 120, 255),
            'invincibility': (255, 200, 60),
        }
        color = colors.get(name, (120, 120, 120))
        surf.fill(color)
        # small decorations
        if name == 'present':
            pygame.draw.rect(surf, (180, 20, 20), (w//4, 0, w//2, h))         # ribbon vertical
            pygame.draw.rect(surf, (200, 40, 40), (0, h//3, w, h//6))        # ribbon horizontal
        elif name == 'player':
            pygame.draw.rect(surf, (255, 255, 255), (w//6, h//6, w//6, h//8))  # faux beard
        elif name == 'tree':
            pygame.draw.polygon(surf, (10, 80, 10), [(w//2, 0), (w, h), (0, h)])
    
    _texture_cache[key] = surf
    return surf