import pygame

FOLLOW_OFFSET = (5, 5)

class Particle:
    
    def __init__(self, game, p_type, pos, velocity=[0,0], frame=0, flip=False, follow_player=False):
        self.game = game
        self.type = p_type
        self.pos = list(pos)
        self.velocity = list(velocity)
        self.animation = self.game.assets['particle/' + p_type].copy()
        self.animation.frame = frame
        self.flip = flip
        self.follow = follow_player

    def update(self):
        """
        Return True and delete particle if animation completes
        """
        kill = False
        if self.animation.done:
            kill = True

        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]

        self.animation.update()

        return kill
    
    def render(self, surf, offset=(0,0)):
        """
        Render with offset and centered around particle img center
        """
        img = self.animation.img()
        if not self.follow:
            surf.blit(img, (self.pos[0] - offset[0] - img.get_width() // 2, self.pos[1] - offset[1] - img.get_height() // 2))
        else:
            surf.blit(pygame.transform.flip(img, self.flip, False), (self.game.player.pos[0] - offset[0] - img.get_width() // 2 + FOLLOW_OFFSET[0] , self.game.player.pos[1] - offset[1] - img.get_height() // 2 + FOLLOW_OFFSET[1] ))