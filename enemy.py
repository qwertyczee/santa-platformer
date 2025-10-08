import pygame

class Enemy:
    def __init__(self, x, y, w, h, patrol_min_x, patrol_max_x, speed=2):
        self.rect = pygame.Rect(x, y, w, h)
        self.vx = speed
        self.patrol_min = patrol_min_x
        self.patrol_max = patrol_max_x
        self.speed = speed

    def update(self):
        self.rect.x += self.vx
        if self.rect.x < self.patrol_min:
            self.rect.x = self.patrol_min
            self.vx = abs(self.speed)
        elif self.rect.x > self.patrol_max:
            self.rect.x = self.patrol_max
            self.vx = -abs(self.speed)