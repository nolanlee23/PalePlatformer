import pygame
import json

# 5x5 Area centered at (0,0)
NEIGHBOR_TILES = [(-2,-2), (-2,-1), (-2,0), (-2,1), (-2,2),
                (-1, -2), (-1,-1), (-1,0), (-1,1), (-1,2), 
                (0,-2), (0,-1), (0,0), (0,1), (0,2), 
                (1,-2), (1,-1), (1,0), (1,1), (1,2),
                (2,-2), (2,-1), (2,0), (2,1), (2,2)]

# Rules for mapping autotiles, locations are neighboring air tiles
AUTOTILE_MAP = {
    tuple(sorted([(1, 0), (0, 1)])) : 0,                    # Right up
    tuple(sorted([(1, 0), (0, 1), (-1, 0)])) : 1,           # Right left up
    tuple(sorted([(-1, 0), (0, 1)])) : 2,                   # Left up
    tuple(sorted([(-1, 0), (0, -1), (0, 1)])) : 3,          # Left down up
    tuple(sorted([(-1, 0), (0, -1)])) : 4,                  # Left down
    tuple(sorted([(-1, 0), (0, -1), (1, 0)])) : 5,          # Left down right
    tuple(sorted([(1, 0), (0, -1)])) : 6,                   # Right down
    tuple(sorted([(1, 0), (0, -1), (0, 1)])) : 7,           # Right down up
    tuple(sorted([(1, 0), (-1, 0), (0, 1), (0, -1)])) : 8,  # Right left up down
}

# Tiles that will autotile
AUTOTILE_TILES = {'grass', 'stone'}
# Tiles that interact with physics and collision
PHYSICS_TILES = {'grass', 'stone', 'spikes'}

class Tilemap:

    def __init__(self, game, tile_size=16):
        self.game = game
        self.tile_size = tile_size
        self.tilemap = {}
        self.offgrid_tiles = []

    def save(self, path):
        """
        Write tilemap info to maps.JSON
        """
        fil = open(path, 'w')
        json.dump({'tilemap': self.tilemap, 'tile_size': self.tile_size, 'offgrid': self.offgrid_tiles}, fil)
        fil.close()

    def load(self, path):
        """
        Read tilemap info from maps.JSON
        """
        fil = open(path, 'r')
        map_data = json.load(fil)
        fil.close()

        self.tilemap = map_data['tilemap']
        self.tile_size = map_data['tile_size']
        self.offgrid_tiles = map_data['offgrid']

    def extract(self, id_pairs, keep=False):
        """
        Returns a list of all tile and offgrid tiles with the given (type, variant) pair
        Deletes all returned tiles if keep is False
        Allows entity spawning tiles to be placed in the world
        """
        matches = []

        for tile in self.offgrid_tiles.copy():
            if (tile['type'], tile['variant']) in id_pairs:
                matches.append(tile.copy())
                if not keep:
                    self.offgrid_tiles.remove(tile)
        
        for loc in self.tilemap:
            tile = self.tilemap[loc]
            if (tile['type'], tile['variant']) in id_pairs:
                matches.append(tile.copy())
                matches[-1]['pos'] = matches[-1]['pos'].copy()
                matches[-1]['pos'][0] *= self.tile_size
                matches[-1]['pos'][1] *= self.tile_size
                if not keep:
                    del self.tilemap[loc]

        return matches

    def tiles_nearby(self, pos):
        """
        Helper method for collision detections
        Returns a list of nearby tiles to pos in a 5x5 area
        """
        output_tiles = []

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
    
    def tile_below(self, pos):
        """
        Helper method for determining properties of tile below if collisions[down] 
        """

        # Convert pixel position to grid position with integer division
        below_tile_loc = (int(pos[0] // self.tile_size), int(pos[1] // self.tile_size))

        below_tile = str(below_tile_loc[0]) + ';' + str(below_tile_loc[1] + 1)
        if below_tile in self.tilemap:
            return self.tilemap[below_tile]
        return None
    
    def autotile(self):
        """
        Examines neighbors of every tile in map and applies rules of autotiling
        """
        for loc in self.tilemap:
        # Get neighboring tiles of current tile
            tile = self.tilemap[loc]
            neighbors = set()
            for shift in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                check_loc = str(tile['pos'][0] + shift[0]) + ';' + str(tile['pos'][1] + shift[1])
                if check_loc in self.tilemap:
                    if self.tilemap[check_loc]['type'] == tile['type']:
                        neighbors.add(shift)
            neighbors = tuple(sorted(neighbors))
        # Apply autotiling rules based on neighbors
            if tile['type'] in AUTOTILE_TILES and neighbors in AUTOTILE_MAP:
                tile['variant'] = AUTOTILE_MAP[neighbors]

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
                if loc in self.tilemap:
                    tile = self.tilemap[loc]
                    surf.blit(self.game.assets[tile['type']][tile['variant']], (tile['pos'][0] * self.tile_size - offset[0], tile['pos'][1] * self.tile_size - offset[1]))

        
            