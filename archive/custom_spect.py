#!/usr/bin/env python3

#####################################################################
# This script presents SPECTATOR mode. In SPECTATOR mode you play and
# your agent can learn from it.
# Configuration is loaded from "../../scenarios/<SCENARIO_NAME>.cfg" file.
#
# To see the scenario description go to "../../scenarios/README.md"
#####################################################################

import os
from argparse import ArgumentParser
from time import sleep

import vizdoom as vzd




if __name__ == "__main__":
    
    game = vzd.DoomGame()

    # Choose scenario config file you wish to watch.
    # Don't load two configs cause the second will overwrite the first one.
    # Multiple config files are ok but combining these ones doesn't make much sense.

    print("Loading config file...")
    game.load_config("spect.cfg")


    #game.set_doom_scenario_path("./custom_wads/zzz.wad")
    #game.set_doom_map("map01")
    #z = os.path.join(vzd.scenarios_path, "basic.wad")
    #print(z)
    #exit()
    z = "/home/paul/Documents/doom_RL/custom_wads/default_levdoom.wad"
    #/home/paul/Documents/doom_RL/custom_wads/zzz.wad
    
    game.set_doom_scenario_path(z)

    # Sets up game for spectator (you)
    game.add_game_args("+freelook 1")
    game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
    game.set_window_visible(True)
    game.set_mode(vzd.Mode.SPECTATOR)

    # Sets map to start (scenario .wad files can contain many maps).
    game.set_doom_map("map01")

    game.init()

    episodes = 2

    for i in range(episodes):
        print(f"Episode #{i + 1}")

        game.new_episode()
        while not game.is_episode_finished():
            state = game.get_state()

            game.advance_action()
            last_action = game.get_last_action()
            reward = game.get_last_reward()

            print(f"State #{state.number}")
            print("Game variables: ", state.game_variables)
            print("Action:", last_action)
            print("Reward:", reward)
            print("=====================")

        print("Episode finished!")
        print("Total reward:", game.get_total_reward())
        print("************************")
        sleep(2.0)

    game.close()