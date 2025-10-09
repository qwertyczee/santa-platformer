import pygame
from typing import Dict, List, Optional, Sequence, Tuple

from constants import ASSETS_DIR, BASE_HEIGHT, BASE_WIDTH, MESSAGE_DURATION


class StoryTextbox:
    """A cinematic textbox capable of rendering scripted sequences."""

    def __init__(
        self,
        body_font: pygame.font.Font,
        name_font: Optional[pygame.font.Font] = None,
        box_margin: Tuple[int, int, int, int] = (56, 340, 56, 36),
    ) -> None:
        self.body_font = body_font
        self.name_font = name_font or body_font
        self.box_margin = box_margin
        self.rect = self._compute_rect()
        self.box_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self._redraw_frame()

        self.pages: List[Dict] = []
        self.current_index = 0
        self.visible_chars = 0.0
        self.speed = 40.0
        self.page_done = False
        self.active = False
        self.finished = False
        self.current_page: Dict = {}
        self.portrait_cache: Dict[str, Optional[pygame.Surface]] = {}
        hint_size = max(18, self.body_font.get_height() - 8)
        self.hint_font = pygame.font.SysFont(self.body_font.get_name(), hint_size)

    def _compute_rect(self) -> pygame.Rect:
        left, top, right, bottom = self.box_margin
        width = BASE_WIDTH - (left + right)
        height = BASE_HEIGHT - (top + bottom)
        return pygame.Rect(left, BASE_HEIGHT - height - bottom, width, height)

    def _redraw_frame(self) -> None:
        self.box_surface.fill((16, 20, 40, 230))
        pygame.draw.rect(
            self.box_surface,
            (210, 225, 255, 255),
            self.box_surface.get_rect(),
            width=3,
            border_radius=16,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self, pages: Sequence[Dict]) -> None:
        self.pages = list(pages or [])
        self.current_index = 0
        self.visible_chars = 0.0
        self.page_done = False
        self.active = bool(self.pages)
        self.finished = not self.pages
        if self.active:
            self._load_page(self.pages[0])
        else:
            self.current_page = {}

    def _load_page(self, page: Dict) -> None:
        self.current_page = page or {}
        self.visible_chars = 0.0
        self.page_done = False
        self.speed = float(self.current_page.get("speed", 40))

    def reset(self) -> None:
        self.pages = []
        self.current_page = {}
        self.visible_chars = 0.0
        self.page_done = False
        self.active = False
        self.finished = False

    # ------------------------------------------------------------------
    # Updates and interaction
    # ------------------------------------------------------------------
    def update(self, dt_ms: int) -> None:
        if not self.active or self.finished:
            return
        text = self.current_page.get("text", "")
        if not text:
            self.page_done = True
            return
        increment = (self.speed / 1000.0) * dt_ms
        self.visible_chars = min(len(text), self.visible_chars + increment)
        if int(self.visible_chars) >= len(text):
            self.page_done = True

    def skip_or_advance(self) -> None:
        if not self.active:
            return
        if not self.page_done:
            self.visible_chars = len(self.current_page.get("text", ""))
            self.page_done = True
            return
        self.current_index += 1
        if self.current_index >= len(self.pages):
            self.active = False
            self.finished = True
            self.current_page = {}
        else:
            self._load_page(self.pages[self.current_index])

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            self.skip_or_advance()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.skip_or_advance()
            return True
        return False

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _load_portrait(self, portrait_name: Optional[str]) -> Optional[pygame.Surface]:
        if not portrait_name:
            return None
        if portrait_name in self.portrait_cache:
            return self.portrait_cache[portrait_name]
        path = ASSETS_DIR / portrait_name
        if not path.exists():
            self.portrait_cache[portrait_name] = None
            return None
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            self.portrait_cache[portrait_name] = None
            return None
        scaled = pygame.transform.smoothscale(image, (96, 96))
        self.portrait_cache[portrait_name] = scaled
        return scaled

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        words = text.split(" ")
        lines: List[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if not candidate:
                continue
            if self.body_font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw(self, surface: pygame.Surface) -> None:
        if not (self.active or self.finished):
            return
        surface.blit(self.box_surface, self.rect)
        if not self.current_page:
            return

        portrait = self._load_portrait(self.current_page.get("portrait"))
        offset_x = 0
        if portrait:
            surface.blit(portrait, (self.rect.x + 20, self.rect.y + 20))
            offset_x = portrait.get_width() + 32

        name = self.current_page.get("speaker")
        text = self.current_page.get("text", "")
        visible_text = text[: int(self.visible_chars)]

        text_x = self.rect.x + 20 + offset_x
        text_y = self.rect.y + 20
        max_width = self.rect.width - 40 - offset_x

        if name:
            name_surface = self.name_font.render(str(name), True, (255, 245, 230))
            surface.blit(name_surface, (text_x, text_y))
            text_y += name_surface.get_height() + 8

        for line in self._wrap_text(visible_text, max_width):
            line_surface = self.body_font.render(line, True, (230, 235, 255))
            surface.blit(line_surface, (text_x, text_y))
            text_y += line_surface.get_height() + 4

        if self.page_done and self.active:
            hint = self.hint_font.render("Press SPACE to continue", True, (200, 210, 255))
            surface.blit(hint, (self.rect.right - hint.get_width() - 20, self.rect.bottom - hint.get_height() - 16))


# ---------------------------------------------------------------------------
# Legacy HUD helpers
# ---------------------------------------------------------------------------

message = ""
message_until = 0


def show_message(text, ms=MESSAGE_DURATION):
    """Display a message for a specified duration."""
    global message, message_until
    message = text
    message_until = pygame.time.get_ticks() + ms


def draw_hud(screen, font, lives, score, level_manager, player):
    """Draw the heads-up display with game information."""
    lives_surf = font.render(f"Lives: {lives}", True, (255, 255, 255))
    level_surf = font.render(f"Level: {level_manager.index + 1} - {level_manager.name}", True, (255, 255, 255))
    score_surf = font.render(f"Presents: {score}/{level_manager.total_presents}", True, (255, 255, 255))
    screen.blit(lives_surf, (10, 8))
    screen.blit(level_surf, (10, 32))
    screen.blit(score_surf, (10, 56))

    now = pygame.time.get_ticks()
    x = BASE_WIDTH - 10
    y = 8
    for ptype in ["double_jump", "speed_boost", "invincibility"]:
        end = player.power_until[ptype]
        if end > now:
            remain_s = (end - now) // 1000 + 1
            text = f"{ptype} {remain_s}s"
            surf = font.render(text, True, (255, 255, 255))
            rect = surf.get_rect(topright=(x, y))
            screen.blit(surf, rect)
            y += 22


def draw_message(screen, font):
    """Draw the current message if active."""
    global message, message_until
    now = pygame.time.get_ticks()
    if message and now < message_until:
        m_surf = font.render(message, True, (255, 255, 255))
        screen.blit(m_surf, (BASE_WIDTH // 2 - m_surf.get_width() // 2, 8))

