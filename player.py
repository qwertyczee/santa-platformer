import pygame
from constants import BASE_SPEED, BASE_JUMP, ANIMATION_SPEED, RESPAWN_INVINCIBLE_TIME, COYOTE_TIME
from utils import get_texture

class Player:
    def __init__(self, start_x, start_y):
        self.w, self.h = 40, 60
        self.rect = pygame.Rect(start_x, start_y, self.w, self.h)
        self.x = float(start_x)
        self.y = float(start_y)
        self.vx = 0
        self.vy = 0
        self.base_speed = BASE_SPEED
        self.speed = self.base_speed
        self.jump_strength = BASE_JUMP
        self.max_jumps = 1
        self.jumps_remaining = self.max_jumps
        self.facing_right = True
        
        # Coyote time - allows jumping shortly after leaving a platform
        self.last_ground_time = 0
        self.on_ground = False

        # powerups timers
        self.power_until = {'speed_boost':0,'double_jump':0,'invincibility':0}
        self.hit_invincible_until = 0

        # --- Animation ---
        self.idle_frame = get_texture("player", (self.w, self.h))
        self.walk_frames = [
            get_texture("player1", (self.w, self.h)),
            get_texture("player2", (self.w, self.h))
        ]
        self.current_frame = 0
        self.animation_timer = 0
        self.animation_speed = ANIMATION_SPEED

    def update_animation(self, dt_ms):
        if self.vx != 0:  # moving
            self.animation_timer += dt_ms
            if self.animation_timer >= self.animation_speed:
                self.animation_timer = 0
                self.current_frame = (self.current_frame + 1) % len(self.walk_frames)
        else:
            self.current_frame = 0  # reset walk animation when idle

    def get_current_frame(self):
        if self.vx != 0:  # moving
            frame = self.walk_frames[self.current_frame]
        else:  # idle
            frame = self.idle_frame

        # Flip horizontally if facing left
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)

        return frame

    def is_invincible(self, now_ms):
        return now_ms < self.power_until['invincibility'] or now_ms < self.hit_invincible_until

    def update_powerups(self, now_ms):
        # speed boost duration effect
        if now_ms < self.power_until['speed_boost']:
            self.speed = self.base_speed * 1.8
        else:
            self.speed = self.base_speed

        # double jump effect
        if now_ms < self.power_until['double_jump']:
            self.max_jumps = 2
        else:
            self.max_jumps = 1

        # reset jumps when landing handled elsewhere
        # invincibility handled in is_invincible()

    def apply_powerup(self, ptype, duration_ms, now_ms):
        self.power_until[ptype] = now_ms + duration_ms
        # if double jump power gained immediately refill jumps so player can use it right away
        if ptype == 'double_jump':
            self.jumps_remaining = self.max_jumps if now_ms < self.power_until['double_jump'] else self.jumps_remaining

    def respawn(self, start_x, start_y):
        self.x = float(start_x)
        self.y = float(start_y)
        self.rect.topleft = (start_x, start_y)
        self.vx = 0
        self.vy = 0
        # give a short invincible window after respawn
        self.hit_invincible_until = pygame.time.get_ticks() + RESPAWN_INVINCIBLE_TIME
        # Reset coyote time on respawn
        self.last_ground_time = 0
        self.on_ground = False
        
    def can_jump(self, current_time):
        """Check if player can jump, considering coyote time"""
        # Can jump if we have jumps remaining AND either:
        # 1. Currently on ground, OR
        # 2. Within coyote time window after leaving ground, OR
        # 3. Have double jump ability (max_jumps > 1) and this is not the first jump
        if self.jumps_remaining <= 0:
            return False
            
        if self.on_ground:
            return True
            
        # Check if we're within coyote time window (only for first jump)
        time_since_ground = current_time - self.last_ground_time
        if time_since_ground <= COYOTE_TIME:
            return True

        # If we have double jump (max_jumps > 1), allow jumping even in air
        # but only if we haven't used all jumps yet
        if self.max_jumps > 1:
            return True

        return False