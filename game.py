import pygame
import sys

from scripts.entities import PhysicsEntity, Player
from scripts.utils import load_image, load_images, Animation
from scripts.tilemap import Tilemap

# Constants
SCREEN_SIZE = (1280, 960)
DISPLAY_SIZE = (320, 240)
TICK_RATE = 60
PLAYER_START_POS = (150, 50)
PLAYER_SIZE = (10, 15)
CAMERA_SMOOTH = 11

class Game:

    def __init__(self):

        pygame.init()
        self.clock = pygame.time.Clock()

        # full size screen used for window
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("PixelKnight")

        # 1/2 scale display used for rendering, scale up to screen
        self.display = pygame.Surface(DISPLAY_SIZE)

        # Load assets
        self.assets = {
            'background' : load_image('backgrounds/green_cave.png'),
            'grass' : load_images('tiles/grass'),
            'stone' : load_images('tiles/stone'),
            'decor' : load_images('tiles/decor'),
            'large_decor' : load_images('tiles/large_decor'),
            'player/idle' : Animation(load_images('player/idle')),
            'player/run' : Animation(load_images('player/run'), img_dur=5),
            'player/jump' : Animation(load_images('player/jump')),
            'player/fall' : Animation(load_images('player/fall')),
            'player/wall_slide' : Animation(load_images('player/wall_slide')),
            'player/dash' : Animation(load_images('player/dash'), img_dur=3, loop=False)
        }

        # Player Init
        self.player = Player(self, PLAYER_START_POS, PLAYER_SIZE)
        self.player_movement = [False, False]

        # World Init
        self.tilemap = Tilemap(self, tile_size=16)
        self.tilemap.load('maps/map.json')

        # Camera Init
        self.scroll = [0, 0]
        
    

    # Runs 60 times per second
    def run(self):
        """
        Primary game loop; controls rendering, game initialization, and player input
        """
        while True:

            # Event loop
            for event in pygame.event.get():

                # Exit the application
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Keystroke down
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:         # A is left
                        self.player_movement[0] = True
                    if event.key == pygame.K_d:         # D is right
                        self.player_movement[1] = True
                    if event.key == pygame.K_SPACE:     # SPACE is jump
                        self.player.jump()
                    if event.key == pygame.K_LSHIFT:     # SHIFT is dash
                        self.player.dash()

                # Keystroke up
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.player_movement[0] = False
                    if event.key == pygame.K_d:
                        self.player_movement[1] = False
                    if event.key == pygame.K_SPACE:
                        self.player.jump_release()      # Jump release for variable jump height

            # Draw background
            self.display.blit(self.assets['background'], (0,0))

            # Control Camera
            self.scroll[0] += (self.player.entity_rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / CAMERA_SMOOTH
            self.scroll[1] += (self.player.entity_rect().centery - self.display.get_height() / 2 - self.scroll[1]) / CAMERA_SMOOTH * 3
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            # Draw tiles
            self.tilemap.render(self.display, offset=render_scroll)

            # Update player X movement
            self.player.update(self.tilemap, (self.player_movement[1] - self.player_movement[0], 0))

            # Render player
            self.player.render(self.display, offset=self.scroll)

            # Render display onto screen (upscaling)
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()))

            # End frame
            pygame.display.update()
            self.clock.tick(TICK_RATE)


Game().run()