import pygame
import sys

from scripts.entities import PhysicsEntity, Collectable, Player
from scripts.utils import load_image, load_images, Animation
from scripts.tilemap import Tilemap
from scripts.particle import Particle

# Game Constants
SCREEN_SIZE = (1280, 960)
DISPLAY_SIZE = (320, 240)
RENDER_SCALE = 4.0
TICK_RATE = 60
PLAYER_START_POS = (0, 0)
PLAYER_SIZE = (10, 14)
CAMERA_SMOOTH = 10
LOOK_OFFSET = 4.5
LOOK_THRESHOLD = 30
FADE_SPEED = 8

class Game:

    def __init__(self):

        pygame.init()
        self.clock = pygame.time.Clock()

        # full size screen used for window (container)
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("PixelKnight")

        # Scaled display used for all rendering, scale up to screen before final render
        self.display = pygame.Surface(DISPLAY_SIZE)

        # Blackout surface for level transition and death effects
        self.blackout_surf = pygame.Surface(DISPLAY_SIZE)
        self.blackout_surf.fill((0, 0, 0))
        self.blackout_alpha = 0
        self.fade_in = False
        self.fade_out = False

        # Load assets
        self.assets = {
            'background' : load_image('backgrounds/green_cave.png'),
            'grass' : load_images('tiles/grass'),
            'stone' : load_images('tiles/stone'),
            'decor' : load_images('tiles/decor'),
            'large_decor' : load_images('tiles/large_decor'),
            'spawners' : load_images('tiles/spawners'),
            'player/idle' : Animation(load_images('player/idle')),
            'player/look_up' : Animation(load_images('player/look_up'), img_dur=4, loop=False),
            'player/look_down' : Animation(load_images('player/look_down'), img_dur=4, loop=False),
            'player/run' : Animation(load_images('player/run'), img_dur=5),
            'player/jump' : Animation(load_images('player/jump')),
            'player/fall' : Animation(load_images('player/fall')),
            'player/wall_slide' : Animation(load_images('player/wall_slide')),
            'player/dash' : Animation(load_images('player/cloak'), img_dur=3, loop=False),
            'player/hitstun' : Animation(load_images('player/hitstun')),
            'particle/dash_particle' : Animation(load_images('particles/cloak_particle'), img_dur=3, loop=False),
            'particle/slide_particle' : Animation(load_images('particles/slide_particle'), img_dur=2, loop=False),
            'particle/run_particle' : Animation(load_images('particles/run_particle'), img_dur=5, loop=False),
            'particle/wings_particle' : Animation(load_images('particles/wings_particle'), img_dur=3, loop=False),
            'collectables/grub/idle' : Animation(load_images('collectables/grub/idle')),
            'collectables/grub/collect' : Animation(load_images('collectables/grub/collect'), img_dur=8, loop=False),
        }

        # Player Init
        self.player_spawn_pos = PLAYER_START_POS
        self.player = Player(self, PLAYER_START_POS, PLAYER_SIZE)
        self.player_movement = [False, False]
        
        # World Init
        self.tilemap = Tilemap(self, tile_size=16)
        self.load_map('0')


    def load_map(self, map_id):
        """
        Load the specified map and initialize game state
        """
        self.tilemap.load('maps/' + str(map_id) + '.json')

        # Particle Init
        self.particles = []

        # Entity Init
        self.collectables = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player_spawn_pos = spawner['pos'].copy()
            if spawner['variant'] == 1:
                self.collectables.append(Collectable(self, spawner['pos'], 'grub'))

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
                    if event.key == pygame.K_w:         # W is up
                        self.player.holding_up = True
                    if event.key == pygame.K_s:         # S is down
                        self.player.holding_down = True
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
                    if event.key == pygame.K_w:         
                        self.player.holding_up = False
                    if event.key == pygame.K_s:         
                        self.player.holding_down = False
                    if event.key == pygame.K_SPACE:
                        self.player.jump_release()      # Jump release for variable jump height

            # Draw background
            self.display.blit(self.assets['background'], (0,0))

            # Adjust camera scroll and increase camera smoothness based on if player is looking vertically
            self.camera_smooth = CAMERA_SMOOTH
            if self.player.looking_up and self.player.idle_timer > LOOK_THRESHOLD:
                self.scroll = [self.scroll[0], self.scroll[1] - LOOK_OFFSET]
                self.camera_smooth = CAMERA_SMOOTH * 1.75
            if self.player.looking_down and self.player.idle_timer > LOOK_THRESHOLD:
                self.scroll = [self.scroll[0], self.scroll[1] + LOOK_OFFSET]
                self.camera_smooth = CAMERA_SMOOTH * 1.75

            # Control Camera
            self.scroll[0] += (self.player.entity_rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / self.camera_smooth
            self.scroll[1] += (self.player.entity_rect().centery - self.display.get_height() / 2 - self.scroll[1]) / self.camera_smooth
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            # Render tilemap
            self.tilemap.render(self.display, offset=render_scroll)

            # Update collectables
            for collectable in self.collectables.copy():
                collectable.update()
                collectable.render(self.display, offset=render_scroll)

            # Update player movement and animation
            if self.player.can_move:
                self.player.update(self.tilemap, (self.player_movement[1] - self.player_movement[0], 0))
            
            # Render player
            self.player.render(self.display, offset=render_scroll)

            # Update and render particles
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=(render_scroll))
                if kill:
                    self.particles.remove(particle)
            
            # Freeze player when fading in or out from death warp
            if self.fade_out:
                # First few frames
                if self.blackout_alpha > 0 and self.blackout_alpha < FADE_SPEED * 3:
                    self.player.hitstun_animation()
                # Fading out
                if self.blackout_alpha < 255:
                    self.blackout_alpha = min(255, self.blackout_alpha + FADE_SPEED)
                else:
                # Black screen
                    self.player.death_warp()
                    self.fade_out = False
                    self.fade_in = True
            if self.fade_in:
                # First frame
                if self.blackout_alpha == 255:
                    self.player.intangibility_timer = 60
                if self.blackout_alpha > 0:
                # Fading in
                    self.blackout_alpha = max(0, self.blackout_alpha - FADE_SPEED)
                else:
                # Full opacity
                    self.player.can_move = True
                    self.player.set_action('idle')
                    self.fade_in = False
                

            # Render and update blackout surface
            self.blackout_surf.set_alpha(self.blackout_alpha)
            self.display.blit(self.blackout_surf)

            # Render display onto screen (upscaling)
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()))

            # End frame
            pygame.display.update()
            self.clock.tick(TICK_RATE)


Game().run()