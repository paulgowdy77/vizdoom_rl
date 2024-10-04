import vizdoom as vzd
import json
from levdoom_utils import create_doom_game

import skimage.transform
import numpy as np


def load_level_details(level_name):
    with open("levdoom_level_dict.json", "r") as f:
        level_dict = json.load(f)
    level_details = level_dict[level_name]
    return level_details





class DoomEnv:
    def __init__(self, level_to_play, AGENT_CONFIG):
        level_details = load_level_details(level_to_play)
        self.game = self.create_new_game(level_details)
        self.reset()

        self.resolution = AGENT_CONFIG.resolution

        # self.game.init()

    def preprocess(self, img):
        """Down samples image to resolution"""
        img = skimage.transform.resize(img, self.resolution)
        img = img.astype(np.float32)
        img = np.expand_dims(img, axis=0)
        return img
    
    def step(self, action, frame_repeat):
        
        reward = self.game.make_action(action, frame_repeat)
        reward = self.adjust_reward(reward)
        done = self.game.is_episode_finished()
        self.episode_reward += reward
        return reward, done
    
    def adjust_reward(self, reward):
        reward += 0.01
        return reward

    def create_new_game(self, levdoom_level_details):
        print("Initializing doom game")
        print(levdoom_level_details)
        # game = vzd.DoomGame()
        # game.load_config(config_file_path)
        game = create_doom_game(levdoom_level_details)

        game.set_window_visible(False)
        game.set_mode(vzd.Mode.PLAYER)
        game.set_screen_format(vzd.ScreenFormat.GRAY8)
        game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
        game.init()
        print("Doom initialized.")

        return game
    
    def reset(self):
        self.game.new_episode()
        self.episode_reward = 0
        #print("Doom game reset.")

    def get_current_state(self):
        return self.game.get_state()
    
    def get_processed_state(self):
        state = self.get_current_state()
        if state is None:
            return None
        img = state.screen_buffer
        return self.preprocess(img)
    
    def get_action_space_size(self):
        n = self.game.get_available_buttons_size()
        return n
    
    def close_env(self):
        self.game.close()
        print("Doom game closed.")  