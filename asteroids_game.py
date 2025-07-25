import pygame
import math
import random
import sys
import numpy as np
import json
import os

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
FPS = 60

# Create sound effects using pygame's built-in sound generation
def create_thrust_sound():
    # Create a thrust sound (low frequency rumble)
    duration = 0.1
    sample_rate = 22050
    frames = int(duration * sample_rate)
    arr = np.zeros((frames, 2), dtype=np.int16)
    for i in range(frames):
        time = float(i) / sample_rate
        wave = int(4096 * math.sin(2 * math.pi * 80 * time) * math.exp(-time * 5))
        arr[i] = [wave, wave]
    sound = pygame.sndarray.make_sound(arr)
    return sound

def create_bullet_sound():
    # Create a bullet sound (sharp, quick beep)
    duration = 0.1  # Shorter duration for better sync
    sample_rate = 22050
    frames = int(duration * sample_rate)
    arr = np.zeros((frames, 2), dtype=np.int16)
    for i in range(frames):
        time = float(i) / sample_rate
        # Sharp attack, quick decay for immediate response
        wave = int(3000 * math.sin(2 * math.pi * 1200 * time) * math.exp(-time * 15))
        arr[i] = [wave, wave]
    sound = pygame.sndarray.make_sound(arr)
    return sound

class Vector2D:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __mul__(self, scalar):
        return Vector2D(self.x * scalar, self.y * scalar)
    
    def normalize(self):
        length = math.sqrt(self.x**2 + self.y**2)
        if length > 0:
            return Vector2D(self.x / length, self.y / length)
        return Vector2D(0, 0)
    
    def length(self):
        return math.sqrt(self.x**2 + self.y**2)

class Ship:
    def __init__(self, x, y):
        self.pos = Vector2D(x, y)
        self.velocity = Vector2D(0, 0)
        self.angle = 0
        self.radius = 10
        self.thrust = 0.3
        self.max_speed = 8
        self.friction = 0.98
        self.thrust_sound = create_thrust_sound()
        self.thrust_channel = None
        
    def update(self):
        # Mouse controls
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        
        # Calculate angle to mouse position
        dx = mouse_pos[0] - self.pos.x
        dy = mouse_pos[1] - self.pos.y
        target_angle = math.degrees(math.atan2(dy, dx))
        
        # Smooth rotation towards mouse
        angle_diff = target_angle - self.angle
        # Normalize angle difference to [-180, 180]
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360
        
        # Apply rotation with some smoothing
        rotation_speed = 8
        if abs(angle_diff) > rotation_speed:
            self.angle += rotation_speed if angle_diff > 0 else -rotation_speed
        else:
            self.angle = target_angle
        
        # Apply thrust with left mouse button
        if mouse_buttons[0]:  # Left mouse button
            thrust_x = math.cos(math.radians(self.angle)) * self.thrust
            thrust_y = math.sin(math.radians(self.angle)) * self.thrust
            self.velocity = self.velocity + Vector2D(thrust_x, thrust_y)
            
            # Play thrust sound
            if self.thrust_channel is None or not self.thrust_channel.get_busy():
                self.thrust_channel = self.thrust_sound.play(-1) # Loop the sound
        else:
            # Stop thrust sound when not thrusting
            if self.thrust_channel and self.thrust_channel.get_busy():
                self.thrust_channel.stop()
            
        # Apply friction
        self.velocity = self.velocity * self.friction
        
        # Limit speed
        if self.velocity.length() > self.max_speed:
            self.velocity = self.velocity.normalize() * self.max_speed
        
        # Update position
        self.pos = self.pos + self.velocity
        
        # Wrap around screen
        self.pos.x %= SCREEN_WIDTH
        self.pos.y %= SCREEN_HEIGHT
    
    def draw(self, screen):
        # Calculate ship points
        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Ship vertices (triangle)
        points = [
            (self.pos.x + cos_a * 15, self.pos.y + sin_a * 15),  # Front
            (self.pos.x + cos_a * -10 + sin_a * -8, self.pos.y + sin_a * -10 + cos_a * 8),  # Back left
            (self.pos.x + cos_a * -10 + sin_a * 8, self.pos.y + sin_a * -10 + cos_a * -8)   # Back right
        ]
        
        pygame.draw.polygon(screen, WHITE, points, 2)

