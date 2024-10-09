import pygame
import math

# Physics constants
TERMINAL_VELOCITY = 6.0
GRAVITY_CONST = 0.2
TICK_RATE = 60

# Offset in image render position to match collision
PLAYER_X_OFFSET = -5
PLAYER_Y_OFFSET = -11
ANIM_OFFSET = (3, 4)

# Player constants
MOVEMENT_X_SCALE = 1.8
JUMP_Y_VEL = -5.0
NUM_AIR_JUMPS = 1
AIR_JUMP_Y_VEL = -4.2
NUM_DASHES = 1
VARIABLE_JUMP_SHEAR = 8.0
AIRTIME_BUFFER = 4
LOW_GRAV_THRESHOLD = 0.6
LOW_GRAV_DIVISOR = 1.3
WALL_SLIDE_VEL = 1.25
WALL_JUMP_Y = -4.8
WALL_JUMP_TICK_CUTOFF = 9
WALL_JUMP_TICK_STALL = 2
DASH_X_SCALE = 5
DASH_TICK = 12
DASH_COOLDOWN_TICK = 8

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
        self.anim_offset = ANIM_OFFSET
        self.flip = False
        self.set_action('idle')

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
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), (self.pos[0] - offset[0] + PLAYER_X_OFFSET + self.anim_offset[0], self.pos[1] - offset[1] + PLAYER_Y_OFFSET + self.anim_offset[1]))



class Player(PhysicsEntity):
    """
    PhysicsEntity subclass to handle player-specific animation and input parameters
    """
    def __init__(self, game, pos, size):
        super().__init__(game, 'player', pos, size)
        self.air_time = 0                               # Time since leaving ground
        self.wall_jump_timer = 0                         # Time since leaving wall from wall jump
        self.wall_slide = False
        self.jumps = NUM_AIR_JUMPS
        self.wall_jump_direction = False                # False is left jump (right wall), True is right jump (left wall)
        self.dashes = NUM_DASHES
        self.dash_timer = 0
        self.dash_cooldown_timer = 0
        

    def update(self, tilemap, movement=(0, 0)):
        """
        Update player movement variables and handle wall jump logic
        Set player animation state based on game state
        """
        # MOVEMENT

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

        # Update collision and movement
        super().update(tilemap, movement=movement)

        # Update jump control variables
        self.air_time += 1
        self.wall_jump_timer += 1
        self.dash_cooldown_timer += 1
        self.wall_slide = False
        self.anim_offset = ANIM_OFFSET

        # Reset upon touching ground
        if self.collisions['down']:
            self.air_time = 0
            self.jumps = NUM_AIR_JUMPS
            self.dashes = NUM_DASHES

        # Reset upon grabbing walls
        if self.collisions['right'] or self.collisions['left']:
            self.jumps = NUM_AIR_JUMPS
            self.dashes = NUM_DASHES

        # Add floatiness to the peak of player jump by dividing gravity
        if self.air_time > AIRTIME_BUFFER:
            if self.velocity[1] > -LOW_GRAV_THRESHOLD and self.velocity[1] < LOW_GRAV_THRESHOLD:
                self.gravity = GRAVITY_CONST / LOW_GRAV_DIVISOR
        # Suspend gravity while dashing
            elif abs(self.dash_timer) > 0:
                self.gravity = 0
                self.velocity[1] = -0.05
            else:
                self.gravity = GRAVITY_CONST

        # Decrement dash timer towards 0 from both sides
        if self.dash_timer > 0:
            self.dash_timer = max(0, self.dash_timer - 1)
        if self.dash_timer < 0:
            self.dash_timer = min(0, self.dash_timer + 1)


        # ANIMATION

        # Check for wall slide, reduce Y speed if touching wall
        if (self.collisions['right'] or self.collisions['left']) and self.air_time > AIRTIME_BUFFER and self.velocity[1] > -0.5:
            self.wall_slide = True
            self.dash_timer /= 2
            self.velocity[1] = min(self.velocity[1], WALL_SLIDE_VEL)
            self.set_action('wall_slide')
        # Wall slide animation facing right, opposite of wall
            if self.collisions['right']:
                self.flip = False
            else:
                self.flip = True

        # Dash animation 
        elif abs(self.dash_timer) > 0:
            self.set_action('dash')
            self.anim_offset = (-3, 4)

        # Buffer for small amounts of airtime flashing animation
        elif self.air_time > AIRTIME_BUFFER:
            if self.velocity[1] < 0:
                self.set_action('jump')     # Rising upward
            else:
                self.set_action('fall')     # Falling
        elif movement[0] != 0 and not self.collisions['left'] and not self.collisions['right']:
            self.set_action('run')          # Running (not into a wall)
        else:
            self.set_action('idle')         # Idle
        

    def jump(self):
        """
        Check if player is eligible to jump, perform jump and wall jump
        Return TRUE if player has sucessfully jumped
        """
        # Wall jump
        if self.wall_slide:
            if self.flip and self.last_movement[0] < 0:         # Left wall
                self.wall_jump_timer = 0
                self.wall_jump_direction = True
                self.velocity[1] = WALL_JUMP_Y
                self.air_time = AIRTIME_BUFFER + 1
                return True
            elif not self.flip and self.last_movement[0] > 0:   # Right wall
                self.wall_jump_timer = 0
                self.wall_jump_direction = False
                self.velocity[1] = WALL_JUMP_Y
                self.air_time = AIRTIME_BUFFER + 1
                return True
        # Normal and double jump
        elif self.jumps and not self.dash_timer:
            if self.air_time > AIRTIME_BUFFER * 2:                  # Mid Air Jump
                self.jumps = max(0, self.jumps - 1)
                self.velocity[1] = AIR_JUMP_Y_VEL
            else:
                self.velocity[1] = JUMP_Y_VEL
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
        if not self.dash_timer and not self.wall_slide and self.wall_jump_timer > DASH_TICK / 2 and self.dashes and self.dash_cooldown_timer > DASH_COOLDOWN_TICK and not self.collisions['right'] and not self.collisions['left']:
        # Decrement dashes counter
            self.dashes = min(0, self.dashes - 1)
        # Start dash and dash cooldown timers, sign of dash timer determines direction of dash
            if self.flip:
                self.dash_timer = -DASH_TICK
            else:
                self.dash_timer = DASH_TICK
            self.dash_cooldown_timer = -DASH_TICK
            return True