import pygame
import math
import random

from .particle import Particle
from .hud import HudElement

# Universal physics constants
TERMINAL_VELOCITY = 5.0
GRAVITY_CONST = 0.2
TICK_RATE = 60
RENDER_SCALE = 4.0
DEPTHS_Y = 400
DEPTHS_X = -300


# Collectable constants
COLLECTABLE_SIZES = {
    'respawn' : (16, 16),
    'grub' : (30, 30),
    'cloak_pickup' : (16, 16),
    'claw_pickup' : (18, 18),
    'wings_pickup' : (22, 14),
    'saw' : (30, 30),
    'gate' : (8, 32),
    'lever' : (16, 14),
    'dash_pickup' : (16, 16),
    'shade_gate' : (16, 32),
    'slippery_rock' : (8, 32),
}
COLLECTABLE_OFFSETS = {
    'respawn' : (0, 1),
    'grub' : (0, 11),
    'saw' : (0, 0),
    'gate' : (0, 0),
    'lever' : (0, 0),
    'dash_pickup' : (0, 0),
    'claw_pickup' : (0, 0),
    'wings_pickup' : (0, 0),
    'cloak_pickup' : (0, 0),
    'shade_gate' : (0, 0),
    'slippery_rock' : (0, 0),
}
GRUB_NOISE_DIST = 200
ALERT_NOISE_DIST = 45
ALERT_COOLDOWN = 3
SHINY_NOISE_DIST = 150
SAW_NOISE_DIST = 80

# Player physics constants
MOVEMENT_X_SCALE = 1.8
JUMP_Y_VEL = -5.05
NUM_AIR_JUMPS = 1
AIR_JUMP_Y_VEL = -4.6
NUM_AIR_DASHES = 1
VARIABLE_JUMP_SHEAR = 12.0
AIRTIME_BUFFER = 4
LOW_GRAV_THRESHOLD = 0.6
LOW_GRAV_DIVISOR = 1.3
DASH_X_SCALE = 4
DASH_TICK = 14
DASH_COOLDOWN_TICK = 26
WALL_SLIDE_VEL = 1.35
WALL_JUMP_Y = -4.6
WALL_JUMP_TICK_CUTOFF = 8
WALL_JUMP_TICK_STALL = 2
WALL_JUMP_BUFFER = 10

# Player animation constants
PLAYER_ANIM_OFFSET = (-3, -8)
DASH_ANIM_OFFSET = (-9, -8)
RUN_PARTICLE_DELAY = 10
DASH_PARTICLE_VEL = 2
DASH_TRAIL_VARIANCE = 0.3
NUM_HITSTUN_PARTICLES = 80
HITSTUN_PARTICLE_VEL = 1
SLIDE_SFX_LEN = 150
FALLING_VOLUME = 0.2