class Bullet:
    def __init__(self, x, y, angle):
        self.pos = Vector2D(x, y)
        speed = 10
        self.velocity = Vector2D(
            math.cos(math.radians(angle)) * speed,
            math.sin(math.radians(angle)) * speed
        )
        self.lifetime = 60  # frames
        self.radius = 2
    
    def update(self):
        self.pos = self.pos + self.velocity
        self.lifetime -= 1
        
        # Wrap around screen
        self.pos.x %= SCREEN_WIDTH
        self.pos.y %= SCREEN_HEIGHT
        
        return self.lifetime > 0
    
    def draw(self, screen):
        pygame.draw.circle(screen, WHITE, (int(self.pos.x), int(self.pos.y)), self.radius)

class Asteroid:
    def __init__(self, x, y, size=3):
        self.pos = Vector2D(x, y)
        angle = random.uniform(0, 360)
        speed = random.uniform(1, 3)
        self.velocity = Vector2D(
            math.cos(math.radians(angle)) * speed,
            math.sin(math.radians(angle)) * speed
        )
        self.size = size
        self.radius = size * 10
        self.rotation = 0
        self.rotation_speed = random.uniform(-3, 3)
        
        # Generate random shape
        self.points = []
        num_points = 8
        for i in range(num_points):
            angle = (360 / num_points) * i
            variance = random.uniform(0.8, 1.2)
            radius = self.radius * variance
            x = math.cos(math.radians(angle)) * radius
            y = math.sin(math.radians(angle)) * radius
            self.points.append((x, y))
    
    def update(self):
        self.pos = self.pos + self.velocity
        self.rotation += self.rotation_speed
        
        # Wrap around screen
        self.pos.x %= SCREEN_WIDTH
        self.pos.y %= SCREEN_HEIGHT
    
    def draw(self, screen):
        # Rotate and translate points
        rotated_points = []
        for point in self.points:
            cos_r = math.cos(math.radians(self.rotation))
            sin_r = math.sin(math.radians(self.rotation))
            
            rotated_x = point[0] * cos_r - point[1] * sin_r
            rotated_y = point[0] * sin_r + point[1] * cos_r
            
            final_x = rotated_x + self.pos.x
            final_y = rotated_y + self.pos.y
            
            rotated_points.append((final_x, final_y))
        
        pygame.draw.polygon(screen, WHITE, rotated_points, 2)
    
    def split(self):
        if self.size > 1:
            new_asteroids = []
            for _ in range(2):
                new_asteroid = Asteroid(self.pos.x, self.pos.y, self.size - 1)
                new_asteroids.append(new_asteroid)
            return new_asteroids
        return []

