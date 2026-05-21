with open('backend/game_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add GameManager at the end of the file
content += """


class GameManager:
    \"\"\"管理多个玩家的游戏实例，通过 session_id 隔离\"\"\"
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self._games = {}

    def get_or_create(self, session_id: str):
        \"\"\"获取或创建指定 session 的游戏实例\"\"\"
        if session_id not in self._games:
            self._games[session_id] = GameEngine(self.system_prompt)
        return self._games[session_id]

    def get(self, session_id: str):
        \"\"\"获取指定 session 的游戏实例（不存在返回 None）\"\"\"
        return self._games.get(session_id)

    def remove(self, session_id: str):
        \"\"\"删除指定 session（重置游戏时调用）\"\"\"
        if session_id in self._games:
            del self._games[session_id]
"""

with open('backend/game_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
import ast
ast.parse(content)
print('OK')
