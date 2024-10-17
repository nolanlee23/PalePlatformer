import pygame
import math
import random

from .entities import PhysicsEntity
from .particle import Particle
from .hud import HudElement

# Universal physics constants
TERMINAL_VELOCITY = 5.0
GRAVITY_CONST = 0.2
TICK_RATE = 60
RENDER_SCALE = 4.0
DEPTHS_Y = 400
DEPTHS_X = -300

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
DASH_TICK = 15
DASH_COOLDOWN_TICK = 22
WALL_SLIDE_VEL = 1.33
WALL_JUMP_Y = -4.6
WALL_JUMP_TICK_CUTOFF = 8
WALL_JUMP_TICK_STALL = 2
WALL_JUMP_BUFFER = 10

# Player animation constants
PLAYER_ANIM_OFFSET = (-3, -8)
DASH_ANIM_OFFSET = (-9, -8)
RUN_PARTICLE_DELAY = 10
DASH_PARTICLE_VEL = 1.5
DASH_TRAIL_VARIANCE = 0.3
NUM_HITSTUN_PARTICLES = 80
HITSTUN_PARTICLE_VEL = 1
SLIDE_SFX_LEN = 150
FALLING_VOLUME = 0.2



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
        self.holding_left = False
        self.holding_right = False
        self.has_grub_finder = False

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
        self.intangibility_timer -= 1
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

            self.dash_timer /= 3
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

        # Become translucent when intangibile
        if self.intangibility_timer <= 1:
            self.opacity = 230
        else:
            self.opacity = 255


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
        if not self.can_move:
            return False
        
        # Wall jump if wall sliding, has claw, and has not wall jumped in ~10 frames
        if self.wall_slide_timer < WALL_JUMP_BUFFER and self.has_claw and self.wall_jump_timer > WALL_JUMP_BUFFER + 4:
            self.game.sfx['wall_slide'].stop()
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
        elif self.jumps and abs(self.dash_timer) < AIRTIME_BUFFER:
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
        Dash by starting timer and taking over player movement ( fast x, no y ) until timer reaches zero
        Return TRUE if sucessful dash
        """
        if not self.can_move:
            return False
        
        # Has dashes, not currently dashing, not dashed in ~20 frames
        if self.has_dash and self.dashes and not self.dash_timer and self.dash_cooldown_timer > DASH_COOLDOWN_TICK:

            # Start dash and dash cooldown timers, sign of dash timer determines direction of dash (particles go opposite direction)
            if (self.sliding_time > AIRTIME_BUFFER + 2 and self.wall_slide_right and self.wall_jump_timer > 10) or (self.sliding_time <= AIRTIME_BUFFER + 2 and self.flip and self.wall_jump_timer > 10) or (self.wall_jump_timer <= 10 and self.holding_left):
                self.dash_timer = -DASH_TICK
                dash_particle_vel = (DASH_PARTICLE_VEL, 0)
            elif (self.sliding_time > AIRTIME_BUFFER + 2 and not self.wall_slide_right and self.wall_jump_timer > 10) or (self.sliding_time <= AIRTIME_BUFFER + 2 and not self.flip and self.wall_jump_timer > 10)  or (self.wall_jump_timer <= 10 and self.holding_right):
                self.dash_timer = DASH_TICK
                dash_particle_vel = (-DASH_PARTICLE_VEL, 0)
            else:
                return False
            
            # Decrement dashes counter
            self.dashes = min(0, self.dashes - 1)

            # Cancel wall slide
            self.sliding_time = 0
            self.wall_slide_timer = WALL_JUMP_BUFFER
            self.dash_cooldown_timer = -DASH_TICK
            self.velocity[1] = 0

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
        self.pos[1] += 1
        self.velocity[1] = 0
        self.dash_timer = 0
        self.gravity = GRAVITY_CONST
        self.death_counter += 1
        self.set_action('kneel')

    
    def grub_pointer(self):
        """
        Display particles directing player towards nearest grub
        """
        if not self.can_move:
            return False
        
        closest_grub = None
        closest_grub_dist = None
        player_rect = self.entity_rect()

        # Loop through all entities and examine all uncollected grubs
        for entity in self.game.collectables:
            if entity.type == 'collectables/grub' and entity.collect_timer == 0:

                # Assign first in the list
                if closest_grub is None:
                    closest_grub = entity
                    closest_grub_dist = math.sqrt((entity.rect.centerx - player_rect.centerx)**2 + (entity.rect.centery - player_rect.centery)**2)
                    continue
                
                # Compare current to closest, assign if curr is closer
                curr_dist = math.sqrt((entity.rect.centerx - player_rect.centerx)**2 + (entity.rect.centery - player_rect.centery)**2)
                if curr_dist < closest_grub_dist:
                    closest_grub = entity
                    closest_grub_dist = curr_dist
        
        # Normalize vector between player and closest grub
        pointing_vector = pygame.Vector2(closest_grub.rect.centerx - player_rect.centerx, closest_grub.rect.centery - player_rect.centery)
        pointing_vector.normalize_ip()

        self.game.sfx['grubfather_1'].play()
        for i in range(3):
            self.game.particles.append(Particle(self.game, 'grub_particle', player_rect.center, pointing_vector * (i + 1) * 0.75, fade_out=5, frame=4 - i))
