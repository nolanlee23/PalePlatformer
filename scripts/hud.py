from typing import Any
import pygame


class HudElement:
    """
    Simple hud class to directly display onto main screen
    Stores information about how long the hud stays on screen and its location
    """

    def __init__(self, game, image, pos, fixed=False, onscreen_tick=300, fadein_tick=30, fadeout_tick=60, opacity=0, scale=2.0,):
        
        self.game = game
        self.image = pygame.transform.scale(image, (int(image.get_width() * scale), int(image.get_height() * scale)))
        self.pos = pos
        self.onscreen_tick = onscreen_tick
        self.fadein_tick = fadein_tick
        self.fadeout_tick = fadeout_tick
        self.opacity = opacity
        self.fixed = fixed
        self.alive_tick = 0

    def update(self):

        self.alive_tick += 1

        # Fade in
        if self.alive_tick < self.fadein_tick and not self.fixed:
            self.opacity = min(254, self.opacity + 255 // self.fadein_tick)

        # Fade out
        if self.alive_tick > self.onscreen_tick and not self.fixed:
            self.opacity = max(0, self.opacity - 255 // self.fadeout_tick)

        # Delete once faded out
        if self.alive_tick > self.onscreen_tick + self.fadeout_tick and not self.fixed or self.opacity == 0:
            self.game.hud.remove(self)
        

    def render(self, surf):

        hud_img = self.image.copy()
        
        # Blit img into surface for transparency
        hud_surf = pygame.Surface(hud_img.get_size(), pygame.SRCALPHA)
        hud_surf.blit(hud_img, (0, 0))
        hud_surf.set_alpha(self.opacity)

        surf.blit(hud_surf, self.pos)