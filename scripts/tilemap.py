import pygame

# 5x5 Area centered at (0,0)
NEIGHBOR_TILES = [(-2,-2), (-2,-1), (-2,0), (-2,1), (-2,2),
    (-1, -2), (-1,-1), (-1,0), (-1,1), (-1,2), 
    (0,-2), (0,-1), (0,0), (0,1), (0,2), 
    (1,-2), (1,-1), (1,0), (1,1), (1,2),
    (2,-2), (2,-1), (2,0), (2,1), (2,2)]

# Tiles that interact with physics and collision
PHYSICS_TILES = {'grass', 'stone'}

class Tilemap:

    def __init__(self, game, tile_size=16):
        self.game = game
        self.tile_size = tile_size
        self.tilemap = {}
        self.offgrid_tiles = []

        for i in range(20):
            self.tilemap[str(3 + i) + ';10'] = {'type': 'grass', 'variant': 1, 'pos': (3 + i, 10)}
            self.tilemap['10;' + str(5 + i)] = {'type': 'stone', 'variant': 1, 'pos': (10, 5 + i)}

    def tiles_nearby(self, pos):
        """
        Helper method for collision detections
        Returns a list of nearby tiles to pos in a 5x5 area
        """
        output_tiles = []

        # Adjust position to center of entity
        #entity_pos = self.game.player.entity_rect().center

        # Convert pixel position to grid position with integer division
        tile_loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size))

        # Access and return each tile around player in a 5x5 area
        for offset in NEIGHBOR_TILES:
            current_tile = str(tile_loc[0] + offset[0]) + ';' + str(tile_loc[1] + offset[1])
            if current_tile in self.tilemap:
                output_tiles.append(self.tilemap[current_tile])

        return output_tiles
    
    def physics_rects_nearby(self, pos):
        """
        Determines if tiles given from tiles_nearby should act as collision
        Returns a Rect list of nearby tiles to pos
        """
        output_rects = []
        for tile in self.tiles_nearby(pos):
            if tile['type'] in PHYSICS_TILES:
                output_rects.append(pygame.Rect(tile['pos'][0] * self.tile_size, tile['pos'][1] * self.tile_size, self.tile_size, self.tile_size))
        return output_rects

    def render(self, surf, offset=(0,0)):
        """
        Renders all tiles onscreen onto display with a camera offset
        Background tiles are rendered before foreground ones
        """
        # Render background objects first
        for tile in self.offgrid_tiles:
            surf.blit(self.game.assets[tile['type']][tile['variant']], (tile['pos'][0] - offset[0], tile['pos'][1] - offset[1]))

        # Render tiles only if in range of camera (camera offset + screen dimension)
        for x in range(offset[0] // self.tile_size, (offset[0] + surf.get_width()) // self.tile_size + 1):
            for y in range(offset[1] // self.tile_size, (offset[1] + surf.get_height()) // self.tile_size + 1):
                loc = str(x) + ';' + str(y)
                for loc in self.tilemap:
                    tile = self.tilemap[loc]
                    surf.blit(self.game.assets[tile['type']][tile['variant']], (tile['pos'][0] * self.tile_size - offset[0], tile['pos'][1] * self.tile_size - offset[1]))
        
            