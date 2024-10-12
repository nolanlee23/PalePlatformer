import pygame
import sys

from scripts.entities import PhysicsEntity, Collectable, Player
from scripts.utils import load_image, load_images, Animation
from scripts.tilemap import Tilemap
from scripts.particle import Particle
from scripts.hud import HudElement

# Game Constants
SCREEN_SIZE = (1280, 960)
DISPLAY_SIZE = (320, 240)
RENDER_SCALE = 4.0
TICK_RATE = 60
PLAYER_START_POS = (0, 0)
PLAYER_SIZE = (10, 14)
CAMERA_SMOOTH = 10
LOOK_OFFSET = 4.5
LOOK_THRESHOLD = 20
FADE_SPEED = 6

class Game:

    def __init__(self):

        pygame.init()
        pygame.mixer.init()
        self.clock = pygame.time.Clock()

        # full size screen used for window (container)
        self.screen = pygame.display.set_mode(SCREEN_SIZE, flags=pygame.SCALED, vsync=1)
        pygame.display.set_caption("PixelKnight")

        # Scaled display used for all rendering, scale up to screen before final render
        self.display = pygame.Surface(DISPLAY_SIZE)

        # Blackout surface for level transition and death effects
        self.blackout_surf = pygame.Surface(SCREEN_SIZE)
        self.blackout_surf.fill((0, 0, 0))
        self.blackout_alpha = 255
        self.damage_fade_in = False
        self.damage_fade_out = False

        # Load assets
        self.assets = {
            'background' : load_image('backgrounds/green_cave.png'),
            'grub_icon' : load_image('hud/counter/grub_icon.png'),
            'guide_move' : load_image('hud/guide/guide_move.png'),
            'guide_jump' : load_image('hud/guide/guide_jump.png'),
            'guide_look' : load_image('hud/guide/guide_look.png'),
            'guide_dash' : load_image('hud/guide/guide_dash.png'),
            'guide_climb' : load_image('hud/guide/guide_climb.png'),
            'guide_fly' : load_image('hud/guide/guide_fly.png'),
            'grass' : load_images('tiles/grass'),
            'stone' : load_images('tiles/stone'),
            'decor' : load_images('tiles/decor'),
            'large_decor' : load_images('tiles/large_decor'),
            'spawners' : load_images('tiles/spawners'),
            'spikes' : load_images('tiles/spikes'),
            'player/idle' : Animation(load_images('player/idle')),
            'player/look_up' : Animation(load_images('player/look_up'), img_dur=4, loop=False),
            'player/look_down' : Animation(load_images('player/look_down'), img_dur=4, loop=False),
            'player/run' : Animation(load_images('player/run'), img_dur=5),
            'player/jump' : Animation(load_images('player/jump')),
            'player/fall' : Animation(load_images('player/fall')),
            'player/wall_slide' : Animation(load_images('player/wall_slide')),
            'player/dash' : Animation(load_images('player/cloak'), img_dur=3, loop=False),
            'player/hitstun' : Animation(load_images('player/hitstun')),
            'player/kneel' : Animation(load_images('player/kneel')),
            'player/float' : Animation(load_images('player/float')),
            'particle/dash_particle' : Animation(load_images('particles/dash_particle'), img_dur=4, loop=False),
            'particle/circle_particle' : Animation(load_images('particles/circle_particle'), img_dur=5, loop=False),
            'particle/cloak_particle' : Animation(load_images('particles/cloak_particle'), img_dur=4, loop=False),
            'particle/slide_particle' : Animation(load_images('particles/slide_particle'), img_dur=2, loop=False),
            'particle/long_slide_particle' : Animation(load_images('particles/long_slide_particle'), img_dur=10, loop=False),
            'particle/run_particle' : Animation(load_images('particles/run_particle'), img_dur=5, loop=False),
            'particle/wings_particle' : Animation(load_images('particles/wings_particle'), img_dur=3, loop=False),
            'collectables/respawn/idle' : Animation(load_images('collectables/respawn/idle')),
            'collectables/grub/idle' : Animation(load_images('collectables/grub/idle')),
            'collectables/grub/alert' : Animation(load_images('collectables/grub/alert')),
            'collectables/grub/collect' : Animation(load_images('collectables/grub/collect'), img_dur=8, loop=False),
            'collectables/cloak_pickup/idle' : Animation(load_images('collectables/cloak_pickup/idle')),
            'collectables/claw_pickup/idle' : Animation(load_images('collectables/claw_pickup/idle')),
            'collectables/wings_pickup/idle' : Animation(load_images('collectables/wings_pickup/idle')),
            'collectables/saw/idle' : Animation(load_images('collectables/saw/idle'), img_dur=3, loop=True),
        }

        # Load audio
        self.sfx = {
            'run_grass' : pygame.mixer.Sound('sfx/run_grass.wav'),
            'run_stone' : pygame.mixer.Sound('sfx/run_stone.wav'),
            'jump' : pygame.mixer.Sound('sfx/jump.wav'),
            'land' : pygame.mixer.Sound('sfx/land.wav'),
            'falling' : pygame.mixer.Sound('sfx/falling.wav'),
            'wings' : pygame.mixer.Sound('sfx/wings.wav'),
            'dash' : pygame.mixer.Sound('sfx/dash.wav'),
            'cloak' : pygame.mixer.Sound('sfx/cloak.wav'),
            'hitstun' : pygame.mixer.Sound('sfx/damage.wav'),
            'wall_jump' : pygame.mixer.Sound('sfx/wall_jump.wav'),
            'wall_slide' : pygame.mixer.Sound('sfx/wall_slide.wav'),
            'mantis_claw' : pygame.mixer.Sound('sfx/mantis_claw.wav'),
            'grub_free_1' : pygame.mixer.Sound('sfx/grub_free_1.wav'),
            'grub_free_2' : pygame.mixer.Sound('sfx/grub_free_2.wav'),
            'grub_free_3' : pygame.mixer.Sound('sfx/grub_free_3.wav'),
            'grub_break' : pygame.mixer.Sound('sfx/grub_break.wav'),
            'grub_burrow' : pygame.mixer.Sound('sfx/grub_burrow.wav'),
            'grub_alert' : pygame.mixer.Sound('sfx/grub_alert.wav'),
            'grub_sad_idle_1' : pygame.mixer.Sound('sfx/grub_sad_idle_1.wav'),
            'grub_sad_idle_2' : pygame.mixer.Sound('sfx/grub_sad_idle_2.wav'),
            'ability_pickup' : pygame.mixer.Sound('sfx/ability_pickup_boom.wav'),
            'ability_info' : pygame.mixer.Sound('sfx/ability_info.wav'),
            'shiny_item' : pygame.mixer.Sound('sfx/shiny_item.wav'),
            'saw_loop' : pygame.mixer.Sound('sfx/saw_loop.wav'),
        }

        # Initialize audio volume
        self.sfx['run_grass'].set_volume(0.2)
        self.sfx['run_stone'].set_volume(0.2)
        self.sfx['jump'].set_volume(0.15)
        self.sfx['land'].set_volume(0.08)
        self.sfx['falling'].set_volume(0.2)
        self.sfx['wings'].set_volume(0.2)
        self.sfx['dash'].set_volume(0.14)
        self.sfx['cloak'].set_volume(0.1)
        self.sfx['hitstun'].set_volume(0.2)
        self.sfx['wall_jump'].set_volume(0.15 )
        self.sfx['wall_slide'].set_volume(0.25)
        self.sfx['mantis_claw'].set_volume(0.15)
        self.sfx['grub_free_1'].set_volume(0.2)
        self.sfx['grub_free_2'].set_volume(0.2)
        self.sfx['grub_free_3'].set_volume(0.3)
        self.sfx['grub_break'].set_volume(0.15)
        self.sfx['grub_burrow'].set_volume(0.35)
        self.sfx['grub_alert'].set_volume(0.3)
        self.sfx['grub_sad_idle_1'].set_volume(0.2)
        self.sfx['grub_sad_idle_2'].set_volume(0.2)
        self.sfx['ability_pickup'].set_volume(0.3)
        self.sfx['ability_info'].set_volume(0.05)
        self.sfx['shiny_item'].set_volume(0.0)
        self.sfx['saw_loop'].set_volume(0.0)

        

        # Player Init
        self.player_spawn_pos = PLAYER_START_POS
        self.player = Player(self, PLAYER_START_POS, PLAYER_SIZE)
        self.player_movement = [False, False]
        
        # World Init
        self.tilemap = Tilemap(self, tile_size=16)
        self.level_select = '0'
        self.load_map(self.level_select)

        


    def load_map(self, map_id):
        """
        Load the specified map and initialize game state
        """
        self.tilemap.load('maps/' + str(map_id) + '.json')

        # Particle Init
        self.particles = []

        # Entity Init
        self.collectables = []
        self.grubs_collected = 0
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1), ('spawners', 2), ('spawners', 3), ('spawners', 4), ('spawners', 5), ('spawners', 6), ('spawners', 7)]):
            if spawner['variant'] == 0:
                self.collectables.append(Collectable(self, spawner['pos'], 'respawn'))
            if spawner['variant'] == 1:
                self.collectables.append(Collectable(self, spawner['pos'], 'grub'))
            if spawner['variant'] == 2:
                self.player.pos = spawner['pos']
                self.player_spawn_pos = spawner['pos'].copy()
            if spawner['variant'] == 3:
                self.collectables.append(Collectable(self, spawner['pos'], 'cloak_pickup'))
            if spawner['variant'] == 4:
                self.collectables.append(Collectable(self, spawner['pos'], 'claw_pickup'))
            if spawner['variant'] == 5:
                self.collectables.append(Collectable(self, spawner['pos'], 'wings_pickup'))
            if spawner['variant'] == 6:
                self.collectables.append(Collectable(self, spawner['pos'], 'saw'))

        # Hud Init
        self.hud = []
        self.hud.append(HudElement(self, self.assets['guide_move'] ,(4, 4)))
        self.hud.append(HudElement(self, self.assets['guide_jump'] ,(32, 4)))
        self.hud.append(HudElement(self, self.assets['grub_icon'] ,(DISPLAY_SIZE[0] - 24, 2), fixed=True, opacity=180))
        self.score_text = pygame.font.Font('freesansbold.ttf', 30)
        self.score_text_back = pygame.font.Font('freesansbold.ttf', 31)

        # Camera Init
        self.scroll = [0, 0]
        self.playing_timer = 0
        

   
    def run(self):
        """
        Primary game loop; controls rendering, game initialization, and player input
        """
        # Start looping music playback
        pygame.mixer.music.load('sfx/music_crossroads.wav')
        pygame.mixer.music.set_volume(0.05)
        pygame.mixer.music.play(-1)

         # Runs 60 times per second
        while True:

            # Input event loop
            for event in pygame.event.get():

                # Exit the application
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Keystroke down
                if event.type == pygame.KEYDOWN and self.player.can_move:
                    if event.key == pygame.K_a:         # A is left
                        self.player_movement[0] = True
                        self.player.holding_left = True
                    if event.key == pygame.K_d:         # D is right
                        self.player_movement[1] = True
                        self.player.holding_right = True
                    if event.key == pygame.K_w:         # W is up
                        self.player.holding_up = True
                    if event.key == pygame.K_s:         # S is down
                        self.player.holding_down = True
                    if event.key == pygame.K_SPACE:     # SPACE is jump
                        self.player.jump()
                    if event.key == pygame.K_LSHIFT:    # SHIFT is dash
                        self.player.dash()
                    if event.key == pygame.K_v:         # V is dev unlock
                        self.player.has_cloak = True
                        self.player.has_claw = True
                        self.player.has_wings = True

                # Keystroke up
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.player_movement[0] = False
                        self.player.holding_left = False
                    if event.key == pygame.K_d:
                        self.player_movement[1] = False
                        self.player.holding_right = False
                    if event.key == pygame.K_w:         
                        self.player.holding_up = False
                    if event.key == pygame.K_s:         
                        self.player.holding_down = False
                    if event.key == pygame.K_SPACE:
                        self.player.jump_release()      # Jump release for variable jump height

            # Fix movement not being updated 
            if not self.player_movement[0] and self.player.holding_left:
                self.player_movement[0] = True
            if not self.player_movement[1] and self.player.holding_right:
                self.player_movement[1] = True



            # Adjust camera scroll and increase camera smoothness based on if player is looking vertically
            self.camera_smooth = CAMERA_SMOOTH
            if self.player.looking_up and self.player.idle_timer > LOOK_THRESHOLD:
                self.scroll = [self.scroll[0], self.scroll[1] - LOOK_OFFSET]
                self.camera_smooth = CAMERA_SMOOTH * 1.75
            if self.player.looking_down and self.player.idle_timer > LOOK_THRESHOLD:
                self.scroll = [self.scroll[0], self.scroll[1] + LOOK_OFFSET]
                self.camera_smooth = CAMERA_SMOOTH * 1.75


            # Freeze player when fading in or out from death warp
            if self.damage_fade_out:

                # First frame of fade out
                if self.blackout_alpha > 0 and self.blackout_alpha <= FADE_SPEED :
                    self.player.hitstun_animation()

                # Fading out
                if self.blackout_alpha < 255:
                    self.blackout_alpha = min(255, self.blackout_alpha + FADE_SPEED)
                    self.player_movement = [False, False]

                else:
                # Black screen
                    self.camera_smooth = 1
                    self.player.death_warp()
                    self.damage_fade_out = False
                    self.damage_fade_in = True

            if self.damage_fade_in:

                # First frame of fade in
                if self.blackout_alpha == 255:
                    self.player.intangibility_timer = 60

                # Last few frames of fade in
                if self.blackout_alpha < 70:
                    self.player.set_action('idle') 

                if self.blackout_alpha > 0:

                # Fading in
                    self.blackout_alpha = max(0, self.blackout_alpha - FADE_SPEED * 1.5)
                    self.player.velocity = [0, 0]
                else:

                # Full opacity
                    self.camera_smooth = CAMERA_SMOOTH
                    self.player.can_move = True
                    self.player.air_time = 0
                    self.player.set_action('idle')
                    self.damage_fade_in = False

            # Fade into first scene
            if self.playing_timer < 10:
                self.can_move = False
                self.camera_smooth = 1
            if self.playing_timer < 25:
                self.blackout_alpha -= 10
                self.player.can_move = True
            
            
            # Draw background
            self.display.blit(self.assets['background'], (0,0))

            # Control Camera
            self.scroll[0] += (self.player.entity_rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / self.camera_smooth
            self.scroll[1] += (self.player.entity_rect().centery - self.display.get_height() / 2 - self.scroll[1]) / self.camera_smooth

            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            # Render tilemap
            self.tilemap.render(self.display, offset=render_scroll)

            # Update player movement and animation
            if self.player.can_update and self.player.can_move:
                self.player.update(self.tilemap, (self.player_movement[1] - self.player_movement[0], 0))
            if self.player.can_update and not self.player.can_move:
                self.player.update(self.tilemap, (0, 0))
            
            # Render player
            self.player.render(self.display, offset=render_scroll)

            # Update and render particles
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=(render_scroll))
                if kill:
                    self.particles.remove(particle)
            
            # Update and render collectables
            for collectable in self.collectables.copy():
                collectable.update()
                collectable.render(self.display, offset=render_scroll)

            # Update and render hud elements
            for hud in self.hud.copy():
                hud.update()
                hud.render(self.display)
            if self.playing_timer == 290:
                self.hud.append(HudElement(self, self.assets['guide_look'] ,(4, 4)))


            # Render display onto final screen (upscaling)
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()))

            # Render layered text onto larger screen to accomodate anti aliasing
            score_img_back = self.score_text_back.render(str(self.grubs_collected) + '/' + str(Collectable.total_grubs), False, (0, 80, 40))
            score_img = self.score_text.render(str(self.grubs_collected) + '/' + str(Collectable.total_grubs), False, (10, 120, 80))
            self.screen.blit(score_img_back, (SCREEN_SIZE[0] - score_img.get_width() - 9.5, 12))
            self.screen.blit(score_img, (SCREEN_SIZE[0] - score_img.get_width() - 8, 13))


            # Render and update blackout surface onto final screen
            self.blackout_surf.set_alpha(self.blackout_alpha)
            self.screen.blit(self.blackout_surf)


            # End frame
            pygame.display.update()
            self.playing_timer += 1
            self.clock.tick(TICK_RATE)


Game().run()