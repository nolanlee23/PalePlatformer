import os
import pygame

BASE_IMG_PATH = 'images/'

def listdir_noinvis(path):
    """
    os.listdir() but filters out evil hidden files like .DS_STORE
    """
    for file in os.listdir(path):
        if not file.startswith('.'):
            yield file

def load_image(path):
    """
    Load single image
    """
    img = pygame.image.load(BASE_IMG_PATH + path).convert_alpha()
    return img

def load_images(path):
    """
    Load a folder of images into a list
    """
    images = []
    for img_name in sorted(listdir_noinvis(BASE_IMG_PATH + path)):
        images.append(load_image(path + '/' + img_name))
    return images

class Animation:
    """
    Control animation assets and frame data
    """
    def __init__(self, images, img_dur=5, loop=True):
        self.images = list(images)
        self.img_duration = img_dur
        self.loop = loop
        self.done = False
        self.frame = 0

    def copy(self):
        """
        Create and return copy of animation instance
        """
        return Animation(self.images, self.img_duration, self.loop)
    
    def update(self):
        """
        Increment animation frame
        """
        # Length in game ticks of total animation time
        total_animation_len = self.img_duration * len(self.images)

        if self.loop:
            # If animation loops, take remainder when dividing by animation frame length
            self.frame = (self.frame + 1) % total_animation_len
        else:
            # If animation doesn't loop, remain on final frame
            self.frame = min(self.frame + 1, total_animation_len - 1)
            if self.frame >= total_animation_len - 1:
                self.done = True

    def img(self):
        """
        Get current img of animation based on current game frame for render
        """
        return self.images[int(self.frame / self.img_duration)]