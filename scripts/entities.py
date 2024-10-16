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
NUM_PICKUP_PARTICLES = 80
SAW_NOISE_DIST = 80
DASH_TICK = 14

# Enemy constants
CRAWLER_NOISE_DIST = 100

class PhysicsEntity:

    def __init__(self, game, e_type, pos, size, scale=1.0, opacity=255):
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
        self.opacity = opacity

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
    """
    Physics entity subclass that handles collectable items, spawn points, and stationary entities with collision
    """

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
                self.game.particles.append(Particle(self.game, 'long_cloak_particle', (self.rect.centerx + random.uniform(-2, 2), self.rect.centery + random.uniform(-8, 8)), velocity=(random.uniform(-0.4,0.4), random.uniform(-0.05,0.05)), fade_out=2, frame=random.randint(1,4)))


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
            if self.collect_timer == 50:
                rand = random.randint(1, 3)
                self.game.sfx['grub_free_' + str(rand)].play()

            # Burrowing away
            if self.collect_timer == 140:
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
            for i in range(NUM_PICKUP_PARTICLES):
                hitstun_particle_vel = (random.uniform(-2, 2), random.uniform(-2, 2))
                self.game.particles.append(Particle(self.game, particle_type, self.game.player.entity_rect().center, hitstun_particle_vel, frame=0))
            for i in range(NUM_PICKUP_PARTICLES):
                hitstun_particle_vel = (random.uniform(-2, 2), random.uniform(-2, 2))
                self.game.particles.append(Particle(self.game, particle_type, self.entity_rect().center, hitstun_particle_vel, frame=0))
            
            return

        # Start collect timer only first frame of contact with player
        if self.collect_timer < 1:
            self.collect_timer = 1

class Enemy(PhysicsEntity):
    """
    Physics entity subclass that handles enemy AI and animations
    """

    def __init__(self, game, e_type, pos, size, scale=1.0):
        
        super().__init__(game, 'enemies/' + e_type, pos, size, scale)
        self.tilemap = self.game.tilemap

        self.idle_noise_timer = 0

    def update(self, movement=(0, 0)):
        
        self.idle_noise_timer += 1
        
        # Update distance to player
        self.rect = self.entity_rect()
        self.player_rect = self.game.player.entity_rect()
        self.x_dist = self.rect.centerx - self.player_rect.centerx
        self.y_dist = self.rect.centery - self.player_rect.centery
        self.dist_to_player = math.sqrt(self.x_dist**2 + self.y_dist**2)

        
        # Crawling enemy that walkes back and forth
        if self.type == 'enemies/crawlid':

            # If running into wall, turn around
            if self.collisions['left'] or self.collisions['right']:
                self.flip = not self.flip

            # Move forward until there isn't a solid tile in front, then turn around
            elif self.tilemap.tile_solid((self.rect.centerx + (-6 if self.flip else 6), self.pos[1] + 16)):
                movement = (movement[0] - 0.6 if self.flip else 0.6, movement[1])
            else:
                self.flip = not self.flip

            # Damage player if too close, tangible, and not cloaking
            if self.dist_to_player < self.size[1] and self.game.player.intangibility_timer < 0 and (self.game.player.cloak_timer == 0 or self.game.player.cloak_timer > DASH_TICK):
                self.game.damage_fade_out = True
            
             # Play crawling sound effect when close
            if self.dist_to_player < CRAWLER_NOISE_DIST * 1.5:
                self.game.sfx['crawler'].set_volume(min(0.06, (CRAWLER_NOISE_DIST - self.dist_to_player) / (CRAWLER_NOISE_DIST)))
            if self.idle_noise_timer % 100 == 1 and self.dist_to_player < CRAWLER_NOISE_DIST * 1.4:
                    self.game.sfx['crawler'].play()

            # Explode if cloaked into by player
            if self.dist_to_player < self.size[1] and self.game.player.cloak_timer > 0 and self.game.player.cloak_timer <= DASH_TICK:
                self.game.sfx['crawler'].stop()
                self.game.sfx['shade_gate_repel'].play()
                for i in range(30):
                    self.game.particles.append(Particle(self.game, 'cloak_particle', self.rect.center, (random.uniform(-1, 1), random.uniform(-1, 1))))
                self.game.enemies.remove(self)
        

        super().update(self.game.tilemap, movement=movement)

    