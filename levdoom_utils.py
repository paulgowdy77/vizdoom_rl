from levdoom_level_dictionary import LEVDOOM_LEVEL_DICTIONARY
import vizdoom as vzd

def load_level_files(level_to_play):
    mode = level_to_play["mode"]
    difficulty = level_to_play["difficulty"]
    level_name = level_to_play["level_name"]

    level_wad_file = f"levdoom_levels/{mode}/" + LEVDOOM_LEVEL_DICTIONARY[mode][difficulty][level_name] + ".wad"
    # want to be able to specify different config files for different modes, not one per mode
    conf_file = f"levdoom_levels/{mode}/conf.cfg"

    return {
        "wad_file": level_wad_file,
        "conf_file": conf_file
    }

def create_doom_game(lvl_details):
    game = vzd.DoomGame()

    level_files = load_level_files(lvl_details)

    game.load_config(level_files["conf_file"])
    game.set_doom_scenario_path(level_files["wad_file"])

    return game


# level_to_spectate = {
#     "mode": "health_gathering",
#     "difficulty": 1,
#     "level_name": "HealthGatheringLevel1_8-v0"
# }