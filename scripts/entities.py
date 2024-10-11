import pygame
import math
import random

from .particle import Particle

# Universal physics constants
TERMINAL_VELOCITY = 6.0
GRAVITY_CONST = 0.2
TICK_RATE = 60
RENDER_SCALE = 4.0
VOID_HEIGHT = 400


# Collectable constants
COLLECTABLE_SIZES = {
    'grub' : (30, 30),
    'cloak_pickup' : (16, 16),
}
COLLECTABLE_OFFSETS = {
    'grub' : (0, 11),
    'cloak_pickup' : (0, 0),
}
GRUB_NOISE_DIST = 200

# Player physics constants
MOVEMENT_X_SCALE = 1.8
JUMP_Y_VEL = -5.0
NUM_AIR_JUMPS = 1
AIR_JUMP_Y_VEL = -4.4
NUM_AIR_DASHES = 1
VARIABLE_JUMP_SHEAR = 6.0
AIRTIME_BUFFER = 4
LOW_GRAV_THRESHOLD = 0.6
LOW_GRAV_DIVISOR = 1.3
DASH_X_SCALE = 4
DASH_TICK = 14
DASH_COOLDOWN_TICK = 20
WALL_SLIDE_VEL = 1.25
WALL_JUMP_Y = -4.5
WALL_JUMP_TICK_CUTOFF = 9
WALL_JUMP_TICK_STALL = 2

# Player animation constants
PLAYER_ANIM_OFFSET = (-2, -8)
DASH_ANIM_OFFSET = (-8, -8)
RUN_PARTICLE_DELAY = 10
DASH_PARTICLE_VEL = 2
DASH_TRAIL_VARIANCE = 0.3
NUM_HITSTUN_PARTICLES = 80
HITSTUN_PARTICLE_VEL = 1
SLIDE_SFX_LEN = 150

class PhysicsEntity:

    def __init__(self, game, e_type, pos, size):
        # General info and physics
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
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
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), (self.pos[0] - offset[0] + self.anim_offset[0], self.pos[1] - offset[1] + self.anim_offset[1]))

