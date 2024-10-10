import pygame
import sys

from utils import load_images
from tilemap import Tilemap

# Constants
SCREEN_SIZE = (1280, 960)
DISPLAY_SIZE = (320, 240)
TICK_RATE = 60
CAMERA_SPEED = 2
PLACING_OPACITY = 200
RENDER_SCALE = 4.0

class Editor:

    def __init__(self):

        pygame.init()
        self.clock = pygame.time.Clock()

        # full size screen used for window
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("PixelKnight - LEVEL EDITOR")

        # 1/2 scale display used for rendering, scale up to screen
        self.display = pygame.Surface(DISPLAY_SIZE)

        # Load assets
        self.assets = {
            'grass' : load_images('tiles/grass'),
            'stone' : load_images('tiles/stone'),
            'decor' : load_images('tiles/decor'),
            'large_decor' : load_images('tiles/large_decor'),
            'spawners' : load_images('tiles/spawners'),
        }

        # World Init
        self.tilemap = Tilemap(self, tile_size=16)
        try:
            self.tilemap.load('maps/map.json')
        except FileNotFoundError:
            pass

        # Camera Init
        self.scroll = [0, 0]
        self.movement = [False, False, False, False]

        # Tile Creation Init
        self.tile_list = list(self.assets)
        self.tile_group = 0
        self.tile_variant = 0
        self.current_tile_group = 0
        self.current_tile_img = 0
        self.ongrid = True

        # Control init
        self.clicking = False
        self.right_clicking = False
        self.shifting = False
    

    # Runs 60 times per second
    def run(self):
        """
        Primary game loop; controls rendering, game initialization
        """
        while True:

            # Event loop
            for event in pygame.event.get():

                # Exit the application
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Mouse button down
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:               # Left click
                        self.clicking = True
                        # Handle offgrid placing ONLY on first frame of mouse down
                        if not self.ongrid:
                            self.tilemap.offgrid_tiles.append({'type' : self.tile_list[self.tile_group], 'variant' : self.tile_variant, 'pos' : (mpos[0] + self.scroll[0], mpos[1] + self.scroll[1])})
                    if event.button == 3:               # Right click
                        self.right_clicking = True
                    if self.shifting:
                        if event.button == 4:               # SHFIT + Scroll up
                            self.tile_group = (self.tile_group - 1) % len(self.tile_list)
                            self.tile_variant = 0
                        if event.button == 5:               # SHIFT + Scroll down
                            self.tile_group = (self.tile_group + 1) % len(self.tile_list)
                            self.tile_variant = 0
                    else:
                        if event.button == 4:               # Scroll up
                            self.tile_variant = (self.tile_variant - 1) % len(self.current_tile_group)
                        if event.button == 5:               # Scroll down
                            self.tile_variant = (self.tile_variant + 1) % len(self.current_tile_group)
                
                # Mouse button up
                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:            
                        self.clicking = False
                    if event.button == 3:             
                        self.right_clicking = False
                
                # Keystroke down
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:         # A is left
                        self.movement[0] = True
                    if event.key == pygame.K_d:         # D is right
                        self.movement[1] = True
                    if event.key == pygame.K_w:         # W is up
                        self.movement[2] = True
                    if event.key == pygame.K_s:         # S is down
                        self.movement[3] = True
                    if event.key == pygame.K_g:         # G is toggle ongrid
                        self.ongrid = not self.ongrid
                    if event.key == pygame.K_t:         # T is autotile
                        self.tilemap.autotile()
                    if event.key == pygame.K_RETURN:    # RETURN is save file
                        self.tilemap.save('maps/map.json')
                    if event.key == pygame.K_l:         # L is load file
                        try:
                            self.tilemap.load('maps/map.json')
                        except FileNotFoundError:
                            pass
                    if event.key == pygame.K_l:
                        pass
                    if event.key == pygame.K_LSHIFT:    # SHIFT is alternate scroll (category)
                        self.shifting = True

                # Keystroke up
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:      
                        self.movement[0] = False
                    if event.key == pygame.K_d:         
                        self.movement[1] = False
                    if event.key == pygame.K_w:   
                        self.movement[2] = False
                    if event.key == pygame.K_s:     
                        self.movement[3] = False
                    if event.key == pygame.K_LSHIFT:
                        self.shifting = False

            # Draw background
            self.display.fill((10, 50, 80))

            # Camera control
            self.scroll[0] += (self.movement[1] - self.movement[0]) * CAMERA_SPEED
            self.scroll[1] += (self.movement[3] - self.movement[2]) * CAMERA_SPEED
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            # Draw tiles
            self.tilemap.render(self.display, offset=render_scroll)

            # Find placing tile
            self.current_tile_group = self.assets[self.tile_list[self.tile_group]]
            self.current_tile_img = self.current_tile_group[self.tile_variant].copy()
            self.current_tile_img.set_alpha(PLACING_OPACITY)

            # Find mouse position
            mpos = pygame.mouse.get_pos()
            mpos = (mpos[0] / RENDER_SCALE, mpos[1] / RENDER_SCALE)
            tile_pos = (int((mpos[0] + self.scroll[0]) // self.tilemap.tile_size), int((mpos[1] + self.scroll[1]) // self.tilemap.tile_size))

            # Render placing tile, offgrid if G is pressed
            if not self.clicking and not self.right_clicking:
                if self.ongrid:
                    self.display.blit(self.current_tile_img, (tile_pos[0] * self.tilemap.tile_size - self.scroll[0], tile_pos[1] * self.tilemap.tile_size - self.scroll[1]))
                else:
                    self.display.blit(self.current_tile_img, mpos)

            # Place and remove tile at mouse pos
            if self.clicking and self.ongrid:
                self.tilemap.tilemap[str(tile_pos[0]) + ';' + str(tile_pos[1])] = {'type' : self.tile_list[self.tile_group], 'variant' : self.tile_variant, 'pos' : tile_pos}
            if self.right_clicking:
                tile_loc = str(tile_pos[0]) + ';' + str(tile_pos[1])
                if tile_loc in self.tilemap.tilemap:
                    del self.tilemap.tilemap[tile_loc]
            # Offgrid, check every offgrid tile to see if colliding with mouse
                for tile in self.tilemap.offgrid_tiles.copy():
                    tile_img = self.assets[tile['type']][tile['variant']]
                    tile_rect = pygame.Rect(tile['pos'][0] - self.scroll[0], tile['pos'][1] - self.scroll[1], tile_img.get_width(), tile_img.get_height())
                    if tile_rect.collidepoint(mpos):
                        self.tilemap.offgrid_tiles.remove(tile)


            # Render display onto screen (upscaling)
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()))

            # End frame
            pygame.display.update()
            self.clock.tick(TICK_RATE)


Editor().run()