with open('backend/game_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. _generate_hitman - skill range 1-50
content = content.replace(
    'skill_level = random.choices([1, 2, 3, 4, 5], weights=[25, 30, 25, 15, 5])[0]',
    'skill_level = random.choices(range(1, 51), weights=([50] + [40]*9 + [30]*10 + [20]*10 + [10]*10 + [5]*10))[0]',
    1
)
print('1. _generate_hitman skill 1-50')

# 2. cut_rates from dict to formula (skills now go up to 50)
content = content.replace(
    'cut_rates = {1: 0.15, 2: 0.20, 3: 0.30, 4: 0.40, 5: 0.50}\n        cut = cut_rates.get(skill_level, 0.20)',
    'cut = min(0.60, 0.10 + skill_level * 0.01)',
    1
)
print('2. cut formula')

# 3. _generate_npc_hitmen - skill 5-50
content = content.replace(
    'skill = random.choices([2, 3, 4, 5, 6, 7, 8, 9, 10], weights=[5, 8, 12, 15, 15, 15, 12, 10, 8])[0]',
    'skill = random.choices(range(5, 51), weights=[5]*10 + [8]*10 + [12]*10 + [10]*10 + [5]*10)[0]',
    1
)
print('3. NPC skill 5-50')

# 4. Training caps: 10->50
content = content.replace(
    'h["skill"] = min(10, h["skill"] + 1)',
    'h["skill"] = min(50, h["skill"] + 1)',
    1
)
print('4. training cap 10->50')

# Also in do_training
content = content.replace(
    'h["skill"] = min(10, h["skill"] + 3)',
    'h["skill"] = min(50, h["skill"] + 3)',
    1
)
print('5. combat training cap 10->50')

# 6. Contract success formula: skill_bonus 0.08->0.01 (since skill now 1-50)
content = content.replace(
    'skill_bonus = hitman["skill"] * 0.08',
    'skill_bonus = hitman["skill"] * 0.01',
    1
)
print('6. contract skill_bonus 0.08->0.01')

# 7. Attack rival success - same adjustment
content = content.replace(
    'player_power = idle_count * 5 + total_skill',
    'player_power = idle_count * 5 + total_skill * 2',
    1
)
print('7. rival attack power adjusted')

# 8. Frontend: skill/10 -> skill/50 display
content = content.replace(
    '${hitman.skill}/10',
    '${hitman.skill}/50',
    1
)
print('8. display /50')

with open('backend/game_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