def check_collision(obj1, obj2):
    distance = math.sqrt((obj1.pos.x - obj2.pos.x)**2 + (obj1.pos.y - obj2.pos.y)**2)
    return distance < (obj1.radius + obj2.radius)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Asteroids")
        self.clock = pygame.time.Clock()
        
        self.ship = Ship(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.bullets = []
        self.asteroids = []
        self.score = 0
        self.lives = 3
        
        # High score system
        self.high_scores_file = "high_scores.json"
        self.high_scores = self.load_high_scores()
        self.show_high_scores = False
        self.new_high_score = False
        
        # Game over system
        self.game_over = False
        self.game_over_timer = 0
        self.game_over_duration = 300  # 5 seconds at 60 FPS
        
        # Load game over music
        try:
            pygame.mixer.music.load("Game Over (8-Bit Music).mp3")
        except pygame.error:
            print("Warning: Could not load Game Over (8-Bit Music).mp3")
            # Try alternative path
            try:
                pygame.mixer.music.load(os.path.join(os.path.dirname(__file__), "Game Over (8-Bit Music).mp3"))
                print("Loaded music from local directory")
            except pygame.error:
                print("Could not find Game Over (8-Bit Music).mp3 in any location")
        
        # Create sound effects
        self.bullet_sound = create_bullet_sound()
        
        # Track shooting state for proper sync
        self.mouse_was_pressed = False
        self.space_was_pressed = False
        
        # Pause functionality
        self.paused = False
        self.enter_was_pressed = False
        
        # Create initial asteroids
        for _ in range(5):
            while True:
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(0, SCREEN_HEIGHT)
                # Make sure asteroid doesn't spawn on ship
                if math.sqrt((x - self.ship.pos.x)**2 + (y - self.ship.pos.y)**2) > 100:
                    self.asteroids.append(Asteroid(x, y))
                    break
        
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 72)

    def load_high_scores(self):
        """Load high scores from file"""
        try:
            if os.path.exists(self.high_scores_file):
                with open(self.high_scores_file, 'r') as f:
                    scores = json.load(f)
                    # Ensure we have exactly 10 scores, fill with zeros if needed
                    while len(scores) < 10:
                        scores.append(0)
                    return scores[:10]  # Keep only top 10
            else:
                return [0] * 10  # Default 10 empty scores
        except:
            return [0] * 10  # If file is corrupted, start fresh
    
    def save_high_scores(self):
        """Save high scores to file"""
        try:
            with open(self.high_scores_file, 'w') as f:
                json.dump(self.high_scores, f)
        except:
            pass  # If save fails, just continue
    
    def check_high_score(self, score):
        """Check if score qualifies for high score list"""
        return score > min(self.high_scores)
    
    def add_high_score(self, score):
        """Add new high score and sort the list"""
        self.high_scores.append(score)
        self.high_scores.sort(reverse=True)
        self.high_scores = self.high_scores[:10]  # Keep only top 10
        self.save_high_scores()
        self.new_high_score = True
    
    def handle_events(self):
        # Get current input states
        mouse_buttons = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    self.show_high_scores = not self.show_high_scores
                elif event.key == pygame.K_r and self.game_over:
                    # Restart game when R is pressed during game over
                    self.restart_from_game_over()
        
        # Check for pause toggle with Enter key (only if not in game over)
        if not self.game_over and keys[pygame.K_RETURN]:
            if not self.enter_was_pressed:  # First frame of press
                self.paused = not self.paused
        self.enter_was_pressed = keys[pygame.K_RETURN]
        
        # Only handle game inputs when not paused, not showing high scores, and not game over
        if not self.paused and not self.show_high_scores and not self.game_over:
            # Check for shooting with right mouse button
            if mouse_buttons[2]:  # Right mouse button pressed
                if not self.mouse_was_pressed:  # First frame of press
                    self.shoot_bullet()
            self.mouse_was_pressed = mouse_buttons[2]
            
            # Check for shooting with spacebar
            if keys[pygame.K_SPACE]:
                if not self.space_was_pressed:  # First frame of press
                    self.shoot_bullet()
            self.space_was_pressed = keys[pygame.K_SPACE]
        
        return True

    def shoot_bullet(self):
        # Play bullet sound immediately and create bullet
        self.bullet_sound.play()
        bullet = Bullet(self.ship.pos.x, self.ship.pos.y, self.ship.angle)
        self.bullets.append(bullet)
    
    def update(self):
        # Handle game over timer
        if self.game_over:
            self.game_over_timer += 1
            if self.game_over_timer >= self.game_over_duration:
                self.restart_from_game_over()
            return
        
        # Don't update game state when paused or showing high scores
        if self.paused or self.show_high_scores:
            return
            
        self.ship.update()
        
        # Update bullets
        self.bullets = [bullet for bullet in self.bullets if bullet.update()]
        
        # Update asteroids
        for asteroid in self.asteroids:
            asteroid.update()
        
        # Check bullet-asteroid collisions
        for bullet in self.bullets[:]:
            for asteroid in self.asteroids[:]:
                if check_collision(bullet, asteroid):
                    self.bullets.remove(bullet)
                    self.asteroids.remove(asteroid)
                    
                    # Split asteroid
                    new_asteroids = asteroid.split()
                    self.asteroids.extend(new_asteroids)
                    
                    # Increase score
                    self.score += (4 - asteroid.size) * 20
                    break
        
        # Check ship-asteroid collisions
        for asteroid in self.asteroids:
            if check_collision(self.ship, asteroid):
                self.lives -= 1
                if self.lives <= 0:
                    # Trigger game over sequence
                    self.trigger_game_over()
                else:
                    # Reset ship position
                    self.ship.pos = Vector2D(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    self.ship.velocity = Vector2D(0, 0)
                break
        
        # Check if all asteroids destroyed
        if not self.asteroids:
            # Spawn more asteroids
            for _ in range(min(5 + self.score // 1000, 10)):
                while True:
                    x = random.randint(0, SCREEN_WIDTH)
                    y = random.randint(0, SCREEN_HEIGHT)
                    if math.sqrt((x - self.ship.pos.x)**2 + (y - self.ship.pos.y)**2) > 100:
                        self.asteroids.append(Asteroid(x, y))
                        break

    def trigger_game_over(self):
        """Start the game over sequence"""
        self.game_over = True
        self.game_over_timer = 0
        
        # Check for high score before showing game over
        if self.check_high_score(self.score):
            self.add_high_score(self.score)
        
        # Stop any playing sounds
        pygame.mixer.stop()
        
        # Play game over music
        try:
            pygame.mixer.music.play()
        except pygame.error:
            print("Could not play game over music")

    def restart_from_game_over(self):
        """Restart the game from game over state"""
        # Stop game over music
        pygame.mixer.music.stop()
        
        # Reset game state
        self.game_over = False
        self.game_over_timer = 0
        self.reset_game()

    def reset_game(self):
        self.ship = Ship(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.bullets = []
        self.asteroids = []
        self.score = 0
        self.lives = 3
        self.new_high_score = False
        
        # Reset shooting state tracking
        self.mouse_was_pressed = False
        self.space_was_pressed = False
        
        # Reset pause state
        self.paused = False
        self.enter_was_pressed = False
        
        # Don't reset game_over state here - let restart_from_game_over handle it
        
        # Create initial asteroids
        for _ in range(5):
            while True:
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(0, SCREEN_HEIGHT)
                if math.sqrt((x - self.ship.pos.x)**2 + (y - self.ship.pos.y)**2) > 100:
                    self.asteroids.append(Asteroid(x, y))
                    break

    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw game over screen
        if self.game_over:
            # Draw final game state in background (dimmed)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(128)
            overlay.fill(BLACK)
            
            # Draw game elements dimmed
            self.ship.draw(self.screen)
            for bullet in self.bullets:
                bullet.draw(self.screen)
            for asteroid in self.asteroids:
                asteroid.draw(self.screen)
            
            # Apply dark overlay
            self.screen.blit(overlay, (0, 0))
            
            # Draw "GAME OVER" text
            game_over_text = self.large_font.render("GAME OVER", True, WHITE)
            game_over_x = SCREEN_WIDTH // 2 - game_over_text.get_width() // 2
            game_over_y = SCREEN_HEIGHT // 2 - 100
            self.screen.blit(game_over_text, (game_over_x, game_over_y))
            
            # Draw final score
            final_score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            final_score_x = SCREEN_WIDTH // 2 - final_score_text.get_width() // 2
            final_score_y = game_over_y + 80
            self.screen.blit(final_score_text, (final_score_x, final_score_y))
            
            # Draw high score if achieved
            if self.new_high_score:
                new_high_text = self.font.render("NEW HIGH SCORE!", True, WHITE)
                new_high_x = SCREEN_WIDTH // 2 - new_high_text.get_width() // 2
                new_high_y = final_score_y + 40
                self.screen.blit(new_high_text, (new_high_x, new_high_y))
            
            # Draw restart instructions
            restart_text = self.small_font.render("Press R to restart or wait for auto-restart", True, WHITE)
            restart_x = SCREEN_WIDTH // 2 - restart_text.get_width() // 2
            restart_y = SCREEN_HEIGHT - 100
            self.screen.blit(restart_text, (restart_x, restart_y))
            
            # Draw countdown timer
            remaining_time = (self.game_over_duration - self.game_over_timer) // 60 + 1
            timer_text = self.small_font.render(f"Auto-restart in: {remaining_time}s", True, WHITE)
            timer_x = SCREEN_WIDTH // 2 - timer_text.get_width() // 2
            timer_y = restart_y + 30
            self.screen.blit(timer_text, (timer_x, timer_y))
            
        # Normal game drawing
        elif not self.show_high_scores:
            self.ship.draw(self.screen)
            
            for bullet in self.bullets:
                bullet.draw(self.screen)
            
            for asteroid in self.asteroids:
                asteroid.draw(self.screen)
        
        # Always draw UI (except during game over)
        if not self.game_over:
            score_text = self.font.render(f"Score: {self.score}", True, WHITE)
            lives_text = self.font.render(f"Lives: {self.lives}", True, WHITE)
            
            self.screen.blit(score_text, (10, 10))
            self.screen.blit(lives_text, (10, 50))
            
            # Draw high score indicator
            if self.high_scores[0] > 0:
                high_score_text = self.small_font.render(f"High Score: {self.high_scores[0]}", True, WHITE)
                self.screen.blit(high_score_text, (10, 90))
            
            # Draw new high score message (only during gameplay)
            if self.new_high_score and not self.game_over:
                new_high_text = self.font.render("NEW HIGH SCORE!", True, WHITE)
                x = SCREEN_WIDTH // 2 - new_high_text.get_width() // 2
                y = 150
                self.screen.blit(new_high_text, (x, y))
        
        # Draw high scores table
        if self.show_high_scores and not self.game_over:
            title_text = self.font.render("HIGH SCORES", True, WHITE)
            title_x = SCREEN_WIDTH // 2 - title_text.get_width() // 2
            title_y = 100
            self.screen.blit(title_text, (title_x, title_y))
            
            for i, score in enumerate(self.high_scores):
                if score > 0:  # Only show non-zero scores
                    rank_text = self.small_font.render(f"{i+1:2d}. {score:,}", True, WHITE)
                    rank_x = SCREEN_WIDTH // 2 - rank_text.get_width() // 2
                    rank_y = title_y + 50 + i * 25
                    self.screen.blit(rank_text, (rank_x, rank_y))
            
            # Instructions to close high scores
            close_text = self.small_font.render("Press H to close", True, WHITE)
            close_x = SCREEN_WIDTH // 2 - close_text.get_width() // 2
            close_y = title_y + 50 + 10 * 25 + 20
            self.screen.blit(close_text, (close_x, close_y))
        
        # Draw pause indicator
        elif self.paused and not self.game_over:
            pause_text = self.font.render("PAUSED", True, WHITE)
            pause_x = SCREEN_WIDTH // 2 - pause_text.get_width() // 2
            pause_y = SCREEN_HEIGHT // 2 - pause_text.get_height() // 2
            
            # Draw semi-transparent background for pause text
            pause_bg = pygame.Surface((pause_text.get_width() + 40, pause_text.get_height() + 20))
            pause_bg.set_alpha(128)
            pause_bg.fill(BLACK)
            self.screen.blit(pause_bg, (pause_x - 20, pause_y - 10))
            
            # Draw pause text
            self.screen.blit(pause_text, (pause_x, pause_y))
            
            # Draw resume instruction
            resume_text = pygame.font.Font(None, 24).render("Press ENTER to resume", True, WHITE)
            resume_x = SCREEN_WIDTH // 2 - resume_text.get_width() // 2
            resume_y = pause_y + pause_text.get_height() + 20
            self.screen.blit(resume_text, (resume_x, resume_y))
        
        # Draw instructions (only when not paused, not game over, and showing instructions)
        elif not hasattr(self, 'show_instructions') or (self.show_instructions and not self.game_over):
            instructions = [
                "Mouse: Point to Aim",
                "Left Click: Thrust | Right Click: Shoot",
                "ENTER: Pause | H: High Scores",
                "Move mouse to start"
            ]
            for i, instruction in enumerate(instructions):
                text = self.font.render(instruction, True, WHITE)
                x = SCREEN_WIDTH // 2 - text.get_width() // 2
                y = SCREEN_HEIGHT // 2 + i * 40
                self.screen.blit(text, (x, y))
        
        pygame.display.flip()

    def run(self):
        running = True
        self.show_instructions = True
        
        while running:
            running = self.handle_events()
            
            # Hide instructions after mouse movement (but not when paused, showing high scores, or game over)
            if not self.paused and not self.show_high_scores and not self.game_over:
                mouse_pos = pygame.mouse.get_pos()
                mouse_buttons = pygame.mouse.get_pressed()
                if mouse_pos != (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2) or any(mouse_buttons):
                    self.show_instructions = False
            
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

# Run the game
if __name__ == "__main__":
    game = Game()
    game.run()
