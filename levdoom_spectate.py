import vizdoom as vzd
from time import sleep

from levdoom_utils import create_doom_game




level_to_spectate = {
    "mode": "health_gathering",
    "difficulty": 1,
    "level_name": "HealthGatheringLevel1_8-v0"
}

game = create_doom_game(level_to_spectate)

#game.add_game_args("+freelook 1")
game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)

game.set_window_visible(True)
game.set_mode(vzd.Mode.SPECTATOR)

game.init()

game.new_episode()
while not game.is_episode_finished():
        
    state = game.get_state()

    game.advance_action()
    last_action = game.get_last_action()
    reward = game.get_last_reward()

    # print(f"State #{state.number}")
    # print("Game variables: ", state.game_variables)
    # print("Action:", last_action)
    # print("Reward:", reward)
    # print("=====================")
    if reward != 0:
        print(f"Reward: {reward}")

print("Episode finished!")
print("Total reward:", game.get_total_reward())
print("************************")
sleep(2.0)

game.close()