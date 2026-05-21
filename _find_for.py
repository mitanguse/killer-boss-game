import json

with open('backend/game_engine.py', 'rb') as f:
    data = f.read()

target = b'def assign_contract'
idx = data.find(target)
chunk = data[idx:idx+1500]

# Find all 'for' keywords
pos = -1
for _ in range(10):
    pos = chunk.find(b'for ', pos + 1)
    if pos < 0:
        break
    start = max(0, pos - 40)
    end = min(len(chunk), pos + 80)
    print(f'--- for at byte {pos} ---')
    print(chunk[start:end].decode('utf-8', errors='replace'))
