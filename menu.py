# menu.py
import pygame
from typing import List, Optional, Callable, Tuple
from constants import BASE_WIDTH, BASE_HEIGHT
from settings import Settings, DIFFICULTY_PRESETS, key_const_to_name

WHITE = (255,255,255)
GREY  = (210,210,220)
DARK  = (30, 34, 48)
ACCENT= (180,220,255)

class Button:
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font):
        self.rect = rect
        self.text = text
        self.font = font
        self.hover = False
        self.disabled = False

    def draw(self, surf: pygame.Surface):
        color = (60,70,95) if not self.hover else (75, 90, 120)
        if self.disabled: color = (45,45,45)
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, (20,25,40), self.rect, 2, border_radius=8)

        t = self.font.render(self.text, True, WHITE if not self.disabled else (140,140,140))
        surf.blit(t, (self.rect.centerx - t.get_width()//2, self.rect.centery - t.get_height()//2))

    def update_hover(self, mouse_pos: Tuple[int,int]):
        self.hover = self.rect.collidepoint(mouse_pos)

    def clicked(self, ev: pygame.event.Event) -> bool:
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos) and not self.disabled)

class MenuBase:
    def __init__(self, title: str, big_font, font):
        self.title = title
        self.big_font = big_font
        self.font = font
        self.buttons: List[Button] = []

    def draw_title(self, surf):
        t = self.big_font.render(self.title, True, WHITE)
        surf.blit(t, (BASE_WIDTH//2 - t.get_width()//2, 70))

    def layout_buttons(self, labels: List[str], start_y=170, gap=60, width=360, height=48):
        self.buttons = []
        x = BASE_WIDTH//2 - width//2
        for i, label in enumerate(labels):
            rect = pygame.Rect(x, start_y + i*gap, width, height)
            self.buttons.append(Button(rect, label, self.font))

    def draw_and_handle(self, surf, events, to_base_pos) -> Optional[str]:
        mx, my = to_base_pos(*pygame.mouse.get_pos())   # <- base coords
        for b in self.buttons:
            b.update_hover((mx, my))
            b.draw(surf)

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                ex, ey = to_base_pos(*ev.pos)           # <- base coords
                for b in self.buttons:
                    if b.rect.collidepoint((ex, ey)) and not b.disabled:
                        return b.text
        return None

class MainMenu(MenuBase):
    def __init__(self, big_font, font):
        super().__init__("Santa Platformer", big_font, font)
        self.layout_buttons(["Start", "Level Selector", "Options", "Quit"])

    def render(self, surf, events, to_base_pos):
        surf.fill(DARK)
        self.draw_title(surf)
        return self.draw_and_handle(surf, events, to_base_pos)

class PauseMenu(MenuBase):
    def __init__(self, big_font, font):
        super().__init__("Paused", big_font, font)
        self.layout_buttons(["Resume", "Options", "Quit to Menu"])

    def render(self, surf, events, to_base_pos):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        surf.blit(overlay, (0,0))
        self.draw_title(surf)
        return self.draw_and_handle(surf, events, to_base_pos)

class LevelSelect(MenuBase):
    def __init__(self, big_font, font, level_names: List[str]):
        super().__init__("Select Level", big_font, font)
        # create buttons for each level + back
        start_y = 160
        width, height = 420, 44
        gap = 52
        self.buttons = []
        x = BASE_WIDTH//2 - width//2
        for i, name in enumerate(level_names):
            rect = pygame.Rect(x, start_y + i*gap, width, height)
            self.buttons.append(Button(rect, f"Start: {i+1} – {name}", font))
        self.back_btn = Button(pygame.Rect(x, start_y + len(level_names)*gap + 20, width, height), "Back", font)

    def render(self, surf, events, to_base_pos):
        surf.fill(DARK)
        self.draw_title(surf)

        mx, my = to_base_pos(*pygame.mouse.get_pos())
        for b in self.buttons + [self.back_btn]:
            b.update_hover((mx, my))
            b.draw(surf)

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                ex, ey = to_base_pos(*ev.pos)
                for idx, b in enumerate(self.buttons):
                    if b.rect.collidepoint((ex, ey)):
                        return f"START_LEVEL_{idx}"
                if self.back_btn.rect.collidepoint((ex, ey)):
                    return "Back"
        return None

class OptionsMenu(MenuBase):
    """
    Options screen with:
      - Difficulty left/right buttons (cycles presets)
      - Control rebind rows (Left, Right, Jump, Pause)
      - Back button
    Render & hit-testing expect a `to_base_pos` callable with signature (screen_x, screen_y) -> (base_x, base_y).
    """
    def __init__(self, big_font, font, settings: Settings):
        super().__init__("Options", big_font, font)
        self.settings = settings

        # Difficulty labels & index (safeguard default)
        self.diff_labels = list(DIFFICULTY_PRESETS.keys())
        self.diff_index = self.diff_labels.index(settings.difficulty) if settings.difficulty in self.diff_labels else 1

        # State for rebind flow (action string) or None
        self.awaiting_rebind: Optional[str] = None

        # Buttons (positions in base 800x600 space)
        self.diff_left  = Button(pygame.Rect(220, 170, 40, 40), "<", font)
        self.diff_right = Button(pygame.Rect(540, 170, 40, 40), ">", font)
        self.back_btn   = Button(pygame.Rect(BASE_WIDTH//2 - 180, 520, 360, 48), "Back", font)

        # Control rows: create buttons showing current mapping (use settings.controls)
        y0 = 260
        gap = 56
        self.control_buttons = []
        for i, action in enumerate(["left", "right", "jump", "pause"]):
            # right-side button that shows the mapped key name
            rect = pygame.Rect(460, y0 + i*gap, 180, 40)
            current_label = self.settings.controls.get(action, action.upper())
            self.control_buttons.append((action, Button(rect, current_label, font)))

    def render(
        self,
        surf: pygame.Surface,
        events: list,
        to_base_pos: Callable[[int, int], Tuple[int, int]]
    ) -> Optional[str]:
        """
        Draw the options menu onto `surf`, process `events`.
        `to_base_pos` must convert screen coordinates -> base (800x600) coordinates.
        Returns:
          - "Back" when back button is pressed
          - None otherwise
        """
        surf.fill(DARK)
        self.draw_title(surf)

        # --- Difficulty display ---
        label = self.font.render("Difficulty:", True, GREY)
        value = self.font.render(self.diff_labels[self.diff_index], True, WHITE)
        surf.blit(label, (220, 140))
        surf.blit(value, (BASE_WIDTH//2 - value.get_width()//2, 178))

        # --- Draw controls & buttons using base-space mouse coords for hover ---
        mx_screen, my_screen = pygame.mouse.get_pos()
        mx, my = to_base_pos(mx_screen, my_screen)

        # gather every interactable button for hover/draw
        all_buttons = [self.diff_left, self.diff_right, self.back_btn] + [btn for _, btn in self.control_buttons]
        for b in all_buttons:
            b.update_hover((mx, my))
            b.draw(surf)

        # control labels (left side)
        y0 = 260
        gap = 56
        for i, (action, btn) in enumerate(self.control_buttons):
            text = self.font.render(action.capitalize(), True, GREY)
            surf.blit(text, (220, y0 + i*gap + 8))

        # awaiting rebind hint
        if self.awaiting_rebind:
            hint = self.font.render(f"Press a key for {self.awaiting_rebind.upper()}...", True, ACCENT)
            surf.blit(hint, (BASE_WIDTH//2 - hint.get_width()//2, 470))

        # --- Event handling (use base coords for mouse clicks) ---
        for ev in events:
            # If we are waiting for a keyboard rebind, capture the next KEYDOWN
            if self.awaiting_rebind and ev.type == pygame.KEYDOWN:
                # store mapping as name (uppercase) via settings helper
                self.settings.set_key(self.awaiting_rebind, ev.key)
                # update the button label for that action
                for act, btn in self.control_buttons:
                    if act == self.awaiting_rebind:
                        btn.text = key_const_to_name(ev.key)
                        break
                self.awaiting_rebind = None
                # continue processing other events normally
                continue

            # Mouse clicks: convert click pos to base-space before testing rects
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                ex, ey = to_base_pos(*ev.pos)

                # Difficulty left/right
                if self.diff_left.rect.collidepoint((ex, ey)):
                    self.diff_index = (self.diff_index - 1) % len(self.diff_labels)
                    self.settings.difficulty = self.diff_labels[self.diff_index]
                    self.settings.apply_difficulty()
                    self.settings.save()
                    continue

                if self.diff_right.rect.collidepoint((ex, ey)):
                    self.diff_index = (self.diff_index + 1) % len(self.diff_labels)
                    self.settings.difficulty = self.diff_labels[self.diff_index]
                    self.settings.apply_difficulty()
                    self.settings.save()
                    continue

                # Back button
                if self.back_btn.rect.collidepoint((ex, ey)):
                    return "Back"

                # Control rebind buttons
                for action, btn in self.control_buttons:
                    if btn.rect.collidepoint((ex, ey)):
                        # Enter rebind mode for this action
                        self.awaiting_rebind = action
                        # Visual feedback: change text to "..." while waiting
                        btn.text = "..."
                        break

        return None