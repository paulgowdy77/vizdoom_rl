import json
import torch
import wandb

import itertools as it
import os
import random
from collections import deque
from time import sleep, time

import numpy as np
import skimage.transform
import torch.nn as nn
import torch.optim as optim
from tqdm import trange
import datetime

from DoomEnv import DoomEnv

def load_level_details(level_name):
    with open("levdoom_level_dict.json", "r") as f:
        level_dict = json.load(f)
    level_details = level_dict[level_name]
    return level_details


class DictObj:
    def __init__(self, in_dict: dict):
        for key, val in in_dict.items():
            setattr(self, key, val)

def load_agent_config(config_file_path):
    with open(config_file_path, "r") as f:
        config = json.load(f)
    config = DictObj(config)
    return config





series_timestamp = datetime.datetime.now().strftime("%m%d-%H%M")

AGENT_CONFIG = load_agent_config("configs/dqn_basic_config.json")

level_name = "SeekAndSlayLevel0-v0"
level_details = load_level_details(level_name)

NB_RUNS = 3


# Uses GPU if available
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    torch.backends.cudnn.benchmark = True
    print("Using GPU")
else:
    DEVICE = torch.device("cpu")
    print("Using CPU")



def test(game, agent, actions, base_reward_per_step=0.01):
    """Runs a test_episodes_per_epoch episodes and prints the result"""
    print("\nTesting...")
    test_scores = []
    for test_episode in trange(AGENT_CONFIG.test_episodes_per_epoch, leave=False):
        game.new_episode()
        episode_reward = 0
        while not game.is_episode_finished():
            state = preprocess(game.get_state().screen_buffer)
            best_action_index = agent.get_action(state)

            reward = game.make_action(actions[best_action_index], AGENT_CONFIG.frame_repeat)
            reward += base_reward_per_step
            episode_reward += reward

        #r = game.get_total_reward()
        r = episode_reward
        test_scores.append(r)

    test_scores = np.array(test_scores)
    print(
        "Results: mean: {:.1f} +/- {:.1f},".format(
            test_scores.mean(), test_scores.std()
        ),
        "min: %.1f" % test_scores.min(),
        "max: %.1f" % test_scores.max(),
    )
    return test_scores.mean()

def run_training(wandb_run, save_path, doom_env, agent, actions, num_epochs, frame_repeat, steps_per_epoch=2000, base_reward_per_step=0.01):
    """
    Run num epochs of training episodes.
    Skip frame_repeat number of frames after each action.
    """

    start_time = time()

    for epoch in range(num_epochs):

        doom_env.reset()

        train_scores = []
        global_step = 0
        print(f"\nEpoch #{epoch + 1}")

        episode_reward = 0

        for _ in trange(steps_per_epoch, leave=False):

            state = doom_env.get_processed_state()

            action = agent.get_action(state)
            reward, done = doom_env.step(actions[action], frame_repeat)

            if not done:
                next_state = doom_env.get_processed_state()
            else:
                next_state = np.zeros((1, 30, 45)).astype(np.float32)

            agent.append_memory(state, action, reward, next_state, done)

            if global_step > agent.batch_size:
                agent.train()
            if done:
                #train_scores.append(game.get_total_reward())
                train_scores.append(doom_env.episode_reward)
                doom_env.reset()

            global_step += 1

        agent.update_target_net()
        train_scores = np.array(train_scores)

        print(
            "Results: mean: {:.1f} +/- {:.1f},".format(
                train_scores.mean(), train_scores.std()
            ),
            "min: %.1f," % train_scores.min(),
            "max: %.1f," % train_scores.max(),
        )


        test_score = -5
        #test(game, agent, actions, base_reward_per_step)

        wandb_run.log(
            {
                "train_score": train_scores.mean(), 
                "test_score": test_score,
                "global_step": global_step,
            }
        )

        if AGENT_CONFIG.save_model:
            #print("Saving the network weights to:", AGENT_CONFIG.model_savefile)
            torch.save(agent.q_net, save_path + "/model.pth")

        print("Total elapsed time: %.2f minutes" % ((time() - start_time) / 60.0))

    doom_env.close_env()