class PhysicsEntity:

    def __init__(self, game, e_type, pos, size, scale=1.0):
        # General info and physics
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
        self.scale = scale
        self.velocity = [0,0]
        self.gravity = GRAVITY_CONST
        self.collisions = {'up' : False, 'down' : False, 'right' : False, 'left' : False}
        self.last_movement = [0,0]

        # Animation and framing
        self.action = ''
        self.anim_offset = (0, 0)
        self.flip = False
        self.set_action('idle')
        self.walking_on = 0                     # Material being walked on for sfx purposes

    def entity_rect(self):
        """
        Returns an instatiated rect at entity postition and scale
        """
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])
    
    def set_action(self, action):
        """
        Set animation action every frame
        """
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()


    def update(self, tilemap, movement=(0,0)):
        """
        Handle entity collision and movement every frame
        """
        # Reset collision detection
        self.collisions = {'up' : False, 'down' : False, 'right' : False, 'left' : False}

        # Add velocity onto position
        frame_movement = (movement[0] + self.velocity[0], movement[1] + self.velocity[1])

        # Update X position based on movement
        self.pos[0] += frame_movement[0]

        # If after X position updates, a collision occurs, snap entity to left/right edge of tile
        entity_rect = self.entity_rect()
        for rect in tilemap.physics_rects_nearby(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0:           # Moving right, snap to left edge of tile
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                if frame_movement[0] < 0:           # Moving left, snap to right edge of tile
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x        # Update player position based on player rect

        # Update Y position
        self.pos[1] += frame_movement[1]

        # If after Y position updates, a collision occurs, snap entity to top/bottom edge of tile
        entity_rect = self.entity_rect()
        for rect in tilemap.physics_rects_nearby(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:           # Moving down, snap to top edge of tile
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                if frame_movement[1] < 0:           # Moving up, snap to bottom edge of tile
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y        # Update player position based on player rect

        # Add gravity and cap terminal velocity
        self.velocity[1] = min(TERMINAL_VELOCITY, self.velocity[1] + self.gravity)

        # Reset gravity if on ground or bonking head on ceiling
        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0

        # Flip sprite on turn around
        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True

        # Update animation
        self.last_movement = movement
        self.animation.update()

    
    def render(self, surf, offset=(0,0)):
        """
        Render entity onto surface taking flip and offset into account
        """
        flipped_img = pygame.transform.flip(self.animation.img(), self.flip, False)
        scaled_img = pygame.transform.scale_by(flipped_img, self.scale)
        surf.blit(scaled_img, (self.pos[0] - offset[0] + self.anim_offset[0], self.pos[1] - offset[1] + self.anim_offset[1]))






class Collectable(PhysicsEntity):

    total_grubs = 0
    
    def __init__(self, game, pos, c_type, scale=1.0, x_collisions=False):
        self.game = game
        self.pos = (pos[0] + COLLECTABLE_OFFSETS[c_type][0], pos[1] + COLLECTABLE_OFFSETS[c_type][1])
        self.type = c_type
        self.size = COLLECTABLE_SIZES[c_type]
        self.scale = scale
        self.x_collisions = x_collisions

        super().__init__(game, 'collectables/' + c_type, pos, self.size, self.scale)

        if c_type == 'grub':
            Collectable.total_grubs += 1
        self.collect_timer = 0
        self.idle_noise_timer = 0
        self.alert_noise_timer = TICK_RATE * ALERT_COOLDOWN
        self.shade_noise_timer = 0
        self.alerted = False
        
        self.dist_to_player = 0
        self.x_dist = 0
        self.y_dist = 0
        self.rect = 0
        self.player_rect = 0
        

    def update(self):
        """
        Used to track timers and play time or distance based sound effects
        """

        self.animation.update()
        self.idle_noise_timer += 1
        self.alert_noise_timer += 1
        self.shade_noise_timer += 1

        # Increment collect counter only if collect() has been called
        if self.collect_timer > 0:
            self.collect_timer += 1

        # Update distance to player
        self.rect = self.entity_rect()
        self.player_rect = self.game.player.entity_rect()
        self.x_dist = self.rect.centerx - self.player_rect.centerx
        self.y_dist = self.rect.centery - self.player_rect.centery
        self.dist_to_player = math.sqrt(self.x_dist**2 + self.y_dist**2)

        # Collect when in contact
        if self.rect.colliderect(self.player_rect):
            self.collect()

        # Saw has circular appearance, use distance from center for collision detection
        if self.type == 'collectables/saw' and self.dist_to_player < COLLECTABLE_SIZES['saw'][0] - 10:
            self.game.damage_fade_out = True

        # Update alerted status for grubs
        if self.dist_to_player >= ALERT_NOISE_DIST:
            self.alerted = False

        # Flash circle particle for pickup items
        if self.type[-6:] == 'pickup':

            # Every other second, pulse circle particle
            if self.idle_noise_timer % TICK_RATE * 2 == 0:
                self.game.particles.append(Particle(self.game, 'circle_particle', self.rect.center, scale=2, opacity= 255 / 3, fade_out=1.3))
        
            # Every 5 seconds, play shiny sound
            self.game.sfx['shiny_item'].set_volume((SHINY_NOISE_DIST - self.dist_to_player) / (SHINY_NOISE_DIST * 2))
            if self.idle_noise_timer % TICK_RATE * 5 == 0 and self.dist_to_player < SHINY_NOISE_DIST:
                self.game.sfx['shiny_item'].play()

        # Play saw blade sound effect
        if self.type == 'collectables/saw':
            self.game.sfx['saw_loop'].set_volume(min(0.2, (SAW_NOISE_DIST - self.dist_to_player) / (SAW_NOISE_DIST)))
            if self.idle_noise_timer % 100 == 1 and self.dist_to_player < SAW_NOISE_DIST * 1.2:
                self.game.sfx['saw_loop'].play()

        # Spawn floating void particles and handle collision
        if self.type == 'collectables/shade_gate':

            # Remove collision if player is cloak dashing
            if self.game.player.cloak_timer > 0 and self.game.player.cloak_timer < DASH_TICK:
                self.x_collisions = False
            else:
                self.x_collisions = True
            
            # Spawn waves of particles
            if self.dist_to_player < 250 and random.randint(0, 1) == 1:
                self.game.particles.append(Particle(self.game, 'long_cloak_particle', (self.rect.centerx + random.uniform(-2, 2), self.rect.centery + random.uniform(-8, 8)), velocity=(random.uniform(-0.4,0.4), random.uniform(-0.05,0.05)), fade_out=2, frame=2))


        # Drop nearest gate and play sfx
        if self.type == 'collectables/lever': 

            if self.collect_timer == 1:
                self.game.sfx['lever'].play()
                
            if self.collect_timer == 30:
                self.game.sfx['gate'].play()
                
            # Open nearest gate after delay
            if self.collect_timer == 60:

                # Gather gates into a list
                gate_list = []
                for entity in self.game.collectables:
                    if entity.type == 'collectables/gate':
                        gate_list.append(entity)

                # Compare each in list and finalize closest
                closest_gate = gate_list[0]
                for gate in gate_list:
                    # New gate distance
                    x_dist = self.rect.centerx - gate.rect.centerx
                    y_dist = self.rect.centery - gate.rect.centery
                    dist_to_gate = math.sqrt(x_dist**2 + y_dist**2)

                    closest_x_dist = self.rect.centerx - closest_gate.rect.centerx
                    closest_y_dist = self.rect.centery - closest_gate.rect.centery
                    closest_dist_to_gate = math.sqrt(closest_x_dist**2 + closest_y_dist**2)
                    if dist_to_gate < closest_dist_to_gate:
                        closest_gate = gate
                
                closest_gate.set_action('drop')
                closest_gate.x_collisions = False

        # Play time based grub sound effects
        if self.type == 'collectables/grub':

            # Before Collection (BC)

            if self.collect_timer == 0:

                # Sad grub noises if within distance and after random interval of seconds
                if self.dist_to_player < GRUB_NOISE_DIST and self.dist_to_player > ALERT_NOISE_DIST and self.idle_noise_timer > random.randint(5, 15) * TICK_RATE and self.game.player.pos[1] < DEPTHS_Y:
                    rand = random.randint(1, 2)
                    rand_chance = random.randint(1, 10)

                    if rand_chance == 1:
                        self.idle_noise_timer = 0
                        self.game.sfx['grub_sad_idle_' + str(rand)].set_volume((GRUB_NOISE_DIST - self.dist_to_player) / (GRUB_NOISE_DIST * 2))
                        self.game.sfx['grub_sad_idle_' + str(rand)].play()

                    

                # Update alert status when player is very close
                if self.dist_to_player < ALERT_NOISE_DIST and abs(self.y_dist) < ALERT_NOISE_DIST / 100:

                    # only play alert sound if havent played in ALERT_COOLDOWN seconds
                    if self.alert_noise_timer > TICK_RATE * ALERT_COOLDOWN and not self.alerted:
                        self.alert_noise_timer = 0
                        self.game.sfx['grub_sad_idle_1'].stop()
                        self.game.sfx['grub_sad_idle_2'].stop()
                        self.game.sfx['grub_alert'].play()

                    self.alerted = True

                # Set action based on how long ago grub was alerted
                if self.alert_noise_timer < TICK_RATE * ALERT_COOLDOWN or self.alerted:
                    self.set_action('alert')
                else:
                    self.set_action('idle')

            # After Collection (AC)

            # Glass break and fades out (and stop sad noises)
            if self.collect_timer == 2:
                self.game.grubs_collected += 1
                self.game.sfx['grub_sad_idle_1'].stop()
                self.game.sfx['grub_sad_idle_2'].stop()
                self.game.sfx['grub_break'].play()
                self.game.sfx['grub_break'].fadeout(1200)

                for i in range(30):
                        self.game.particles.append(Particle(self.game, 'slide_particle', self.entity_rect().center, velocity=(random.uniform(-3, 3), random.uniform(-2, 3))))
            

            # Happy grub noises
            if self.collect_timer == 40:
                rand = random.randint(1, 3)
                self.game.sfx['grub_free_' + str(rand)].play()

            # Burrowing away
            if self.collect_timer == 120:
                self.game.sfx['grub_burrow'].play()

        
    def collect(self):
        """
        Called every frame while player collides with collectable
        Used to start animations and collisions
        """
        # Set spawn point on checkpoint
        if self.type == 'collectables/respawn':
            self.game.player_spawn_pos = self.pos.copy()

        # Start save animation
        if self.type == 'collectables/grub':
            self.set_action('collect')

        # Lever pull animation
        if self.type == 'collectables/lever':
            self.set_action('collect')

        if self.type == 'collectables/shade_gate':
            if self.shade_noise_timer > 30 and self.game.player.cloak_timer > 0 and self.game.player.cloak_timer < DASH_TICK:
                self.game.sfx['shade_gate'].play()
                self.shade_noise_timer = 0
            if self.shade_noise_timer > 180 and self.game.player.has_cloak == False:
                self.game.sfx['shade_gate_repel'].play()
                self.shade_noise_timer = 0

        # Collide with player
        if self.x_collisions:
            if self.player_rect.centerx < self.rect.centerx:
                self.game.player.collisions['right'] = True
                self.player_rect.right = self.rect.left
                self.game.player.entity_x_colliding = 0
            else:
                self.game.player.collisions['left'] = True
                self.player_rect.left = self.rect.right
                self.game.player.entity_x_colliding = 1
            self.game.player.pos[0] = self.player_rect.x
            
        # If item is an ability pickup item
        if self.type[-6:] == 'pickup':

            if self.type == 'collectables/dash_pickup':
                self.game.player.has_dash = True
                particle_type = 'long_dash_particle'
                self.game.hud.append(HudElement(self.game, self.game.assets['guide_dash'] ,(8, 10)))
        
            if self.type == 'collectables/claw_pickup':
                self.game.player.has_claw = True
                particle_type ='long_dash_particle'
                self.game.hud.append(HudElement(self.game, self.game.assets['guide_climb'] ,(8, 0)))

            if self.type == 'collectables/wings_pickup':
                self.game.player.has_wings = True
                particle_type = 'long_slide_particle'
                self.game.hud.append(HudElement(self.game, self.game.assets['guide_fly'] ,(8, 0)))

            if self.type == 'collectables/cloak_pickup':
                self.game.player.has_cloak = True
                particle_type = 'long_cloak_particle'
                self.game.hud.append(HudElement(self.game, self.game.assets['guide_cloak'] ,(8, 10)))
                self.game.sfx['dark_spell_get'].play()
                

            # Boom sound effect and particle burst
            self.game.sfx['shiny_item'].stop()
            self.game.sfx['ability_info'].play()
            self.game.sfx['ability_pickup'].play()
            self.game.collectables.remove(self)
            for i in range(NUM_HITSTUN_PARTICLES):
                hitstun_particle_vel = (random.uniform(-2, 2), random.uniform(-2, 2))
                self.game.particles.append(Particle(self.game, particle_type, self.game.player.entity_rect().center, hitstun_particle_vel, frame=0))
            for i in range(NUM_HITSTUN_PARTICLES):
                hitstun_particle_vel = (random.uniform(-2, 2), random.uniform(-2, 2))
                self.game.particles.append(Particle(self.game, particle_type, self.entity_rect().center, hitstun_particle_vel, frame=0))
            
            return

        # Start collect timer only first frame of contact with player
        if self.collect_timer < 1:
            self.collect_timer = 1


        



class Player(PhysicsEntity):
    """
    PhysicsEntity subclass to handle player-specific animation and movement
    """
    def __init__(self, game, pos, size):

        super().__init__(game, 'player', pos, size)

        # Control variables
        self.intangibility_timer = 0
        self.player_rect = 0
        self.entity_x_colliding = -1
        self.entity_collision = False
        self.can_update = True
        self.can_move = True
        self.death_counter = 0

        # Jump and wall jump variables
        self.has_wings = False
        self.has_claw = False
        self.running_time = 0                           # Time spent running    
        self.air_time = -10                             # Time since leaving ground
        self.falling_time = 0                           # Time since started having negative velocity
        self.wall_jump_timer = 0                        # Time since leaving wall from wall jump
        self.sliding_time = 0                           # Time spent wall sliding
        self.wall_slide = False                         
        self.wall_slide_timer = 1                       # Time since last moment sliding on wall
        self.wall_slide_right = False                   # True if wall sliding on right wall, False if left wall
        self.wall_slide_x_pos = 0                       # Tracker to prevent wall jumping (in buffer) while not next to wall
        self.jumps = NUM_AIR_JUMPS
        self.air_jumping = 0
        self.wall_jump_direction = False                # False is left jump (right wall), True is right jump (left wall)


        # Control dash variables
        self.has_dash = False
        self.has_cloak = False
        self.dashes = NUM_AIR_DASHES
        self.dash_timer = 0
        self.cloak_timer = 0
        self.dash_cooldown_timer = 0

        # Camera control for player holding up or down while idle for a time
        self.idle_timer = 0
        self.holding_up = False
        self.looking_up = False
        self.holding_down = False
        self.looking_down = False

        self.holding_left = False
        self.holding_right = False
        

    def update(self, tilemap, movement=(0, 0)):
        """
        Update player movement variables and handle wall jump logic
        Set player animation state based on game state
        """

        #### MOVEMENT ###


        # Override player movement for a short period after wall jump
        if self.wall_jump_timer < WALL_JUMP_TICK_CUTOFF:
            if self.wall_jump_direction == True:        # Left wall
                movement = (MOVEMENT_X_SCALE, movement[1])
            else:                                       # Right wall
                movement = (-MOVEMENT_X_SCALE, movement[1])

        # Stall for a brief period before control is given back after wall jump
        elif self.wall_jump_timer < WALL_JUMP_TICK_CUTOFF + WALL_JUMP_TICK_STALL:
            movement = (0, movement[1])

        # Apply fast dash movement while dashing
        elif abs(self.dash_timer) > 0:
            movement = (math.copysign(1.0, self.dash_timer) * DASH_X_SCALE, movement[1])
        else:
            
        # Apply normal horizontal movement scale 
            movement = (movement[0] * MOVEMENT_X_SCALE, movement[1])


        # Suspend gravity completely while dashing
        if abs(self.dash_timer) > 0:
            self.gravity = 0
            self.velocity[1] = 0
            movement = (movement[0], 0)

        # Minimize gravity at the peak of player jump to add precision
        elif self.air_time > AIRTIME_BUFFER and self.velocity[1] > -LOW_GRAV_THRESHOLD and self.velocity[1] < LOW_GRAV_THRESHOLD:
            self.gravity = GRAVITY_CONST / LOW_GRAV_DIVISOR
        else:
            self.gravity = GRAVITY_CONST
    

        # Update collision and position based on movement
        if self.can_move:
            super().update(tilemap, movement=movement)

        # Check for entity collision from left or right
        self.entity_collision = False
        if self.entity_x_colliding == 0:
            self.collisions['left'] = True
            self.entity_collision = True
        if self.entity_x_colliding == 1:
            self.collisions['right'] = True
            self.entity_collision = True
        self.entity_x_colliding = -1


        # Void out and death warp if player falls below given Y value (and not in depths)
        if self.pos[1] > DEPTHS_Y and self.pos[0] > DEPTHS_X:
            self.game.damage_fade_out = True
        elif self.pos[1] > DEPTHS_Y * 4:
            self.game.damage_fade_out = True

        # Void out and death warp if player collides with spike tiles
        below_tile = self.game.tilemap.tile_below(self.entity_rect().center)
        if below_tile == None:
            below_tile = {'type': 'air', 'variant': 1}
        if below_tile['type'] == 'spikes' and self.collisions['down'] == True:
            self.game.damage_fade_out = True

        # Update control variables
        self.air_time += 1
        self.wall_jump_timer += 1
        self.dash_cooldown_timer += 1
        self.wall_slide_timer += 1
        self.wall_slide = False
        self.anim_offset = PLAYER_ANIM_OFFSET
        if self.air_jumping > 0:
            self.air_jumping += 1
        if self.cloak_timer > 0:
            self.cloak_timer += 1

        # Reset mobility upon touching ground
        if self.collisions['down']:
            self.jumps = NUM_AIR_JUMPS
            self.dashes = NUM_AIR_DASHES
            self.air_jumping = 0
            
            if self.air_time > AIRTIME_BUFFER and self.dash_cooldown_timer > DASH_TICK and not below_tile['type'] == 'spikes':
                # Hard landing
                if self.game.sfx['falling'].get_volume() > FALLING_VOLUME - 0.01:
                    self.game.sfx['land_hard'].play()
                    # Large dust plume
                    for i in range(40):
                        self.game.particles.append(Particle(self.game, 'slide_particle', self.entity_rect().midbottom, velocity=(random.uniform(-2.5, 2.5), random.uniform(0, 0.5))))
                # Normal landing
                else:
                    self.game.sfx['land'].play()
                    # Dust plume
                    for i in range(10):
                        self.game.particles.append(Particle(self.game, 'run_particle', self.entity_rect().midbottom, velocity=(random.uniform(-0.5, 0.5), random.uniform(0.1, 0.3))))
            
            self.game.sfx['falling'].stop()
            self.air_time = 0

        # Reset mobility upon grabbing wall
        if self.sliding_time > 0:
            self.jumps = NUM_AIR_JUMPS
            self.dashes = NUM_AIR_DASHES
            self.air_jumping = 0
            self.game.sfx['falling'].stop()



        # Decrement dash timer towards 0 from both sides
        if self.dash_timer > 0:
            self.dash_timer = max(0, self.dash_timer - 1)
        if self.dash_timer < 0:
            self.dash_timer = min(0, self.dash_timer + 1)
    

        ### ANIMATION HEIRARCHY ###

        # Update animationm variables
        idling = False
        self.looking_down = False
        self.looking_up = False
        

        # If can't move, don't update animation
        if not self.can_move:
            pass
        # WALL SLIDE, reduce Y ďpeed if touching wall
        elif (self.collisions['right'] or self.collisions['left']) and self.air_time > AIRTIME_BUFFER and self.velocity[1] > 0 and self.has_claw and not self.entity_collision and self.dash_cooldown_timer > 1:

            # Only play grabbing wall sound if not touching wall previously
            if self.wall_slide_timer > AIRTIME_BUFFER:
                self.game.sfx['mantis_claw'].play()
            
            # Play looping sliding effect
            if self.sliding_time % SLIDE_SFX_LEN == 1:
                self.game.sfx['wall_slide'].play()
            
            self.wall_slide = True
            self.wall_slide_timer = 0
            self.wall_slide_right = True if self.collisions['right'] else False
            self.sliding_time += 1

            if self.sliding_time == 1:
                self.wall_slide_x_pos = self.pos[0]

            self.dash_timer /= 2
            self.velocity[1] = min(self.velocity[1], WALL_SLIDE_VEL)

            self.set_action('wall_slide') 

            # Wall slide animation facing right, opposite of wall
            player_rect = self.entity_rect()
            if self.wall_slide_right:
                self.flip = False
                slide_particle_pos = player_rect.midright
            else:
                self.flip = True
                slide_particle_pos = player_rect.midleft

            # Wall slide particles
            slide_particle_start_f = random.randint(0, 2)
            slide_particle_vel = (0, random.randint(1, 4) / 2)
            self.game.particles.append(Particle(self.game, 'slide_particle', slide_particle_pos, velocity=slide_particle_vel, frame=slide_particle_start_f))

        # DASH animation 
        elif abs(self.dash_timer) > 0:
            self.set_action(self.dash_type)     
            self.anim_offset = DASH_ANIM_OFFSET
            # Dash particles 
            if not self.collisions['left'] and not self.collisions['right']:
                dash_trail_pos = (self.entity_rect().centerx, self.entity_rect().centery + random.randint(-1, 1) / DASH_TRAIL_VARIANCE)
                self.game.particles.append(Particle(self.game, self.dash_type + '_particle', dash_trail_pos, velocity=(0,0), frame=0))

        # AIRTIME, buffer for small amounts of airtime flashing animation
        elif self.air_time > AIRTIME_BUFFER:
            if self.velocity[1] < 0:
                self.set_action('jump') 
                # Drifting random wing particles while rising
                if self.air_jumping > 0 and self.air_jumping < 16:
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', (self.entity_rect().centerx + random.randint(-10, 10), self.entity_rect().centery), velocity=(random.uniform(-0.1, 0.1), random.uniform(0, 0.2))))
            else:
                self.set_action('fall')  

        # Run if moving and not moving into a wall
        elif movement[0] != 0 and not self.collisions['left'] and not self.collisions['right']:
            self.set_action('run') 
            idling = False
            self.running_time += 1

            # Running particles
            if self.wall_jump_timer % RUN_PARTICLE_DELAY == 0:
                run_particle_start_f = random.randint(0, 1)
                run_particle_vel = (random.randint(-1, 1) / 3, random.randint(-1, 1) / 5)
                self.game.particles.append(Particle(self.game, 'run_particle', self.entity_rect().midbottom, velocity=run_particle_vel, frame=run_particle_start_f))

            # Determine ground material while walking for running sounds
            below_tile = self.game.tilemap.tile_below(self.pos)
            if not below_tile == None and self.running_time % 120 == 5:
                if below_tile['type'] == 'grass':
                    self.game.sfx['run_grass'].play()
                if below_tile['type'] == 'stone':
                    self.game.sfx['run_stone'].play()
        # Looking up 
        elif self.holding_up:
            self.looking_up = True
            idling = True
            self.set_action('look_up')
        # Looking down 
        elif self.holding_down:
            self.looking_down = True
            idling = True
            self.set_action('look_down')    # Looking down
        # Idling
        else:
            idling = True
            self.set_action('idle')         # Idle
            


        # Add delay in camera movement to avoid rapid changes
        if idling:
            self.idle_timer += 1
        else:
            self.idle_timer = 0

        # Cancel wall slide when player x pos goes behind wall
        if self.sliding_time > 1:
                if not self.pos[0] == self.wall_slide_x_pos:
                    if self.wall_slide_right and self.pos[0] > self.wall_slide_x_pos:
                        self.wall_slide = False
                        self.sliding_time = 0
                        self.wall_slide_timer = WALL_JUMP_BUFFER
                    if not self.wall_slide_right and self.pos[0] < self.wall_slide_x_pos:
                        self.wall_slide = False
                        self.sliding_time = 0
                        self.wall_slide_timer = WALL_JUMP_BUFFER


        # Add falling timer for hard landing sound effects
        if self.velocity[1] > 0:
            self.falling_time += 1
        if self.velocity[1] < 0 or self.air_time < AIRTIME_BUFFER or self.sliding_time > 0:
            self.falling_time = 0
        if self.falling_time < TICK_RATE:
            self.game.sfx['falling'].set_volume(0.0)
        if self.falling_time == TICK_RATE:
            self.game.sfx['falling'].play()
        if self.falling_time >= TICK_RATE and self.velocity[1] > 0:
            self.game.sfx['falling'].set_volume(min(FALLING_VOLUME, self.game.sfx['falling'].get_volume() + 0.01))


        # Ensure no lingering sound effects
        if not self.wall_slide and self.has_claw:
            self.game.sfx['wall_slide'].stop()
            self.sliding_time = 0
        if self.air_time > AIRTIME_BUFFER or self.idle_timer > AIRTIME_BUFFER:
            self.game.sfx['run_grass'].stop()
            self.game.sfx['run_stone'].stop()
            self.running_time = 0
            
            

    def jump(self):
        """
        Check if player is eligible to jump, perform jump and wall jump
        Return TRUE if player has sucessfully jumped
        """
        # Wall jump if wall sliding, has claw, and has not wall jumped in ~10 frames
        if self.wall_slide_timer < WALL_JUMP_BUFFER and self.has_claw and self.wall_jump_timer > WALL_JUMP_BUFFER + 4:
            self.game.sfx['wall_jump'].play()
            if not self.wall_slide_right:         # Off of left wall
                self.wall_jump_direction = True
                particle_loc = self.entity_rect().bottomleft
            elif self.wall_slide_right:           # Off of right wall
                self.wall_jump_direction = False
                particle_loc = self.entity_rect().bottomright
            self.wall_jump_timer = 0
            self.velocity[1] = WALL_JUMP_Y
            self.air_time = AIRTIME_BUFFER + 1

            for i in range(5):
                    self.game.particles.append(Particle(self.game, 'run_particle', particle_loc, velocity=(random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.3))))
            return True
        # Normal and double jump if grounded or not
        elif self.jumps and not self.dash_timer:
            if self.air_time > AIRTIME_BUFFER * 2: 
                # Mid Air jump             
                if self.has_wings:
                    self.jumps = min(0, self.jumps - 1)
                    self.velocity[1] = AIR_JUMP_Y_VEL
                    self.air_jumping = 1
                    self.game.sfx['wings'].play()
                    # Midair wing jump particle: 1 for wing animation, 6 bursts in each downward direction
                    self.game.particles.append(Particle(self.game, 'wings_particle', self.entity_rect().center, velocity=(0, 0), flip=self.flip, follow_player=True))
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', self.entity_rect().center, velocity=(-0.1, 0.3)))
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', self.entity_rect().center, velocity=(0.1, 0.3)))
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', self.entity_rect().midleft + (2,0), velocity=(-0.2, 0.2)))
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', self.entity_rect().midright + (-2,0), velocity=(0.2, 0.2)))
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', self.entity_rect().midleft, velocity=(-0.4, 0.1)))
                    self.game.particles.append(Particle(self.game, 'long_slide_particle', self.entity_rect().midright, velocity=(0.4, 0.1)))
            # Grounded jump
            else:                                        
                self.velocity[1] = JUMP_Y_VEL
                self.game.sfx['jump'].play()

                # Dust plume around jump
                for i in range(6):
                    self.game.particles.append(Particle(self.game, 'run_particle', self.entity_rect().midbottom, velocity=(random.uniform(-0.4, 0.4), random.uniform(-0.4, -0.1))))
            
            self.air_time = AIRTIME_BUFFER + 1
            return True
        
        return False

    def jump_release(self):
        """
        Allow variable jump height by reducing velocity on SPACE keystroke up
        """
        if self.velocity[1] < 0:
            if self.wall_jump_timer > WALL_JUMP_TICK_CUTOFF:
                self.velocity[1] /= VARIABLE_JUMP_SHEAR
            else:
                self.velocity[1] /= VARIABLE_JUMP_SHEAR / 4
            self.wall_jump_timer *= 1.5
            self.gravity = GRAVITY_CONST
            self.air_jumping = 0

    def dash(self):
        """
        Dash by starting timer and taking over player movement until timer reaches zero
        Return TRUE if sucessful dash
        """
        if self.has_dash and not self.dash_timer and self.dashes and self.wall_jump_timer > WALL_JUMP_TICK_CUTOFF + WALL_JUMP_TICK_STALL and self.dash_cooldown_timer > DASH_COOLDOWN_TICK:
            # Decrement dashes counter
            self.dashes = min(0, self.dashes - 1)

            # Start dash and dash cooldown timers, sign of dash timer determines direction of dash (particles go opposite direction)
            if (self.sliding_time > AIRTIME_BUFFER + 2 and self.wall_slide_right) or (self.sliding_time <= AIRTIME_BUFFER + 2 and self.flip):
                self.dash_timer = -DASH_TICK
                dash_particle_vel = (DASH_PARTICLE_VEL, 0)
            else:
                self.dash_timer = DASH_TICK
                dash_particle_vel = (-DASH_PARTICLE_VEL, 0)
            
            # Cancel wall slide
            self.sliding_time = 0
            self.dash_cooldown_timer = -DASH_TICK

            # Cloak or dash based on cooldown timer
            if self.has_cloak:
                self.dash_type = 'cloak'
                self.cloak_timer = 1
            else:
                self.dash_type = 'dash'

            # Burst of 3 particles head to toe in opposite direction of dash
            self.game.particles.append(Particle(self.game, self.dash_type + '_particle', self.entity_rect().center, velocity=dash_particle_vel, frame=0))
            self.game.particles.append(Particle(self.game, self.dash_type + '_particle', self.entity_rect().midtop, velocity=dash_particle_vel, frame=0))
            self.game.particles.append(Particle(self.game, self.dash_type + '_particle', self.entity_rect().midbottom, velocity=dash_particle_vel, frame=0))

            self.game.sfx[self.dash_type].play()

            return True
        
    def hitstun_animation(self):
        """
        Hitstun animation and particles immediately after taking damage
        Stop mostly all sound effects
        """
        self.set_action('hitstun')
        self.game.sfx['land'].stop()
        self.game.sfx['falling'].stop()
        self.game.sfx['wings'].stop()
        self.game.sfx['cloak'].stop()
        self.game.sfx['run_grass'].stop()
        self.game.sfx['run_stone'].stop()
        self.game.sfx['wall_slide'].stop()
        self.game.sfx['hitstun'].play()
        self.can_move = False
        self.falling_time = 0

        for i in range(NUM_HITSTUN_PARTICLES):
            hitstun_particle_vel = (random.uniform(-5, 5), random.uniform(-5, 5)) * HITSTUN_PARTICLE_VEL
            self.game.particles.append(Particle(self.game, 'cloak_particle', self.entity_rect().center, hitstun_particle_vel, frame=0))


    def death_warp(self):
        """
        Teleport player to spawn point during fadeout
        Reset physics constants
        """
        self.can_update = True
        self.pos = self.game.player_spawn_pos.copy()
        self.pos[1] += COLLECTABLE_OFFSETS['respawn'][1]
        self.velocity[1] = 0
        self.dash_timer = 0
        self.gravity = GRAVITY_CONST
        self.death_counter += 1
        self.set_action('kneel')

    
    def grub_pointer(self):
        """
        Display particles directing player towards nearest grub
        """
        pass
