"""Players and keyboard controllers for Table Hockey."""

from dataclasses import dataclass

import pygame


@dataclass
class Player:
    """Scoreboard identity for one side of the table."""

    number: int
    name: str
    color: tuple
    score: int = 0

    def reset_score(self):
        self.score = 0


class HumanController:
    """Maps four keyboard keys to a normalized movement vector."""

    def __init__(self, up, down, left, right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right

    def direction(self, pressed):
        x = float(pressed[self.right]) - float(pressed[self.left])
        y = float(pressed[self.down]) - float(pressed[self.up])
        direction = pygame.Vector2(x, y)
        if direction.length_squared() > 1.0:
            direction.normalize_ip()
        return direction


P1_CONTROLLER = HumanController(pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d)
P2_CONTROLLER = HumanController(
    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT
)