class DuelQNet(nn.Module):
    """
    This is Duel DQN architecture.
    see https://arxiv.org/abs/1511.06581 for more information.
    """

    def __init__(self, available_actions_count):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 8, kernel_size=3, stride=2, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(),
        )

        self.conv2 = nn.Sequential(
            nn.Conv2d(8, 8, kernel_size=3, stride=2, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(),
        )

        self.conv3 = nn.Sequential(
            nn.Conv2d(8, 8, kernel_size=3, stride=1, bias=False),
            nn.BatchNorm2d(8),
            nn.ReLU(),
        )

        self.conv4 = nn.Sequential(
            nn.Conv2d(8, 16, kernel_size=3, stride=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(),
        )

        self.state_fc = nn.Sequential(nn.Linear(96, 64), nn.ReLU(), nn.Linear(64, 1))

        self.advantage_fc = nn.Sequential(
            nn.Linear(96, 64), nn.ReLU(), nn.Linear(64, available_actions_count)
        )

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.conv4(x)
        x = x.view(-1, 192)
        x1 = x[:, :96]  # input for the net to calculate the state value
        x2 = x[:, 96:]  # relative advantage of actions in the state
        state_value = self.state_fc(x1).reshape(-1, 1)
        advantage_values = self.advantage_fc(x2)
        x = state_value + (
            advantage_values - advantage_values.mean(dim=1).reshape(-1, 1)
        )

        return x

class DQNAgent:
    def __init__(
        self,
        action_size,
        memory_size,
        batch_size,
        discount_factor,
        lr,
        load_model,
        epsilon=1,
        epsilon_decay=0.9996,
        epsilon_min=0.1,
    ):
        self.action_size = action_size
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.batch_size = batch_size
        self.discount = discount_factor
        self.lr = lr
        self.memory = deque(maxlen=memory_size)
        self.criterion = nn.MSELoss()

        if load_model:
            print("Loading model from: ", AGENT_CONFIG.model_savefile)
            self.q_net = torch.load(AGENT_CONFIG.model_savefile)
            self.target_net = torch.load(AGENT_CONFIG.model_savefile)
            self.epsilon = self.epsilon_min

        else:
            print("Initializing new model")
            self.q_net = DuelQNet(action_size).to(DEVICE)
            self.target_net = DuelQNet(action_size).to(DEVICE)

        self.opt = optim.SGD(self.q_net.parameters(), lr=self.lr)

    def get_action(self, state):
        if np.random.uniform() < self.epsilon:
            return random.choice(range(self.action_size))
        else:
            state = np.expand_dims(state, axis=0)
            state = torch.from_numpy(state).float().to(DEVICE)
            action = torch.argmax(self.q_net(state)).item()
            return action

    def update_target_net(self):
        self.target_net.load_state_dict(self.q_net.state_dict())

    def append_memory(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def train(self):
        batch = random.sample(self.memory, self.batch_size)
        batch = np.array(batch, dtype=object)

        states = np.stack(batch[:, 0]).astype(float)
        actions = batch[:, 1].astype(int)
        rewards = batch[:, 2].astype(float)
        next_states = np.stack(batch[:, 3]).astype(float)
        dones = batch[:, 4].astype(bool)
        not_dones = ~dones

        row_idx = np.arange(self.batch_size)  # used for indexing the batch

        # value of the next states with double q learning
        # see https://arxiv.org/abs/1509.06461 for more information on double q learning
        with torch.no_grad():
            next_states = torch.from_numpy(next_states).float().to(DEVICE)
            idx = row_idx, np.argmax(self.q_net(next_states).cpu().data.numpy(), 1)
            next_state_values = self.target_net(next_states).cpu().data.numpy()[idx]
            next_state_values = next_state_values[not_dones]

        # this defines y = r + discount * max_a q(s', a)
        q_targets = rewards.copy()
        q_targets[not_dones] += self.discount * next_state_values
        q_targets = torch.from_numpy(q_targets).float().to(DEVICE)

        # this selects only the q values of the actions taken
        idx = row_idx, actions
        states = torch.from_numpy(states).float().to(DEVICE)
        action_values = self.q_net(states)[idx].float().to(DEVICE)

        self.opt.zero_grad()
        td_error = self.criterion(q_targets, action_values)
        td_error.backward()
        self.opt.step()

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        else:
            self.epsilon = self.epsilon_min


def run_training_for_DQN(level_name, wandb_run, agent_config, save_path):

    doom_env = DoomEnv(level_name, agent_config)
   
    n = doom_env.get_action_space_size()
    actions = [list(a) for a in it.product([0, 1], repeat=n)]

    # Initialize our agent with the set parameters
    agent = DQNAgent(
        len(actions),
        lr=agent_config.learning_rate,
        batch_size=agent_config.batch_size,
        memory_size=agent_config.replay_memory_size,
        discount_factor=agent_config.discount_factor,
        load_model=agent_config.load_model,
    )

    run_training(
        wandb_run,
        save_path,
        #game,
        doom_env,
        agent,
        actions,
        num_epochs=agent_config.train_epochs,
        frame_repeat=agent_config.frame_repeat,
        steps_per_epoch=agent_config.learning_steps_per_epoch
    )

    # print("======================================")
    # print("Training finished. It's time to watch!")
    print("Training finished.")

    # Reinitialize the game with window visible
    #game.close()
    doom_env.close_env()
    # game.set_window_visible(True)
    # game.set_mode(vzd.Mode.ASYNC_PLAYER)
    # game.init()
    # pass


save_dir = "model_checkpoints/"

for run_nb in range(NB_RUNS):

    run_name = level_details["level_name"] + f"-run-{run_nb}--{series_timestamp}"
    run_save_dir = save_dir + run_name

    # create run name directory
    os.makedirs(run_save_dir, exist_ok=True)

    wdb_run = wandb.init(
        project="doom-rl",
        name=run_name,
        config=AGENT_CONFIG,
        group=level_details["level_name"] + "-" + series_timestamp,
    )

    run_training_for_DQN(level_name, wdb_run, AGENT_CONFIG, run_save_dir)

    wdb_run.finish()