class Collectable(PhysicsEntity):
    
    def __init__(self, game, pos, c_type):
        self.size = COLLECTABLE_SIZES[c_type]
        self.game = game
        self.pos = (pos[0] + COLLECTABLE_OFFSETS['grub'][0], pos[1] + COLLECTABLE_OFFSETS['grub'][1])

        super().__init__(game, 'collectables/' + c_type, pos, self.size)

        self.collect_timer = 0
        self.idle_noise_timer = GRUB_NOISE_DIST
        self.dist_to_player = 0
        self.rect = 0
        

    def update(self):
        
        self.animation.update()
        self.idle_noise_timer += 1

        # Collect upon player collision
        if self.entity_rect().colliderect(self.game.player.entity_rect()):
            self.collect()

        # Increment collect counter only if collect() has been called
        if self.collect_timer > 0:
            self.collect_timer += 1

        # Update distance to player
        self.rect = self.entity_rect()
        player_rect = self.game.player.entity_rect()
        x_dist = self.rect.x - player_rect.x
        y_dist = self.rect.y - player_rect.y
        self.dist_to_player = math.sqrt(x_dist**2 + y_dist**2)

        self.pos = self.pos[0] + 0, self.pos[1] + 0

        # Play time based sound effects
        if self.type == 'collectables/cloak_pickup':
            if self.collect_timer == 10:
                pass

        if self.type == 'collectables/grub':

            # Sad grub noises if within distance and after interval of seconds
            if self.dist_to_player < GRUB_NOISE_DIST and self.collect_timer == 0 and self.idle_noise_timer > random.randint(3, 8) * TICK_RATE:

                rand = random.randint(1, 2)
                rand_chance = random.randint(1, 5)
                if rand_chance == 1:
                    self.idle_noise_timer = 0
                    self.game.sfx['grub_sad_idle_' + str(rand)].set_volume((GRUB_NOISE_DIST - self.dist_to_player) / (GRUB_NOISE_DIST))
                    self.game.sfx['grub_sad_idle_' + str(rand)].play()

            # Glass break (and mute sad noises)
            if self.collect_timer == 2:
                self.game.sfx['grub_sad_idle_1'].stop()
                self.game.sfx['grub_sad_idle_2'].play()
                self.game.sfx['grub_break'].play()

            # Happy grub noises
            if self.collect_timer == 40:
                rand = random.randint(1, 3)
                self.game.sfx['grub_free_' + str(rand)].play()

            # Burrowing away
            if self.collect_timer == 120:
                self.game.sfx['grub_burrow'].play()
        
    def collect(self):
        """
        Events occuring after player collides with collectable
        """

        if self.type == 'collectables/cloak_pickup':
            self.game.player.has_cloak = True
            self.game.sfx['ability_pickup'].play()
            self.game.sfx['ability_info'].play()
            self.game.collectables.remove(self)
            for i in range(NUM_HITSTUN_PARTICLES * 2):
                hitstun_particle_vel = (random.uniform(-2, 2), random.uniform(-2, 2))
                self.game.particles.append(Particle(self.game, 'dash_particle', self.game.player.entity_rect().center, hitstun_particle_vel, frame=0))
            return

        self.set_action('collect')

        # Start timer only first frame of contact with player
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
        self.can_move = True

        # Jump and wall jump variables
        self.has_wings = False
        self.has_claw = False
        self.running_time = 0                           # Time spent running    
        self.air_time = -10                             # Time since leaving ground
        self.wall_jump_timer = 0                        # Time since leaving wall from wall jump
        self.sliding_time = 0                           # Time spent wall sliding
        self.wall_slide = False                         
        self.wall_slide_timer = 1                       # Time since last moment sliding on wall
        self.jumps = NUM_AIR_JUMPS
        self.wall_jump_direction = False                # False is left jump (right wall), True is right jump (left wall)


        # Control dash variables
        self.has_cloak = False
        self.dashes = NUM_AIR_DASHES
        self.dash_timer = 0
        self.dash_cooldown_timer = 0

        # Camera control for player holding up or down while idle for a time
        self.idle_timer = 0
        self.holding_up = False
        self.looking_up = False
        self.holding_down = False
        self.looking_down = False
        

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
        # Apply faster dash movement while dashing
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
    
        # Void out and death warp if player falls below given Y value
        if self.pos[1] > VOID_HEIGHT:
            self.game.fade_out = True

        # Void out and death warp if player collides with spike tiles
        below_tile = self.game.tilemap.tile_below(self.entity_rect().center)
        if not below_tile == None:
            if below_tile['type'] == 'spikes' and self.collisions['down'] == True:
                self.game.fade_out = True

        # Update collision and position based on movement
        super().update(tilemap, movement=movement)

        # Update jump control variables
        self.air_time += 1
        self.wall_jump_timer += 1
        self.dash_cooldown_timer += 1
        self.wall_slide_timer += 1
        self.wall_slide = False
        self.anim_offset = PLAYER_ANIM_OFFSET

        # Reset upon touching ground
        below_tile = self.game.tilemap.tile_below(self.pos)
        if self.collisions['down']:
                if self.air_time > AIRTIME_BUFFER:
                    self.game.sfx['land'].play()
                self.air_time = 0
                self.jumps = NUM_AIR_JUMPS
                self.dashes = NUM_AIR_DASHES
                if not below_tile == None:
                    if not below_tile['type'] == 'spikes':
                        self.game.player_spawn_pos = self.pos.copy()

        # Reset upon grabbing walls
        if self.collisions['right'] or self.collisions['left']:
            self.jumps = NUM_AIR_JUMPS
            self.dashes = NUM_AIR_DASHES


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
        

        # Check for wall slide, reduce Y speed if touching wall
        if (self.collisions['right'] or self.collisions['left']) and self.air_time > AIRTIME_BUFFER and self.velocity[1] > 0 and self.has_claw:

            # Only play grabbing wall sound if not touching wall previously
            if self.wall_slide_timer > AIRTIME_BUFFER:
                self.game.sfx['mantis_claw'].play()
            self.wall_slide_timer = 0
            self.sliding_time += 1
            
            if self.sliding_time % SLIDE_SFX_LEN == 1:
                self.game.sfx['wall_slide'].play()
            
            self.wall_slide = True
            self.dash_timer /= 2
            self.velocity[1] = min(self.velocity[1], WALL_SLIDE_VEL)

            self.set_action('wall_slide')   # Wall sliding
        # Wall slide animation facing right, opposite of wall
            player_rect = self.entity_rect()
            if self.collisions['right']:
                self.flip = False
                slide_particle_pos = player_rect.midright
            else:
                self.flip = True
                slide_particle_pos = player_rect.midleft
        # Wall slide particles
            slide_particle_start_f = random.randint(0, 2)
            slide_particle_vel = (0, random.randint(1, 4) / 2)
            self.game.particles.append(Particle(self.game, 'slide_particle', slide_particle_pos, velocity=slide_particle_vel, frame=slide_particle_start_f))

        # Dash animation 
        elif abs(self.dash_timer) > 0:
            self.set_action('dash')         # Dashing
            self.anim_offset = DASH_ANIM_OFFSET
        # Dash particles 
            dash_trail_pos = (self.entity_rect().centerx, self.entity_rect().centery + random.randint(-1, 1) / DASH_TRAIL_VARIANCE)
            self.game.particles.append(Particle(self.game, 'dash_particle', dash_trail_pos, velocity=(0,0), frame=0))

        # Buffer for small amounts of airtime flashing animation
        elif self.air_time > AIRTIME_BUFFER:
            if self.velocity[1] < 0:
                self.set_action('jump')     # Rising
            else:
                self.set_action('fall')     # Falling
        # Run if moving and not moving into a wall
        elif movement[0] != 0 and not self.collisions['left'] and not self.collisions['right']:
            self.set_action('run')          # Running
            idling = False
            self.running_time += 1

        # Running particles
            if self.wall_jump_timer % RUN_PARTICLE_DELAY == 0:
                run_particle_start_f = random.randint(0, 1)
                run_particle_vel = (random.randint(-1, 1) / 3, random.randint(-1, 1) / 5)
                self.game.particles.append(Particle(self.game, 'run_particle', self.entity_rect().midbottom, velocity=run_particle_vel, frame=run_particle_start_f))

        # Determine ground material while walking for running sounds
            below_tile = self.game.tilemap.tile_below(self.pos)
            if not below_tile == None and self.running_time % 180 == 1:
                if below_tile['type'] == 'grass':
                    self.game.sfx['run_grass'].play()
                if below_tile['type'] == 'stone':
                    self.game.sfx['run_stone'].play()
                    
        elif self.holding_up:
            self.looking_up = True
            idling = True
            self.set_action('look_up')     # Looking up

        elif self.holding_down:
            self.looking_down = True
            idling = True
            self.set_action('look_down')    # Looking down

        else:
            idling = True
            self.set_action('idle')         # Idle
            
        # Add delay in camera movement to avoid rapid changes
        if idling:
            self.idle_timer += 1
        else:
            self.idle_timer = 0


        # Ensure no lingering sound effects
        if self.wall_slide == False and self.has_claw:
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
        # Wall jump
        if self.wall_slide and self.has_claw:
            self.game.sfx['wall_jump'].play()
            if self.flip and self.last_movement[0] < 0:         # Off of left wall
                self.wall_jump_timer = 0
                self.wall_jump_direction = True
                self.velocity[1] = WALL_JUMP_Y
                self.air_time = AIRTIME_BUFFER + 1
                return True
            elif not self.flip and self.last_movement[0] > 0:   # Off of right wall
                self.wall_jump_timer = 0
                self.wall_jump_direction = False
                self.velocity[1] = WALL_JUMP_Y
                self.air_time = AIRTIME_BUFFER + 1
                return True
        # Normal and double jump
        elif self.jumps and not self.dash_timer:
            if self.air_time > AIRTIME_BUFFER * 2:              # Mid Air jump
                if self.has_wings:
                    self.jumps = max(0, self.jumps - 1)
                    self.velocity[1] = AIR_JUMP_Y_VEL
                    self.game.sfx['wings'].play()
                # Midair wing jump particle
                    self.game.particles.append(Particle(self.game, 'wings_particle', self.entity_rect().center, velocity=(0, 0), frame=0, flip=self.flip, follow_player=True))
                    self.game.particles.append(Particle(self.game, 'slide_particle', self.entity_rect().center, velocity=(0, 1), frame=0))
                    self.game.particles.append(Particle(self.game, 'slide_particle', self.entity_rect().midleft, velocity=(-1, 0.8), frame=0))
                    self.game.particles.append(Particle(self.game, 'slide_particle', self.entity_rect().midright, velocity=(1, 0.8), frame=0))
            else:                                               # Grounded jump
                self.velocity[1] = JUMP_Y_VEL
                self.game.sfx['jump'].play()
            self.air_time = AIRTIME_BUFFER + 1
            return True
        
        return False

    def jump_release(self):
        """
        Allow variable jump height by reducing velocity on SPACE keystroke up
        """
        if self.velocity[1] < 0:
            self.velocity[1] /= VARIABLE_JUMP_SHEAR
            self.gravity = GRAVITY_CONST

    def dash(self):
        """
        Dash by starting timer and taking over player movement until timer reaches zero
        Return TRUE if sucessful dash
        """
        if self.has_cloak and not self.dash_timer and not self.wall_slide and self.wall_jump_timer >= WALL_JUMP_TICK_CUTOFF and self.dashes and self.dash_cooldown_timer > DASH_COOLDOWN_TICK and not self.collisions['right'] and not self.collisions['left']:
        # Decrement dashes counter
            self.dashes = min(0, self.dashes - 1)
        # Start dash and dash cooldown timers, sign of dash timer determines direction of dash (particles go opposite direction)
            if self.flip:
                self.dash_timer = -DASH_TICK
                dash_particle_vel = (DASH_PARTICLE_VEL, 0)
            else:
                self.dash_timer = DASH_TICK
                dash_particle_vel = (-DASH_PARTICLE_VEL, 0)
            self.dash_cooldown_timer = -DASH_TICK

            self.game.particles.append(Particle(self.game, 'dash_particle', self.entity_rect().center, velocity=dash_particle_vel, frame=0))
            self.game.particles.append(Particle(self.game, 'dash_particle', self.entity_rect().midtop, velocity=dash_particle_vel, frame=0))
            self.game.particles.append(Particle(self.game, 'dash_particle', self.entity_rect().midbottom, velocity=dash_particle_vel, frame=0))

            self.game.sfx['cloak'].play()

            return True
        
    def death_warp(self):
        """
        Teleport player to spawn point during fadeout
        """
        self.pos = self.game.player_spawn_pos.copy()
        self.velocity[1] = 0
        self.dash_timer = 0
        self.gravity = GRAVITY_CONST
        self.set_action('kneel')

    
    def hitstun_animation(self):
        """
        Hitstun animation immediatley after taking damage
        """
        self.set_action('hitstun')
        self.game.sfx['hitstun'].play()
        self.game.sfx['wings'].stop()
        self.game.sfx['run_grass'].stop()
        self.game.sfx['run_stone'].stop()
        self.game.sfx['wall_slide'].stop()
        self.can_move = False

        for i in range(NUM_HITSTUN_PARTICLES):
            hitstun_particle_vel = (random.uniform(-5, 5), random.uniform(-5, 5)) * HITSTUN_PARTICLE_VEL
            self.game.particles.append(Particle(self.game, 'dash_particle', self.entity_rect().center, hitstun_particle_vel, frame=0))
    