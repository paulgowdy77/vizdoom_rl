import levdoom

env = levdoom.make('HealthGatheringLevel3_1-v0')
env.reset()
done = False
steps = 0
total_reward = 0
while not done:
    action = env.action_space.sample()
    state, reward, done, truncated, info = env.step(action)
    env.render()
    steps += 1
    total_reward += reward
print(f"Episode finished in {steps} steps. Reward: {total_reward:.2f}")
env.close()